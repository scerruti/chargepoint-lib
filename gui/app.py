import streamlit as st
import pandas as pd
import plotly.express as px
import os
import json
import sys
from datetime import datetime
import calendar

# --- IMPORT FROM THE INSTALLED PACKAGE ---
try:
    from chargepoint_dal.dal import ChargePointDAL
except ImportError as e:
    st.error(f"Failed to import DAL. Did you run 'pip install -e .'?: {e}")
    st.stop()

# --- CONFIGURATION & STYLING ---
st.set_page_config(page_title="CPH50 Control", layout="wide", page_icon="⚡")

st.markdown("""
    <style>
    .main .block-container { padding-top: 2rem; }
    div[data-testid="stMetric"] {
        background-color: var(--secondary-background-color);
        padding: 15px;
        border-radius: 10px;
        text-align: center;
        border: 1px solid rgba(128, 128, 128, 0.2);
    }
    div[data-testid="stMetricLabel"] { color: var(--text-color) !important; font-weight: bold; }
    </style>
""", unsafe_allow_html=True)

# --- BACKEND LOGIC ---
current_dir = os.path.dirname(os.path.abspath(__file__))
BASE_DIR = os.path.abspath(os.path.join(current_dir, '..', 'data'))
VEHICLE_CONFIG_PATH = os.path.join(BASE_DIR, 'vehicle_config.json')
SESSION_VEHICLE_MAP_PATH = os.path.join(BASE_DIR, 'session_vehicle_map.json')

class DataService:
    def __init__(self):
        self.user = os.environ.get("CP_USERNAME")
        self.pwd = os.environ.get("CP_PASSWORD")
        
        if not self.user or not self.pwd:
            st.error("Missing credentials! Please set CP_USERNAME and CP_PASSWORD environment variables.")
            st.stop()
            
        self.dal = ChargePointDAL(
            username=self.user,
            password=self.pwd,
            rate_limit=2, 
            rate_period=10.0
        )
        
        self.vehicle_config = self._load_json(VEHICLE_CONFIG_PATH).get('vehicles', {})
        self.session_vehicle_map = self._load_json(SESSION_VEHICLE_MAP_PATH).get('sessions', {})

    def _load_json(self, path):
        if not os.path.isfile(path): return {}
        try:
            with open(path, 'r') as f: return json.load(f)
        except: return {}

    def get_visualization_config(self):
        color_map = {}
        pattern_map = {}
        color_map["Unknown"] = "#808080"
        pattern_map["Unknown"] = "/"
        
        for v_id, v_data in self.vehicle_config.items():
            name = v_data.get('nickname') or v_data.get('model')
            color = v_data.get('display_color', '#667eea')
            if name:
                color_map[name] = color
                pattern_map[name] = ""
                
        return color_map, pattern_map

    def get_month_data(self, year, month):
        try:
            raw_sessions = self.dal.get_sessions(year=year, month=month, max_batches=10)
        except Exception as e:
            st.error(f"DAL Error: {e}")
            return pd.DataFrame()

        normalized_rows = []
        for s in raw_sessions:
            details = s.get('charging_status', s)
            sid = str(details.get('session_id', s.get('session_id', '')))
            
            vid = self.session_vehicle_map.get(sid, {}).get('vehicle')
            if not vid: vid = details.get('vehicle_info', {}).get('vehicle_id')
            if not vid: vid = s.get('vehicle', {}).get('id')
            
            v_display = "Unknown"
            efficiency = 2.5 
            
            if vid:
                vid_str = str(vid)
                v_config = self.vehicle_config.get(vid_str)
                if not v_config:
                    for k, v in self.vehicle_config.items():
                        if str(v.get('vehicle_id')) == vid_str:
                            v_config = v
                            break
                if v_config:
                    v_display = v_config.get('nickname') or v_config.get('model')
                    efficiency = v_config.get('efficiency_mi_per_kwh', 2.5)

            start_raw = details.get('start_time') or s.get('session_start_time')
            end_raw = details.get('end_time') or s.get('session_end_time')
            start_dt = self._parse_time(start_raw)
            end_dt = self._parse_time(end_raw)
            
            duration_min = 0
            is_active = False
            if start_dt:
                if end_dt:
                    duration_min = int((end_dt - start_dt).total_seconds() / 60)
                else:
                    if (datetime.now() - start_dt).total_seconds() < 86400:
                        is_active = True
                        duration_min = int((datetime.now() - start_dt).total_seconds() / 60)
            
            energy = float(details.get('energy_kwh') or s.get('energy_kwh') or 0)
            miles = energy * efficiency

            normalized_rows.append({
                "session_id": sid,
                "Date": start_dt,
                "Vehicle": v_display,
                "Energy (kWh)": energy,
                "Miles": miles,
                "Efficiency": efficiency,
                "Duration (min)": duration_min,
                "Status": "Active" if is_active else "Completed",
                "Location": "Home",
                "Details": "📊" # Icon in its own column
            })
            
        df = pd.DataFrame(normalized_rows)
        if not df.empty:
            df = df.sort_values(by="Date", ascending=False)
        return df
    
    def get_session_details(self, session_id):
        return self.dal.get_session_activity(session_id, include_samples=True)

    def _parse_time(self, val):
        if not val: return None
        try:
            if isinstance(val, (int, float)):
                return datetime.fromtimestamp(val / 1000)
            if isinstance(val, str):
                return datetime.fromisoformat(val)
        except: return None
        return None

# --- UI COMPONENTS ---

@st.dialog("Charging Details", width="large")
def show_session_modal(session_id, row_data, service):
    with st.spinner("Fetching power curve..."):
        data = service.get_session_details(session_id)
    
    status = data.get('charging_status', {}) if data else {}
    
    col1, col2 = st.columns([2, 1])
    with col1:
        st.subheader(f"{row_data['Vehicle']}")
        if row_data['Date']:
            st.caption(f"{row_data['Date'].strftime('%A, %b %d, %Y • %I:%M %p')}")

    with col2:
        st.info(f"ID: {session_id}")

    samples = status.get('update_data', [])
    if samples:
        chart_data = []
        for s in samples:
            if 'power_kw' in s and 'timestamp' in s:
                chart_data.append({
                    'Time': datetime.fromtimestamp(s['timestamp']/1000),
                    'Power (kW)': s['power_kw']
                })
        
        if chart_data:
            df_chart = pd.DataFrame(chart_data)
            
            fig = px.area(df_chart, x='Time', y='Power (kW)')
            fig.update_traces(
                line=dict(color='#667eea'), 
                fillcolor='rgba(102, 126, 234, 0.4)',
                mode="lines",
                hovertemplate='%{y} kW<extra></extra>' 
            )
            fig.update_layout(
                margin=dict(l=0, r=0, t=10, b=0),
                height=250,
                xaxis_title=None,
                yaxis_title="kW",
                showlegend=False,
                hovermode="x", 
            )
            fig.update_xaxes(
                showspikes=True, spikemode="across", spikesnap="cursor", 
                showline=False, showgrid=True, spikecolor="grey",
                spikethickness=1, spikedash="dash"
            )
            fig.update_yaxes(showspikes=False)
            st.plotly_chart(fig, width="stretch")
    else:
        st.warning("No power curve data available.")

    m1, m2, m3 = st.columns(3)
    cost = status.get('total_amount', 0)
    
    m1.metric("Energy", f"{row_data['Energy (kWh)']:.2f} kWh")
    m2.metric("Cost", f"${cost:.2f}")
    m3.metric("Est. Miles", f"{row_data['Miles']:.1f} mi", help=f"Efficiency: {row_data['Efficiency']} mi/kWh")

# --- MAIN APP ---

def main():
    service = DataService()

    with st.sidebar:
        st.header("Data Controls")
        if st.button("🔄 Refresh Data from API"):
            st.toast("Asking DAL to fetch new data...", icon="📡")
            st.cache_data.clear()

    tab1, tab2, tab3, tab4 = st.tabs(["Status", "History", "Labeling", "Blog"])
    
    with tab2:
        st.subheader("Charging History")
        
        c1, c2, c3, c4 = st.columns(4)
        years = ["2026", "2025", "2024"] 
        sel_year = c1.selectbox("Year", years)
        
        months = list(calendar.month_name)[1:]
        current_month_idx = datetime.now().month - 1
        sel_month_name = c2.selectbox("Month", months, index=current_month_idx)
        sel_month_num = list(calendar.month_name).index(sel_month_name)
        
        sel_vehicle = c3.selectbox("Vehicle", ["All Vehicles", "Serenity", "Volvo"])
        sel_metric = c4.selectbox("Metric", ["Energy (kWh)", "Miles"])
        
        st.divider()

        df = service.get_month_data(int(sel_year), sel_month_num)
        
        if not df.empty:
            if sel_vehicle != "All Vehicles":
                df = df[df['Vehicle'].str.contains(sel_vehicle, case=False, na=False)]

            total_energy = df["Energy (kWh)"].sum()
            total_sessions = len(df)
            total_miles = df["Miles"].sum()
            
            m1, m2, m3 = st.columns(3)
            m1.metric("TOTAL ENERGY", f"{total_energy:.1f} kWh")
            m2.metric("SESSIONS", f"{total_sessions}")
            if sel_metric == "Miles":
                 m3.metric("TOTAL MILES", f"{total_miles:.1f} mi")
            else:
                 m3.metric("AVG ENERGY", f"{(total_energy/total_sessions if total_sessions else 0):.1f} kWh")
            
            # Chart
            color_map, pattern_map = service.get_visualization_config()
            y_axis = "Energy (kWh)" if sel_metric == "Energy (kWh)" else "Miles"
            df['Day'] = df['Date'].dt.day
            chart_data = df.groupby(['Day', 'Vehicle'])[y_axis].sum().reset_index()
            
            fig = px.bar(
                chart_data, 
                x='Day', y=y_axis, color='Vehicle', pattern_shape='Vehicle',
                color_discrete_map=color_map, pattern_shape_map=pattern_map,
                hover_data={'Day': True, y_axis: ':.1f', 'Vehicle': True}
            )
            fig.update_traces(marker_line_width=0)
            fig.update_layout(legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1))
            st.plotly_chart(fig, width="stretch")
            
            st.subheader("Session Details")
            st.caption("Click any row to view details.")
            
            display_df = df.copy()
            display_df['Date'] = display_df['Date'].dt.strftime('%b %d, %I:%M %p')
            display_df['Duration'] = display_df.apply(
                lambda x: f"{x['Duration (min)']} min {'(Active)' if x['Status']=='Active' else ''}", axis=1
            )
            
            # DYNAMIC HEIGHT CALCULATION
            # approx 35px per row + 38px for header. Cap at 600px max to avoid huge pages.
            table_height = min((len(display_df) * 35) + 38, 600)
            if table_height < 150: table_height = 150 # Minimum height

            event = st.dataframe(
                display_df,
                width="stretch",
                hide_index=True,
                height=table_height,
                column_order=["Date", "Vehicle", "Energy (kWh)", "Details", "Miles", "Duration", "Location"],
                column_config={
                    "Energy (kWh)": st.column_config.NumberColumn(
                        "Energy (kWh)",
                        format="%.1f"
                    ),
                    "Details": st.column_config.Column(
                        "View",
                        help="Graph",
                        width="small",
                    ),
                    "Miles": st.column_config.NumberColumn(
                        "Miles",
                        help="Calculated based on vehicle efficiency.",
                        format="%.1f"
                    )
                },
                on_select="rerun",
                selection_mode="single-row"
            )
            
            if event.selection.rows:
                selected_idx = event.selection.rows[0]
                row_data = df.iloc[selected_idx]
                selected_session_id = row_data['session_id']
                show_session_modal(selected_session_id, row_data, service)
                
        else:
            st.info(f"No data found for {sel_month_name} {sel_year}")

if __name__ == "__main__":
    main()
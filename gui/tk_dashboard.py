
import os
import json
import tkinter as tk
from tkinter import ttk, messagebox
from datetime import datetime

# Paths for vehicle config and session vehicle map
BASE_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data'))
DATA_DIR = os.path.join(BASE_DIR, 'session_cache')
VEHICLE_CONFIG_PATH = os.path.join(BASE_DIR, 'vehicle_config.json')
SESSION_VEHICLE_MAP_PATH = os.path.join(BASE_DIR, 'session_vehicle_map.json')

DATA_DIR = os.path.abspath(os.path.join(os.path.dirname(__file__), '../data/session_cache'))


class SessionData:
    def __init__(self):
        self.years = self._find_years()
        self.vehicle_config = self._load_vehicle_config()
        self.session_vehicle_map = self._load_session_vehicle_map()

    def _find_years(self):
        if not os.path.isdir(DATA_DIR):
            return []
        return sorted([y for y in os.listdir(DATA_DIR) if y.isdigit()])

    def get_months(self, year):
        path = os.path.join(DATA_DIR, year)
        if not os.path.isdir(path):
            return []
        return sorted([m for m in os.listdir(path) if m.isdigit()])

    def get_sessions(self, year, month):
        path = os.path.join(DATA_DIR, year, month)
        if not os.path.isdir(path):
            return []
        files = [f for f in os.listdir(path) if f.endswith('.json')]
        return [f[:-5] for f in files]

    def get_session_details(self, year, month, session_id):
        path = os.path.join(DATA_DIR, year, month, f'{session_id}.json')
        if not os.path.isfile(path):
            return None
        with open(path, 'r') as f:
            data = json.load(f)
        # Skip if data is a list (malformed/legacy file)
        if isinstance(data, list):
            return None
        # Always extract from 'charging_status' if present
        if isinstance(data, dict) and 'charging_status' in data:
            details = data['charging_status']
        else:
            details = data
        # Defensive: skip if details is a list
        if isinstance(details, list):
            return None
        # Attach session_id for mapping
        details['session_id'] = session_id
        # Attach vehicle info from session_vehicle_map if available
        vehicle_map = self.session_vehicle_map.get(session_id)
        if vehicle_map:
            details['vehicle_id'] = vehicle_map.get('vehicle')
            details['confidence'] = vehicle_map.get('confidence')
        else:
            details['vehicle_id'] = None
            details['confidence'] = None
        # Attach vehicle display info if available
        if details.get('vehicle_id') and details['vehicle_id'] in self.vehicle_config:
            vinfo = self.vehicle_config[details['vehicle_id']]
            details['vehicle_display'] = vinfo.get('nickname') or vinfo.get('model')
            details['vehicle_color'] = vinfo.get('display_color')
        else:
            details['vehicle_display'] = ''
            details['vehicle_color'] = ''
        return details

    def _load_vehicle_config(self):
        try:
            with open(VEHICLE_CONFIG_PATH, 'r') as f:
                data = json.load(f)
            return data.get('vehicles', {})
        except Exception:
            return {}

    def _load_session_vehicle_map(self):
        try:
            with open(SESSION_VEHICLE_MAP_PATH, 'r') as f:
                data = json.load(f)
            return data.get('sessions', {})
        except Exception:
            return {}


def format_session_row(details):
    # Extract start/end as ms since epoch (UTC)
    start = details.get('start_time')
    end = details.get('end_time')
    date_str = ''
    time_str = ''
    duration = ''
    # Format date/time
    try:
        start_int = int(start)
    except Exception:
        start_int = None
    try:
        end_int = int(end)
    except Exception:
        end_int = None
    if start_int:
        try:
            dt = datetime.fromtimestamp(start_int / 1000, datetime.UTC)
            date_str = dt.strftime('%Y-%m-%d')
            time_str = dt.strftime('%H:%M')
        except Exception:
            date_str = str(start)
            time_str = ''
    # Compute duration
    if start_int and end_int:
        try:
            dt1 = datetime.fromtimestamp(start_int / 1000, datetime.UTC)
            dt2 = datetime.fromtimestamp(end_int / 1000, datetime.UTC)
            mins = int((dt2-dt1).total_seconds()//60)
            if mins < 1:
                duration = '<1 min'
            else:
                duration = f"{mins} min"
        except Exception:
            duration = ''
    # Energy (rounded, always shown as float)
    energy = details.get('energy_kwh') or details.get('energy') or ''
    try:
        energy = f"{float(energy):.3f}" if energy != '' else ''
    except Exception:
        pass
    # Vehicle display
    vehicle = details.get('vehicle_display') or ''
    # Confidence (always show as percent if available)
    confidence = details.get('confidence')
    if confidence is not None:
        try:
            confidence = f"{int(float(confidence)*100)}%"
        except Exception:
            confidence = str(confidence)
    else:
        confidence = ''
    return (date_str, time_str, duration, energy, vehicle, confidence)

class DashboardApp(tk.Tk):
    def __init__(self):
        super().__init__()
        self.title('ChargePoint Session Analytics')
        self.geometry('900x600')
        self.data = SessionData()
        self._build_ui()

    def _build_ui(self):
        frame = ttk.Frame(self)
        frame.pack(fill='both', expand=True, padx=20, pady=20)

        # Year/month selectors
        self.year_var = tk.StringVar()
        self.month_var = tk.StringVar()
        years = self.data.years
        months = self.data.get_months(years[-1]) if years else []
        self.year_cb = ttk.Combobox(frame, textvariable=self.year_var, values=years, state='readonly', width=6)
        self.month_cb = ttk.Combobox(frame, textvariable=self.month_var, values=months, state='readonly', width=4)
        self.year_cb.grid(row=0, column=0, padx=5, pady=5, sticky='w')
        self.month_cb.grid(row=0, column=1, padx=5, pady=5, sticky='w')
        self.year_cb.bind('<<ComboboxSelected>>', self._on_year)
        self.month_cb.bind('<<ComboboxSelected>>', self._on_month)
        if years:
            self.year_var.set(years[-1])
            self._update_months()

        # Table
        columns = ('Date', 'Start Time', 'Duration', 'Energy (kWh)', 'Vehicle', 'Confidence')
        self.tree = ttk.Treeview(frame, columns=columns, show='headings', height=20)
        for col in columns:
            self.tree.heading(col, text=col)
            self.tree.column(col, width=120)
        self.tree.grid(row=1, column=0, columnspan=6, sticky='nsew', pady=10)
        self.tree.bind('<Double-1>', self._on_row)
        frame.rowconfigure(1, weight=1)
        frame.columnconfigure(5, weight=1)
        self._update_table()

    def _on_year(self, event=None):
        self._update_months()
        self._update_table()

    def _on_month(self, event=None):
        self._update_table()

    def _update_months(self):
        year = self.year_var.get()
        months = self.data.get_months(year)
        self.month_cb['values'] = months
        if months:
            self.month_var.set(months[-1])
        else:
            self.month_var.set('')

    def _update_table(self):
        year = self.year_var.get()
        month = self.month_var.get()
        for row in self.tree.get_children():
            self.tree.delete(row)
        if not year or not month:
            return
        sessions = self.data.get_sessions(year, month)
        for session_id in sessions:
            details = self.data.get_session_details(year, month, session_id)
            if not isinstance(details, dict):
                continue  # skip malformed or list-based session files
            row = format_session_row(details)
            # Debug: print the row being inserted
            print(f"Session {session_id}: {row}")
            self.tree.insert('', 'end', iid=session_id, values=row)

    def _on_row(self, event):
        item = self.tree.selection()
        if not item:
            return
        session_id = item[0]
        year = self.year_var.get()
        month = self.month_var.get()
        details = self.data.get_session_details(year, month, session_id)
        if details:
            msg = json.dumps(details, indent=2)
            messagebox.showinfo('Session Details', msg)

if __name__ == '__main__':
    app = DashboardApp()
    app.mainloop()

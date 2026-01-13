import os
from chargepoint_dal import ChargePointDAL

def test_session_details():
    username = os.getenv("CP_USERNAME")
    password = os.getenv("CP_PASSWORD")
    station_id = os.getenv("CP_STATION_ID")
    dal = ChargePointDAL(username, password, station_id)
    year = 2025
    month = 10
    sessions = dal.get_sessions(year=year, month=month)
    print(f"All sessions for {year}-{month:02d}:")
    target_sid = "4469113931"
    found = False
    for s in sessions:
        sid = str(s.get("session_id") or s.get("sessionId"))
        loc = s.get("location", {})
        is_public = not (loc.get("is_home_charger") or loc.get("isHomeCharger"))
        print(f"Session {sid}: Public={is_public}, Location={loc.get('address') or loc.get('address1')}, Energy={s.get('energy_kwh')}")
        if sid == target_sid:
            found = True
            print(f"\nRetrieving detailed activity for session {sid}...")
            activity = dal.get_session_activity(sid)
            if activity:
                print("Detailed activity:")
                print(activity)
            else:
                print("No detailed activity found for this session.")
    if not found:
        print(f"Session {target_sid} not found in results.")

if __name__ == "__main__":
    test_session_details()

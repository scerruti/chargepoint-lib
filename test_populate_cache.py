import os
import datetime
from chargepoint_dal import ChargePointDAL

def test_populate_cache():
    username = os.getenv("CP_USERNAME")
    password = os.getenv("CP_PASSWORD")
    station_id = os.getenv("CP_STATION_ID")
    dal = ChargePointDAL(username, password, station_id, git_commit_enabled=True)
    now = datetime.datetime.now()
    year = now.year
    month = now.month
    print(f"Reading sessions for {year}-{month:02d}...")
    sessions = dal.get_sessions(year=year, month=month)
    print(f"Found {len(sessions)} sessions.")
    for s in sessions:
        sid = str(s.get("session_id") or s.get("sessionId"))
        print(f"Fetching activity for session {sid}...")
        activity = dal.get_session_activity(sid)
        if activity:
            print(f"Session {sid} activity cached.")
        else:
            print(f"No activity found for session {sid}.")

if __name__ == "__main__":
    test_populate_cache()

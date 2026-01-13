from datetime import datetime

def filter_vehicles_by_date(vehicles: dict, session_date: datetime) -> dict:
    """
    Return a dict of vehicles valid for the given session_date based on valid_periods.
    """
    valid = {}
    from datetime import timezone
    # Ensure session_date is timezone-aware (UTC)
    if session_date.tzinfo is None:
        session_date = session_date.replace(tzinfo=timezone.utc)
    for vid, vinfo in vehicles.items():
        periods = vinfo.get("valid_periods", [])
        for period in periods:
            start = datetime.strptime(period["start"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            end = None
            if period.get("end"):
                end = datetime.strptime(period["end"], "%Y-%m-%d").replace(tzinfo=timezone.utc)
            if (session_date >= start) and (end is None or session_date <= end):
                valid[vid] = vinfo
                break
    return valid
import os
import json
from datetime import timedelta

def daterange(start_date, end_date):
    for n in range((end_date - start_date).days + 1):
        yield start_date + timedelta(n)

def load_session_map(path):
    if not os.path.exists(path):
        return {"sessions": {}, "unknown_sessions": [], "last_updated": None, "statistics": {}}
    with open(path, "r") as f:
        return json.load(f)

def save_session_map(data, path):
    tmp_path = path + ".tmp"
    with open(tmp_path, "w") as f:
        json.dump(data, f, indent=2)
    os.replace(tmp_path, path)

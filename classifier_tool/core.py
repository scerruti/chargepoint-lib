import os
import json
from datetime import datetime, timedelta
from chargepoint_dal import ChargePointDAL
from vehicle_classifier import VehicleClassifier
from threading import Lock
from .utils import daterange, load_session_map, save_session_map

SESSION_MAP_PATH = "data/session_vehicle_map.json"
LOCK = Lock()

def batch_classify_sessions(args):
    from datetime import timezone
    start_date = datetime.strptime(args.start_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    end_date = datetime.strptime(args.end_date, "%Y-%m-%d").replace(tzinfo=timezone.utc)
    dal = ChargePointDAL(args.username, args.password)
    classifier = VehicleClassifier()
    session_map = load_session_map(SESSION_MAP_PATH)
    updated = False
    from vehicle_classifier.vehicle_manager import VehicleManager
    from .utils import filter_vehicles_by_date
    vehicle_manager = VehicleManager()
    all_vehicles = vehicle_manager.get_all_vehicles()
    from datetime import timezone


    # Build a set of (year, month) tuples in the date range
    months = set()
    for single_date in daterange(start_date, end_date):
        months.add((single_date.year, single_date.month))

    sessions_by_month = {}
    for year, month in sorted(months):
        print(f"Fetching sessions for {year}-{month:02d}")
        sessions_by_month[(year, month)] = dal.get_sessions(year=year, month=month)

    processed_sessions = set()
    for year, month in sorted(months):
        sessions = sessions_by_month.get((year, month), [])
        for session in sessions:
            session_id = str(session.get("session_id") or session.get("sessionId"))
            if not session_id or session_id in processed_sessions:
                continue
            processed_sessions.add(session_id)
            activity = dal.get_session_activity(session_id)
            if not activity:
                print(f"  [!] No activity for session {session_id}")
                continue
            # Determine session date (use start_time or similar field)
            session_time = None
            for k in ("start_time", "session_start_time", "collection_start"):
                if k in session:
                    session_time = session[k]
                    break
            if not session_time:
                print(f"  [!] No session time for session {session_id}")
                continue
            # Parse session_time to datetime
            try:
                if isinstance(session_time, int):
                    session_dt = datetime.fromtimestamp(session_time / 1000, tz=timezone.utc)
                else:
                    session_dt = datetime.fromisoformat(session_time.replace("Z", "+00:00"))
            except Exception as e:
                print(f"  [!] Could not parse session time for {session_id}: {e}")
                continue
            # Filter vehicles by valid_periods
            eligible_vehicles = filter_vehicles_by_date(all_vehicles, session_dt)
            # Get charger/device_id
            charger_id = session.get("device_id") or session.get("deviceId")
            # Classify with context
            power_samples = activity.get("power_samples") or activity.get("samples")
            if not power_samples:
                # Try update_data as fallback (top-level or under charging_status)
                update_data = activity.get("update_data")
                if not update_data and "charging_status" in activity:
                    update_data = activity["charging_status"].get("update_data")
                if update_data and isinstance(update_data, list) and len(update_data) > 0:
                    # Convert update_data to a list of floats (power_kw) for classifier
                    power_samples = [
                        float(d.get("power_kw", 0.0))
                        for d in update_data if "power_kw" in d
                    ]
                if not power_samples or len(power_samples) == 0:
                    print(f"  [!] No power samples for session {session_id}")
                    continue
            vehicle, confidence = classifier.predict(power_samples, eligible_vehicles, charger_id)
            print(f"  Session {session_id}: {vehicle} (confidence={confidence:.3f})")
            if confidence >= args.min_confidence:
                if args.update_map:
                    with LOCK:
                        session_map["sessions"][session_id] = {
                            "vehicle": vehicle,
                            "confidence": confidence,
                            "source": "classifier",
                            "labeled_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                        }
                        updated = True
            elif args.label_unknown:
                if args.update_map:
                    with LOCK:
                        session_map["sessions"][session_id] = {
                            "vehicle": "Unknown",
                            "confidence": confidence,
                            "source": "classifier",
                            "labeled_at": datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
                        }
                        if session_id not in session_map.get("unknown_sessions", []):
                            session_map.setdefault("unknown_sessions", []).append(session_id)
                        updated = True

    if updated and args.update_map:
        session_map["last_updated"] = datetime.now(timezone.utc).isoformat().replace("+00:00", "Z")
        save_session_map(session_map, SESSION_MAP_PATH)
        print("Session vehicle map updated.")
    else:
        print("No updates made to session vehicle map.")

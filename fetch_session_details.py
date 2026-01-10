#!/usr/bin/env python3
"""
Fetch complete ChargePoint session data and cache locally for history display.

Usage: 
    python fetch_session_details.py <session_id>              # Fetch single session
    python fetch_session_details.py --month YYYY-MM           # Fetch entire month
    python fetch_session_details.py --current                 # Fetch current month to now

This script:
1. Authenticates with ChargePoint
2. Fetches complete session data via ChargePoint API
3. Merges vehicle classification from data/sessions/{date}/{id}.json
4. Saves to data/session_cache/YYYY-MM.json (organized by month)
5. Git commits the monthly cache file

The cached monthly files contain minimal session objects with:
- session_id, start_time, end_time, energy_kwh
- vehicle ID and classifier confidence

This allows the history.html page to display comprehensive charging data
without making repeated ChargePoint API calls. Monthly organization allows
efficient loading of month/year views.
"""

import os
import sys
import json
import subprocess
from datetime import datetime, timedelta
from dotenv import load_dotenv

# Load environment variables from .env
load_dotenv()

try:
    from chargepoint.client import ChargePoint
except ImportError:
    print("ERROR: python-chargepoint library not found")
    print("Install with: pip install python-chargepoint")
    sys.exit(1)


def fetch_session_details(session_id):
    """
    Fetch ChargePoint session data and cache minimal metrics locally.
    
    Creates minimal monthly cache files with only essential data for history display:
    - session_id, start_time, end_time, energy_kwh
    - vehicle ID and classifier confidence
    
    Args:
        session_id (str): ChargePoint session ID
        
    Returns:
        dict: Minimal session data for cache
    """
    
    # Get credentials from environment
    username = os.getenv('CP_USERNAME')
    password = os.getenv('CP_PASSWORD')
    
    if not username or not password:
        print("ERROR: CP_USERNAME and CP_PASSWORD environment variables required")
        sys.exit(1)
    
    print(f"[fetch_session_details] Fetching session {session_id}...")
    
    try:
        # Authenticate with ChargePoint
        client = ChargePoint(username=username, password=password)
        
        # Fetch the session
        session_obj = client.get_charging_session(session_id)
        
        # Extract session start time for organizing by month
        session_start = datetime.fromisoformat(session_obj.session_start_time.isoformat())
        year = session_start.year
        month = session_start.month
        
        # Create minimal cache structure (only what history.html needs)
        session_dict = {
            "session_id": session_id,
            "session_start_time": session_obj.session_start_time.isoformat(),
            "session_end_time": session_obj.session_end_time.isoformat() if session_obj.session_end_time else None,
            "energy_kwh": float(session_obj.energy_kwh) if session_obj.energy_kwh else None,
            "vehicle": {
                "id": None,
                "confidence": None
            }
        }
        
        # Try to merge vehicle classification from collection data
        # Classification files are organized by date: data/sessions/YYYY/MM/DD/{session_id}.json
        # Try multiple possible date paths (session might span dates)
        for date_offset in range(-1, 2):  # Try day before, same day, day after
            possible_date = session_start + timedelta(days=date_offset)
            classification_path = f"data/sessions/{possible_date.year:04d}/{possible_date.month:02d}/{possible_date.day:02d}/{session_id}.json"
            
            if os.path.exists(classification_path):
                print(f"[fetch_session_details] Merging classification from {classification_path}")
                with open(classification_path, 'r') as f:
                    classification_data = json.load(f)
                    if "vehicle_id" in classification_data:
                        session_dict["vehicle"]["id"] = classification_data["vehicle_id"]
                    if "vehicle_confidence" in classification_data:
                        session_dict["vehicle"]["confidence"] = classification_data["vehicle_confidence"]
                break
        
        # Organize cache by month: data/session_cache/YYYY-MM.json
        cache_dir = f"data/session_cache"
        os.makedirs(cache_dir, exist_ok=True)
        
        cache_file = f"{cache_dir}/{year:04d}-{month:02d}.json"
        
        # Read existing sessions for this month
        sessions = []
        if os.path.exists(cache_file):
            print(f"[fetch_session_details] Loading existing {cache_file}")
            with open(cache_file, 'r') as f:
                sessions = json.load(f)
        
        # Check if session already exists (avoid duplicates)
        existing_index = next((i for i, s in enumerate(sessions) if s["session_id"] == session_id), None)
        
        if existing_index is not None:
            print(f"[fetch_session_details] Updating existing session at index {existing_index}")
            sessions[existing_index] = session_dict
        else:
            print(f"[fetch_session_details] Adding new session to {cache_file}")
            sessions.append(session_dict)
        
        # Write atomically: write to temp file, then rename
        temp_file = f"{cache_file}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(sessions, f, indent=2)
        
        os.rename(temp_file, cache_file)
        print(f"[fetch_session_details] Saved {len(sessions)} sessions to {cache_file}")
        
        # Git commit
        try:
            subprocess.run(["git", "add", cache_file], cwd=".", check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Cache: {len(sessions)} sessions for {year:04d}-{month:02d}"],
                cwd=".",
                check=True
            )
            print(f"[fetch_session_details] Committed to git")
        except subprocess.CalledProcessError as e:
            print(f"[fetch_session_details] WARNING: Git commit failed: {e}")
            # Don't fail the entire operation if git fails
        
        return session_dict
        if os.path.exists(cache_file):
            print(f"[fetch_session_details] Loading existing {cache_file}")
            with open(cache_file, 'r') as f:
                sessions = json.load(f)
        
        # Check if session already exists (avoid duplicates)
        existing_index = next((i for i, s in enumerate(sessions) if s["session_id"] == session_id), None)
        
        if existing_index is not None:
            print(f"[fetch_session_details] Updating existing session at index {existing_index}")
            sessions[existing_index] = session_dict
        else:
            print(f"[fetch_session_details] Adding new session to {cache_file}")
            sessions.append(session_dict)
        
        # Write atomically: write to temp file, then rename
        temp_file = f"{cache_file}.tmp"
        with open(temp_file, 'w') as f:
            json.dump(sessions, f, indent=2)
        
        os.rename(temp_file, cache_file)
        print(f"[fetch_session_details] Saved {len(sessions)} sessions to {cache_file}")
        
        # Git commit
        try:
            subprocess.run(["git", "add", cache_file], cwd=".", check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Cache: {len(sessions)} sessions for {year:04d}-{month:02d}"],
                cwd=".",
                check=True
            )
            print(f"[fetch_session_details] Committed to git")
        except subprocess.CalledProcessError as e:
            print(f"[fetch_session_details] WARNING: Git commit failed: {e}")
            # Don't fail the entire operation if git fails
        
        return session_dict
        
    except Exception as e:
        print(f"ERROR: Failed to fetch session {session_id}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


def fetch_month_sessions(year, month, up_to_now=False):
    """
    Fetch all charging sessions for a specific month from ChargePoint.
    
    Args:
        year (int): Year (e.g., 2026)
        month (int): Month (1-12)
        up_to_now (bool): If True, only fetch sessions up to current time (for current month)
        
    Returns:
        list: List of processed session dicts
    """
    username = os.getenv('CP_USERNAME')
    password = os.getenv('CP_PASSWORD')
    
    if not username or not password:
        print("ERROR: CP_USERNAME and CP_PASSWORD environment variables required")
        sys.exit(1)
    
    # Calculate date range
    start_date = datetime(year, month, 1)
    
    if up_to_now:
        end_date = datetime.now()
        print(f"[fetch_month_sessions] Fetching sessions from {start_date.date()} to now...")
    else:
        # Last day of month
        if month == 12:
            end_date = datetime(year + 1, 1, 1) - timedelta(days=1)
        else:
            end_date = datetime(year, month + 1, 1) - timedelta(days=1)
        end_date = end_date.replace(hour=23, minute=59, second=59)
        print(f"[fetch_month_sessions] Fetching all sessions for {year}-{month:02d}...")
    
    try:
        client = ChargePoint(username=username, password=password)
        
        # Get all sessions in date range
        sessions = client.get_sessions(start_time=start_date, end_time=end_date)
        print(f"[fetch_month_sessions] Found {len(sessions)} sessions from ChargePoint")
        
        # Process each session
        results = []
        for session_id in sessions:
            try:
                result = fetch_session_details(session_id)
                if result:
                    results.append(result)
            except Exception as e:
                print(f"[fetch_month_sessions] WARNING: Failed to fetch session {session_id}: {e}")
                continue
        
        print(f"[fetch_month_sessions] Successfully processed {len(results)}/{len(sessions)} sessions")
        return results
        
    except Exception as e:
        print(f"ERROR: Failed to fetch sessions for {year}-{month:02d}: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        print("Usage:")
        print("  python fetch_session_details.py <session_id>        # Fetch single session")
        print("  python fetch_session_details.py --month YYYY-MM     # Fetch entire month")
        print("  python fetch_session_details.py --current           # Fetch current month to now")
        print("")
        print("Examples:")
        print("  python fetch_session_details.py abc123xyz")
        print("  python fetch_session_details.py --month 2026-01")
        print("  python fetch_session_details.py --current")
        sys.exit(1)
    
    arg = sys.argv[1]
    
    if arg == "--current":
        # Fetch current month up to now
        now = datetime.now()
        results = fetch_month_sessions(now.year, now.month, up_to_now=True)
        print(f"\n✅ Cached {len(results)} sessions for {now.year}-{now.month:02d}")
        
    elif arg == "--month":
        # Fetch entire month
        if len(sys.argv) < 3:
            print("ERROR: --month requires YYYY-MM argument")
            print("Example: python fetch_session_details.py --month 2026-01")
            sys.exit(1)
        
        month_str = sys.argv[2]
        try:
            year, month = map(int, month_str.split('-'))
            results = fetch_month_sessions(year, month, up_to_now=False)
            print(f"\n✅ Cached {len(results)} sessions for {year}-{month:02d}")
        except ValueError:
            print(f"ERROR: Invalid month format: {month_str}")
            print("Expected format: YYYY-MM (e.g., 2026-01)")
            sys.exit(1)
    
    else:
        # Single session fetch
        session_id = arg
        result = fetch_session_details(session_id)
        print(json.dumps(result, indent=2))

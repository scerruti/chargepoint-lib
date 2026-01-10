#!/usr/bin/env python3
"""
Fetch complete ChargePoint session data and cache locally for history display.

Usage: 
    python fetch_session_details.py <session_id>          # Single session
    python fetch_session_details.py --bulk                # Fetch all sessions via API
    python fetch_session_details.py --month YYYY-MM       # Specific month

This script:
1. Authenticates with ChargePoint
2. Fetches session data via ChargePoint API
3. Merges vehicle classification from data/sessions/{date}/{id}.json
4. Saves to data/session_cache/YYYY-MM.json (organized by month)
5. Git commits the monthly cache file

The cached monthly files contain minimal session objects with:
- session_id, start_time, end_time, energy_kwh
- vehicle ID and classifier confidence

This allows the history.html page to display comprehensive charging data
without making repeated ChargePoint API calls.

Uses direct API to support:
- Session history queries via /map-prod/v2 endpoint
- Bulk session fetching from ChargePoint
"""

import os
import sys
import json
import subprocess
import argparse
from datetime import datetime, timedelta
from dotenv import load_dotenv
from pathlib import Path

# Load environment variables from .env
load_dotenv()

try:
    from chargepoint_api import ChargePointDirectAPI
except ImportError:
    print("ERROR: chargepoint_api module not found")
    print("Make sure chargepoint_api.py is in the same directory")
    sys.exit(1)


def cache_session(session_id, session_data):
    """
    Cache a session to the monthly cache file and commit to git.
    
    Args:
        session_id: ChargePoint session ID
        session_data: Session data dict
    
    Returns:
        True if successful, False otherwise
    """
    try:
        # Extract start time to determine month
        if isinstance(session_data, dict):
            if "session_start_time" in session_data:
                start_time_str = session_data["session_start_time"]
            elif "start_time" in session_data:
                start_time_str = session_data["start_time"]
            else:
                print(f"ERROR: No start time in session data")
                return False
        else:
            start_time_str = getattr(session_data, 'session_start_time', None)
            if not start_time_str:
                start_time_str = getattr(session_data, 'start_time', None)
        
        session_start = datetime.fromisoformat(str(start_time_str).replace('Z', '+00:00'))
        year = session_start.year
        month = session_start.month
        
        # Create minimal cache structure
        if isinstance(session_data, dict):
            session_dict = {
                "session_id": session_id,
                "session_start_time": session_data.get("session_start_time") or session_data.get("start_time"),
                "session_end_time": session_data.get("session_end_time") or session_data.get("end_time"),
                "energy_kwh": float(session_data.get("energy_kwh", 0)) if session_data.get("energy_kwh") else None,
                "vehicle": {"id": None, "confidence": None}
            }
        else:
            session_dict = {
                "session_id": session_id,
                "session_start_time": start_time_str,
                "session_end_time": getattr(session_data, 'session_end_time', None),
                "energy_kwh": float(getattr(session_data, 'energy_kwh', 0)) if getattr(session_data, 'energy_kwh', None) else None,
                "vehicle": {"id": None, "confidence": None}
            }
        
        # Try to merge vehicle classification from collection data
        for date_offset in range(-1, 2):
            possible_date = session_start + timedelta(days=date_offset)
            session_data_path = Path(f"data/sessions/{possible_date.year:04d}/{possible_date.month:02d}/{possible_date.day:02d}/{session_id}.json")
            
            if session_data_path.exists():
                try:
                    with open(session_data_path, 'r') as f:
                        collection_data = json.load(f)
                        if "classification" in collection_data:
                            vehicle_data = collection_data["classification"]
                            session_dict["vehicle"] = {
                                "id": vehicle_data.get("vehicle_id"),
                                "confidence": vehicle_data.get("confidence")
                            }
                            break
                except Exception as e:
                    pass
        
        # Save to monthly cache
        cache_dir = Path(f"data/session_cache/{year:04d}/{month:02d}")
        cache_dir.mkdir(parents=True, exist_ok=True)
        
        cache_file = cache_dir / f"{year:04d}-{month:02d}.json"
        sessions = []
        
        if cache_file.exists():
            try:
                with open(cache_file, 'r') as f:
                    data = json.load(f)
                    sessions = data if isinstance(data, list) else data.get("sessions", [])
            except Exception as e:
                print(f"Warning: Could not load existing cache {cache_file}: {e}")
        
        # Add or update session
        existing_ids = {s["session_id"] for s in sessions}
        if session_id not in existing_ids:
            sessions.append(session_dict)
        else:
            for i, s in enumerate(sessions):
                if s["session_id"] == session_id:
                    sessions[i] = session_dict
                    break
        
        # Write cache file
        with open(cache_file, 'w') as f:
            json.dump(sessions, f, indent=2)
        print(f"✓ Cached session {session_id} to {cache_file}")
        
        # Commit to git
        try:
            subprocess.run(["git", "add", str(cache_file)], cwd=".", check=True, capture_output=True)
            subprocess.run(
                ["git", "commit", "-m", f"Cache: session {session_id}"],
                cwd=".",
                check=True,
                capture_output=True
            )
        except subprocess.CalledProcessError:
            pass
        
        return True
    
    except Exception as e:
        print(f"ERROR: Could not cache session: {e}")
        return False


def fetch_single_session(session_id):
    """Fetch and cache a single session by ID."""
    username = os.getenv('CP_USERNAME')
    password = os.getenv('CP_PASSWORD')
    
    if not username or not password:
        print("ERROR: CP_USERNAME and CP_PASSWORD environment variables required")
        sys.exit(1)
    
    print(f"[fetch_session_details] Fetching session {session_id}...")
    
    try:
        client = ChargePointDirectAPI(username=username, password=password)
        session_obj = client.get_session_details(session_id)
        
        if not session_obj:
            print(f"ERROR: Could not fetch session {session_id}")
            return False
        
        return cache_session(session_id, session_obj)
    
    except Exception as e:
        print(f"ERROR: {e}")
        return False


def fetch_all_sessions():
    """Fetch all sessions from ChargePoint via API and cache."""
    username = os.getenv('CP_USERNAME')
    password = os.getenv('CP_PASSWORD')
    
    if not username or not password:
        print("ERROR: CP_USERNAME and CP_PASSWORD environment variables required")
        sys.exit(1)
    
    print("[fetch_session_details] Fetching all charging sessions from ChargePoint...")
    
    try:
        client = ChargePointDirectAPI(username=username, password=password)
        
        # Fetch all charging activity pages (handles pagination)
        sessions = client.get_session_history_paginated(page_size=200, max_pages=30)
        
        if not sessions:
            print("WARNING: No sessions found in activity data")
            return False
        
        print(f"[fetch_session_details] Found {len(sessions)} sessions to cache")
        
        # Cache each session
        cached_count = 0
        for session in sessions:
            session_id = session.get("session_id") or session.get("sessionId")
            if session_id:
                if cache_session(session_id, session):
                    cached_count += 1
        
        print(f"[fetch_session_details] Successfully cached {cached_count}/{len(sessions)} sessions")
        return cached_count > 0
    
    except Exception as e:
        print(f"ERROR: {e}")
        import traceback
        traceback.print_exc()
        return False


def fetch_month_sessions(year, month):
    """Fetch sessions for a specific month from local filesystem."""
    try:
        from backfill_cache import find_session_ids
        
        print(f"[fetch_session_details] Fetching sessions for {year:04d}-{month:02d}")
        
        all_sessions = find_session_ids(year=year, month=month)
        
        if not all_sessions:
            print(f"No sessions found for {year:04d}-{month:02d}")
            return False
        
        print(f"Found {len(all_sessions)} sessions to fetch")
        
        cached_count = 0
        for y, m, d, session_id in all_sessions:
            if fetch_single_session(session_id):
                cached_count += 1
        
        print(f"Successfully cached {cached_count}/{len(all_sessions)} sessions")
        return cached_count > 0
    
    except ImportError:
        print("ERROR: Could not import backfill_cache module")
        return False


if __name__ == "__main__":
    parser = argparse.ArgumentParser(
        description="Fetch ChargePoint session data and cache locally"
    )
    
    parser.add_argument(
        "session_id",
        nargs="?",
        help="Session ID to fetch"
    )
    
    parser.add_argument(
        "--bulk",
        action="store_true",
        help="Fetch ALL sessions from ChargePoint API"
    )
    
    parser.add_argument(
        "--month",
        help="Fetch sessions for specific month (YYYY-MM format)"
    )
    
    args = parser.parse_args()
    
    if args.session_id:
        fetch_single_session(args.session_id)
    elif args.bulk:
        fetch_all_sessions()
    elif args.month:
        try:
            month_dt = datetime.strptime(args.month, "%Y-%m")
            fetch_month_sessions(month_dt.year, month_dt.month)
        except ValueError:
            print(f"ERROR: Invalid month format '{args.month}'. Use YYYY-MM")
            sys.exit(1)
    else:
        parser.print_help()
        sys.exit(1)

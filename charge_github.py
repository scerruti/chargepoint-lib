#!/usr/bin/env python3
"""
GitHub Actions EV Charging Automation
Runs on cron schedule to start charging at 6 AM PST/PDT
"""

import os
import sys
import time
import json
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from python_chargepoint import ChargePoint
from python_chargepoint.exceptions import ChargePointCommunicationException


def record_run_result(result, reason, polling_duration_sec=0):
    """Append charging run result to data/runs.json and commit to repo."""
    pacific = ZoneInfo("America/Los_Angeles")
    now_utc = datetime.now(ZoneInfo('UTC'))
    now_pt = datetime.now(pacific)
    
    run_record = {
        "run_id": os.environ.get("GITHUB_RUN_ID", "unknown"),
        "date": now_pt.strftime("%Y-%m-%d"),
        "time_utc": now_utc.strftime("%H:%M:%S"),
        "time_pt": now_pt.strftime("%H:%M:%S"),
        "result": result,  # "success" or "failure"
        "start_time_pt": now_pt.strftime("%H:%M:%S"),
        "polling_duration_sec": polling_duration_sec,
        "reason": reason,
        "details": ""
    }
    
    data_file = "data/runs.json"
    
    try:
        # Load existing data
        if os.path.exists(data_file):
            with open(data_file, 'r') as f:
                data = json.load(f)
        else:
            data = {"runs": []}
        
        # Append new record
        data["runs"].append(run_record)
        
        # Write back
        with open(data_file, 'w') as f:
            json.dump(data, f, indent=2)
        
        print(f"✓ Recorded run result: {result} ({reason})")
        
        # Git commit and push
        try:
            subprocess.run(["git", "config", "user.name", "GitHub Actions"], check=True, capture_output=True)
            subprocess.run(["git", "config", "user.email", "actions@github.com"], check=True, capture_output=True)
            subprocess.run(["git", "add", data_file], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Record charging run: {result}"], check=True, capture_output=True)
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print("✓ Committed and pushed run data")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not commit run data: {e}")
            # Don't fail the job if git commit fails
    except Exception as e:
        print(f"⚠️  Warning: Could not record run data: {e}")
        # Don't fail the job if data logging fails


def wait_for_scheduled_charging_to_end(client, charger_id):
    """Poll charger status from 5:50-6:05 PT until scheduled charging ends (clock-drift resistant).
    
    Returns True when scheduled charging ends or window expires, False if error.
    """
    pacific = ZoneInfo("America/Los_Angeles")
    window_start = 5 * 60 + 50  # 5:50 AM in minutes
    window_end = 6 * 60 + 5    # 6:05 AM in minutes
    poll_interval = 20  # seconds
    
    print("⏳ Polling for scheduled charging end (5:50–6:05 PT window)...")
    window_start_time = datetime.now(pacific).replace(hour=5, minute=50, second=0, microsecond=0)
    window_end_time = datetime.now(pacific).replace(hour=6, minute=5, second=0, microsecond=0)
    
    # If before window, wait until 5:50
    now = datetime.now(pacific)
    if now < window_start_time:
        wait_secs = (window_start_time - now).total_seconds()
        print(f"   Early start: waiting {int(wait_secs)}s until 5:50 AM PT...")
        time.sleep(wait_secs)
    
    # Poll within 5:50–6:05 window
    poll_count = 0
    while True:
        now = datetime.now(pacific)
        
        # Exit window check
        if now > window_end_time:
            print(f"✓ 6:05 AM PT reached; proceeding with charging attempt")
            return True
        
        # Fetch status
        poll_count += 1
        try:
            status = client.get_home_charger_status(charger_id)
        except Exception as e:
            print(f"⚠️  Status check #{poll_count} failed: {e}")
            time.sleep(poll_interval)
            continue
        
        current_time = now.strftime("%H:%M")
        charging_status = status.charging_status
        print(f"   [{poll_count}] {current_time} PT – Status: {charging_status}")
        
        # Check if unplugged
        if not status.plugged_in:
            print("ℹ️  Vehicle unplugged during poll - proceeding to charge")
            return True
        
        # Success: scheduled charging ended
        if charging_status != "CHARGING":
            print(f"✓ Scheduled charging ended at {current_time} PT (status: {charging_status})")
            return True
        
        # Still charging, wait and poll again
        time.sleep(poll_interval)
    
    return True


def charge():
    """Main charging logic with wait-for-scheduled-charging-to-end. Returns True on success, False on failure."""
    username = os.environ.get("CP_USERNAME")
    password = os.environ.get("CP_PASSWORD")
    station_id = os.environ.get("CP_STATION_ID")
    
    if not all([username, password, station_id]):
        print("❌ ERROR: Missing required environment variables")
        print("   Required: CP_USERNAME, CP_PASSWORD, CP_STATION_ID")
        return False
    
    try:
        # Authenticate
        print(f"🔐 Authenticating as {username}...")
        client = ChargePoint(username=username, password=password)
        print("✓ Authentication successful")
        
        # Get home chargers
        print("🔍 Fetching home chargers...")
        chargers = client.get_home_chargers()
        
        if not chargers:
            print("❌ ERROR: No home chargers found")
            return False
        
        charger_id = chargers[0]
        print(f"✓ Found charger: {charger_id}")
        
        # Step 1: Check if car is plugged in
        status = client.get_home_charger_status(charger_id)
        print(f"📊 Initial Status:")
        print(f"   Connected: {status.connected}")
        print(f"   Plugged In: {status.plugged_in}")
        print(f"   Charging Status: {status.charging_status}")
        
        if not status.connected:
            print("⚠️  Charger is offline - cannot start charging")
            return False  # Fail so GitHub sends alert email
        
        if not status.plugged_in:
            print("ℹ️  No vehicle plugged in - nothing to do")
            return True  # Success: nothing wrong, just nothing to charge
        
        # Step 2: Poll for scheduled charging to end (5:50–6:05 PT window, clock-drift resistant)
        if not wait_for_scheduled_charging_to_end(client, charger_id):
            return False
        
        # Verify car still plugged after polling window
        status = client.get_home_charger_status(charger_id)
        if not status.plugged_in:
            print("ℹ️  Vehicle unplugged after polling window - exiting")
            return True
        
        if status.charging_status == "CHARGING":
            print("⚠️  WARNING: Scheduled charging still active after 6:05 PT window")
            print("   Proceeding anyway (may be holiday or extended schedule)")
        
        # Step 3: Start charging (with exponential backoff retries)
        print(f"\n⚡ Starting charging session for station {station_id}...")
        start_attempt_time = datetime.now(pacific).strftime("%H:%M:%S")
        print(f"   Start time: {start_attempt_time} PT")
        
        backoff_delays = [5, 10, 20]  # Exponential backoff: 5s, 10s, 20s
        
        for retry in range(1, 4):  # Up to 3 attempts
            try:
                client.start_charging_session(station_id)
                success_time = datetime.now(pacific).strftime("%H:%M:%S")
                print(f"✅ SUCCESS: Charging session started at {success_time} PT!")
                return True
                
            except ChargePointCommunicationException as timeout_error:
                if "failed to start in time allotted" in str(timeout_error).lower():
                    print(f"⚠️  Timeout on attempt {retry}/3")
                    
                    # Wait with exponential backoff
                    backoff_sec = backoff_delays[retry - 1]
                    print(f"   Waiting {backoff_sec}s before status check...")
                    time.sleep(backoff_sec)
                    
                    try:
                        status = client.get_home_charger_status(charger_id)
                    except Exception as check_error:
                        print(f"   ⚠️  Status check failed: {check_error}")
                        if retry < 3:
                            print(f"   Retrying... ({retry}/3)")
                            continue
                        else:
                            print("❌ ERROR: All retries exhausted and cannot confirm charging")
                            return False
                    
                    # Check car still plugged
                    if not status.plugged_in:
                        print("ℹ️  Vehicle unplugged - exiting")
                        return True
                    
                    # Check if charging actually started
                    if status.charging_status == "CHARGING":
                        print(f"✅ Charging confirmed active at {datetime.now(pacific).strftime('%H:%M:%S')} PT (timeout was false alarm)")
                        return True
                    
                    # Not charging yet, retry if attempts remain
                    if retry < 3:
                        print(f"   Charging not detected, retrying... ({retry}/3)")
                        continue
                    else:
                        print("❌ ERROR: 3 attempts failed, charging not confirmed")
                        return False
                else:
                    raise  # Other communication errors
        
    except ChargePointCommunicationException as e:
        print(f"❌ ERROR: ChargePoint API communication failed")
        print(f"   {str(e)}")
        return False
    except Exception as e:
        print(f"❌ ERROR: Unexpected error occurred")
        print(f"   {type(e).__name__}: {str(e)}")
        return False


def main():
    """Entry point for GitHub Actions."""
    print("=" * 60)
    print("EV Charging Automation - GitHub Actions")
    utc_time = datetime.now(ZoneInfo('UTC')).strftime('%Y-%m-%d %H:%M:%S %Z')
    local_time = datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M:%S %Z')
    print(f"Run Time (UTC):  {utc_time}")
    print(f"Run Time (PT):   {local_time}")
    print("=" * 60)
    
    # Check if past charging window
    pacific = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific)
    if now.hour > 6:
        print(f"ℹ️  Past charging window (current hour: {now.hour}, target: 5:50–6:05) - exiting")
        record_run_result("success", "Skipped: past charging window")
        sys.exit(0)
    
    print("🎯 Within charging window, proceeding...")
    
    # Attempt to charge
    success = charge()
    
    if success:
        print("=" * 60)
        print("✅ Charging automation completed successfully")
        print("=" * 60)
        record_run_result("success", "Charging session started successfully")
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ Charging automation failed - see errors above")
        print("=" * 60)
        record_run_result("failure", "Charging session failed - see logs")
        sys.exit(1)


if __name__ == "__main__":
    main()

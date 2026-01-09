#!/usr/bin/env python3
"""
GitHub Actions EV Charging Automation
Runs on cron schedule to start charging at 6 AM PST/PDT
"""

import os
import sys
import time
from datetime import datetime
from zoneinfo import ZoneInfo
from python_chargepoint import ChargePoint
from python_chargepoint.exceptions import ChargePointCommunicationException


def wait_until_charge_window():
    """If run before 5:59 AM PT, sleep until exactly 5:59 AM PT."""
    pacific = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific)
    target = now.replace(hour=5, minute=59, second=0, microsecond=0)

    # If already at/after 5:59 AM PT, only proceed if before 6:05 AM, otherwise exit
    if now >= target:
        if now.hour == 5 or (now.hour == 6 and now.minute < 5):
            return True
        print(f"ℹ️  Past charging window (current local time: {now.strftime('%H:%M')}, target: 05:59) - exiting")
        return False

    # Wait until 5:59 AM PT
    wait_seconds = (target - now).total_seconds()
    print(f"⏳ Early start detected, waiting {int(wait_seconds)}s until 5:59 AM PT...")
    time.sleep(wait_seconds)
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
            print("⚠️  Charger is offline - exiting")
            return False
        
        if not status.plugged_in:
            print("ℹ️  No vehicle plugged in - nothing to do")
            return True  # Success: nothing wrong, just nothing to charge
        
        # Step 2: Wait for scheduled charging to end (up to 5 minutes)
        if status.charging_status == "CHARGING":
            print("\n⏳ Scheduled charging detected - waiting for it to end...")
            for attempt in range(1, 16):  # 15 attempts = 5 minutes
                print(f"   Wait check {attempt}/15 (20s intervals)...")
                time.sleep(20)
                
                status = client.get_home_charger_status(charger_id)
                
                # Check if unplugged during wait
                if not status.plugged_in:
                    print("ℹ️  Vehicle unplugged during wait - exiting")
                    return True
                
                # Check if charging stopped
                if status.charging_status != "CHARGING":
                    print(f"✓ Scheduled charging ended (status: {status.charging_status})")
                    break
            else:
                # Still charging after 12 checks
                print("ℹ️  Scheduled charging still active after 4 minutes")
                print("   (May be a holiday or extended schedule - exiting)")
                return True  # Success: scheduled charging still running, that's fine
        
        # Step 3: Start charging (with retry logic for timeouts)
        print(f"\n⚡ Starting charging session for station {station_id}...")
        
        for retry in range(1, 4):  # Up to 3 attempts
            try:
                client.start_charging_session(station_id)
                print("✅ SUCCESS: Charging session started!")
                return True
                
            except ChargePointCommunicationException as timeout_error:
                if "failed to start in time allotted" in str(timeout_error).lower():
                    print(f"⚠️  Timeout on attempt {retry}/3 - checking if charging started...")
                    time.sleep(20)
                    
                    status = client.get_home_charger_status(charger_id)
                    
                    if not status.plugged_in:
                        print("ℹ️  Vehicle unplugged - exiting")
                        return True
                    
                    if status.charging_status == "CHARGING":
                        print("✅ Charging confirmed active (timeout was expected)")
                        return True
                    
                    if retry < 3:
                        print(f"   Charging not detected, retrying ({retry}/3)...")
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
    print(f"Run Time (UTC): {datetime.now(ZoneInfo('UTC')).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Run Time (PST): {datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 60)
    
    # Wait until 6 AM PT if we were triggered at 5 AM to cover DST
    if not wait_until_charge_window():
        print("Exiting normally")
        sys.exit(0)
    
    print("🎯 It's 6 AM PT - initiating charge sequence...")
    
    # Attempt to charge
    success = charge()
    
    if success:
        print("=" * 60)
        print("✅ Charging automation completed successfully")
        print("=" * 60)
        sys.exit(0)
    else:
        print("=" * 60)
        print("❌ Charging automation failed - see errors above")
        print("=" * 60)
        sys.exit(1)


if __name__ == "__main__":
    main()

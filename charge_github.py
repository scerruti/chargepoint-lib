#!/usr/bin/env python3
"""
GitHub Actions EV Charging Automation
Runs on cron schedule to start charging at 6 AM PST/PDT
"""

import os
import sys
from datetime import datetime
from zoneinfo import ZoneInfo
from python_chargepoint import ChargePoint
from python_chargepoint.exceptions import ChargePointCommunicationException


def should_charge_now():
    """Check if current time in America/Los_Angeles is 6 AM (hour 6)."""
    pacific = ZoneInfo("America/Los_Angeles")
    now = datetime.now(pacific)
    return now.hour == 6


def charge():
    """Main charging logic. Returns True on success, False on failure."""
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
        
        # Check charger status
        status = client.get_home_charger_status(charger_id)
        print(f"📊 Charger Status:")
        print(f"   Connected: {status.connected}")
        print(f"   Plugged In: {status.plugged_in}")
        print(f"   Model: {status.model}")
        print(f"   Last Connected: {status.last_connected_at}")
        
        if not status.connected:
            print("⚠️  WARNING: Charger is offline (not connected to network)")
            print("   Charging cannot start until charger reconnects")
            return False
        
        if not status.plugged_in:
            print("⚠️  WARNING: No vehicle plugged in")
            print("   Charging cannot start until vehicle is connected")
            return False
        
        # Start charging session
        print(f"⚡ Starting charging session for station {station_id}...")
        try:
            client.start_charging_session(station_id)
            print("✅ SUCCESS: Charging session started!")
            return True
        except ChargePointCommunicationException as timeout_error:
            if "failed to start in time allotted" in str(timeout_error).lower():
                print("⚠️  WARNING: API timed out, but charging likely started anyway")
                return True  # Treat as success since this is expected
            else:
                raise
        
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
    
    # Check if it's 6 AM PST
    if not should_charge_now():
        pacific_hour = datetime.now(ZoneInfo("America/Los_Angeles")).hour
        print(f"ℹ️  Not charging time (current hour: {pacific_hour}, target: 6)")
        print("Exiting normally")
        sys.exit(0)
    
    print("🎯 It's 6 AM PST - initiating charge sequence...")
    
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

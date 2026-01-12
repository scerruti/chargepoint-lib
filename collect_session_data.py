#!/usr/bin/env python3
"""
Session Data Collection Script
Collects 5 minutes of charging data (30 samples at 10s intervals) for vehicle identification.
"""

import os
import sys
import json
import time
import subprocess
from datetime import datetime
from zoneinfo import ZoneInfo
from pathlib import Path
from python_chargepoint import ChargePoint
from python_chargepoint.exceptions import ChargePointCommunicationException

# Import classifier - try library first, fall back to local module
try:
    from vehicle_classifier import VehicleClassifier
    CLASSIFIER_AVAILABLE = True
except ImportError:
    try:
        from classify_vehicle import VehicleClassifier
        CLASSIFIER_AVAILABLE = True
    except ImportError:
        CLASSIFIER_AVAILABLE = False


def update_session_vehicle_map(session_id, vehicle_id, vehicle_confidence, source="collector"):
    """
    Update the session_vehicle_map.json with vehicle classification.
    
    Args:
        session_id: ChargePoint session ID
        vehicle_id: Identified vehicle ID (or None for unknown)
        vehicle_confidence: Confidence score 0-1 (or None)
        source: Source of identification (collector, classifier, manual, etc)
    """
    map_file = "data/session_vehicle_map.json"
    
    # Load existing map
    vehicle_map = {"sessions": {}, "unknown_sessions": [], "last_updated": datetime.now(ZoneInfo('UTC')).isoformat()}
    if os.path.exists(map_file):
        try:
            with open(map_file, 'r') as f:
                existing = json.load(f)
                vehicle_map = existing
        except Exception as e:
            print(f"⚠️  Warning: Could not load {map_file}: {e}")
    
    # Update or add session entry
    if vehicle_id:
        vehicle_map["sessions"][session_id] = {
            "vehicle": vehicle_id,
            "confidence": vehicle_confidence or 0.0,
            "source": source,
            "labeled_at": datetime.now(ZoneInfo('UTC')).isoformat()
        }
        # Remove from unknown_sessions if present
        if session_id in vehicle_map["unknown_sessions"]:
            vehicle_map["unknown_sessions"].remove(session_id)
    else:
        if session_id not in vehicle_map["sessions"] and session_id not in vehicle_map["unknown_sessions"]:
            vehicle_map["unknown_sessions"].append(session_id)
    
    # Update statistics
    stats = {}
    for sid, entry in vehicle_map["sessions"].items():
        vehicle = entry.get("vehicle", "unknown")
        stats[vehicle] = stats.get(vehicle, 0) + 1
    stats["unknown"] = len(vehicle_map["unknown_sessions"])
    vehicle_map["statistics"] = {
        "total_sessions": len(vehicle_map["sessions"]) + len(vehicle_map["unknown_sessions"]),
        "labeled_sessions": len(vehicle_map["sessions"]),
        **stats
    }
    
    vehicle_map["last_updated"] = datetime.now(ZoneInfo('UTC')).isoformat()
    
    # Write atomically
    temp_file = f"{map_file}.tmp"
    try:
        with open(temp_file, 'w') as f:
            json.dump(vehicle_map, f, indent=2)
        os.rename(temp_file, map_file)
        print(f"✓ Updated {map_file}")
        
        # Commit to git
        try:
            subprocess.run(["git", "add", map_file], cwd=".", check=True)
            subprocess.run(
                ["git", "commit", "-m", f"Map: session {session_id} vehicle={vehicle_id}"],
                cwd=".",
                check=True
            )
        except subprocess.CalledProcessError:
            # Commit may fail if nothing changed, that's ok
            pass
    except Exception as e:
        print(f"⚠️  Warning: Could not update {map_file}: {e}")


def collect_session_data(session_id):
    """Collect 30 samples of charging data over 5 minutes."""
    print("=" * 60)
    print(f"Session Data Collection: {session_id}")
    start_time = datetime.now(ZoneInfo('UTC'))
    print(f"Start Time (UTC): {start_time.strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print(f"Start Time (PT):  {datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M:%S %Z')}")
    print("=" * 60)
    
    username = os.environ.get("CP_USERNAME")
    password = os.environ.get("CP_PASSWORD")
    
    if not all([username, password]):
        print("❌ ERROR: Missing CP_USERNAME or CP_PASSWORD")
        sys.exit(1)
    
    try:
        # Authenticate
        print(f"🔐 Authenticating as {username}...")
        client = ChargePoint(username=username, password=password)
        print("✓ Authentication successful\n")
        
        # Collect 30 samples at 10-second intervals
        samples = []
        target_samples = 30
        interval_sec = 10
        
        print(f"📊 Collecting {target_samples} samples at {interval_sec}s intervals (total: ~{target_samples * interval_sec}s)")
        print("-" * 60)
        
        for i in range(target_samples):
            sample_start = time.time()
            
            try:
                # Get current charging session data
                status = client.get_charging_session(session_id)
                
                sample = {
                    "sample_number": i + 1,
                    "timestamp": datetime.now(ZoneInfo('UTC')).isoformat(),
                    "timestamp_pt": datetime.now(ZoneInfo('America/Los_Angeles')).strftime('%Y-%m-%d %H:%M:%S %Z'),
                    "session_id": session_id,
                    "power_kw": getattr(status, 'power_kw', None),
                    "energy_kwh": getattr(status, 'energy_kwh', None),
                    "duration_minutes": getattr(status, 'duration_minutes', None),
                    "status": getattr(status, 'status', None),
                }
                
                samples.append(sample)
                
                # Display progress
                power_str = f"{sample['power_kw']:.2f} kW" if sample['power_kw'] else "N/A"
                energy_str = f"{sample['energy_kwh']:.2f} kWh" if sample['energy_kwh'] else "N/A"
                print(f"  [{i+1:2d}/{target_samples}] {sample['timestamp_pt']} | Power: {power_str:>10} | Energy: {energy_str}")
                
            except ChargePointCommunicationException as e:
                print(f"  ⚠️  Sample {i+1} failed: {e}")
                samples.append({
                    "sample_number": i + 1,
                    "timestamp": datetime.now(ZoneInfo('UTC')).isoformat(),
                    "error": str(e)
                })
            
            # Wait for next interval (accounting for API call time)
            if i < target_samples - 1:  # Don't wait after last sample
                elapsed = time.time() - sample_start
                sleep_time = max(0, interval_sec - elapsed)
                if sleep_time > 0:
                    time.sleep(sleep_time)
        
        print("-" * 60)
        end_time = datetime.now(ZoneInfo('UTC'))
        duration = (end_time - start_time).total_seconds()
        print(f"✓ Collection complete: {len(samples)} samples in {duration:.1f}s\n")
        
        # Calculate statistics
        valid_samples = [s for s in samples if 'power_kw' in s and s['power_kw'] is not None]
        if valid_samples:
            powers = [s['power_kw'] for s in valid_samples]
            avg_power = sum(powers) / len(powers)
            max_power = max(powers)
            min_power = min(powers)
            variance = sum((p - avg_power) ** 2 for p in powers) / len(powers)
        
        # Predict vehicle from power samples
        vehicle_id = None
        vehicle_confidence = None
        if CLASSIFIER_AVAILABLE and valid_samples:
            try:
                classifier = VehicleClassifier()
                vehicle_id, vehicle_confidence = classifier.predict(powers)
                if vehicle_id:
                    print(f"🚗 Vehicle Classification: {vehicle_id.upper()} (confidence: {vehicle_confidence:.1%})")
            except Exception as e:
                print(f"⚠️  Vehicle classification failed: {e}")
            
            print()
            print("📈 Statistics:")
            print(f"   Valid Samples: {len(valid_samples)}/{len(samples)}")
            print(f"   Avg Power: {avg_power:.2f} kW")
            print(f"   Max Power: {max_power:.2f} kW")
            print(f"   Min Power: {min_power:.2f} kW")
            print(f"   Variance: {variance:.4f}")
            print()
        
        # Update session_vehicle_map with classification result
        update_session_vehicle_map(session_id, vehicle_id, vehicle_confidence, source="classifier")
        
        # Save to file in date-based directory structure
        # Extract start date from collection_start timestamp
        start_date = start_time.strftime('%Y/%m/%d')
        session_dir = f"data/sessions/{start_date}"
        os.makedirs(session_dir, exist_ok=True)
        output_file = f"{session_dir}/{session_id}.json"
        
        output_data = {
            "session_id": session_id,
            "collection_start": start_time.isoformat(),
            "collection_end": end_time.isoformat(),
            "duration_seconds": duration,
            "sample_count": len(samples),
            "valid_sample_count": len(valid_samples),
            "interval_seconds": interval_sec,
            "samples": samples,
            "statistics": {
                "avg_power_kw": avg_power if valid_samples else None,
                "max_power_kw": max_power if valid_samples else None,
                "min_power_kw": min_power if valid_samples else None,
                "variance": variance if valid_samples else None,
            } if valid_samples else None,
            "vehicle_id": vehicle_id,
            "vehicle_confidence": vehicle_confidence,
            "labeled_by": "classifier" if vehicle_id else None,
            "labeled_at": datetime.now(ZoneInfo('UTC')).isoformat() if vehicle_id else None
        }
        
        with open(output_file, 'w') as f:
            json.dump(output_data, f, indent=2)
        
        print(f"💾 Saved data to {output_file}")
        
        # Commit to git
        try:
            subprocess.run(["git", "add", output_file], check=True, capture_output=True)
            subprocess.run(["git", "commit", "-m", f"Data: collected session {session_id}"], check=True, capture_output=True)
            subprocess.run(["git", "push"], check=True, capture_output=True)
            print("✓ Committed and pushed session data")
        except subprocess.CalledProcessError as e:
            print(f"⚠️  Warning: Could not commit session data: {e}")
        
        print("=" * 60)
        print("✅ Session data collection complete")
        print("=" * 60)
        
    except ChargePointCommunicationException as e:
        print(f"\n❌ ERROR: ChargePoint API communication failed")
        print(f"   {str(e)}")
        sys.exit(1)
    except Exception as e:
        print(f"\n❌ ERROR: Unexpected error occurred")
        print(f"   {type(e).__name__}: {str(e)}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    if len(sys.argv) != 2:
        print("Usage: collect_session_data.py <session_id>")
        sys.exit(1)
    
    session_id = sys.argv[1]
    collect_session_data(session_id)

#!/usr/bin/env python3
"""
Generate weekly charging report from GitHub Actions run logs.
"""

import json
import subprocess
from datetime import datetime, timedelta
from zoneinfo import ZoneInfo

pacific = ZoneInfo("America/Los_Angeles")

# Get all charge-ev runs from past 7 days
cmd = ["gh", "run", "list", "--workflow", "charge-ev.yml", "--limit", "100", 
       "--json", "databaseId,createdAt,conclusion,status"]
result = subprocess.run(cmd, capture_output=True, text=True)
runs = json.loads(result.stdout)

new_records = []
cutoff = datetime.now(pacific) - timedelta(days=7)

for run in runs:
    try:
        run_date = datetime.fromisoformat(run['createdAt'].replace('Z', '+00:00')).astimezone(pacific)
        if run_date < cutoff:
            break
        
        # Fetch full log
        log_cmd = ["gh", "run", "view", str(run["databaseId"]), "--log"]
        log_result = subprocess.run(log_cmd, capture_output=True, text=True, timeout=30)
        log_text = log_result.stdout
        
        # Parse log for key info
        result_status = run['conclusion']
        start_time_pt = 'N/A'
        polling_duration = 0
        reason = ''
        
        if 'SUCCESS: Charging session started' in log_text:
            reason = 'Charging started successfully'
            # Extract timestamp
            for line in log_text.split('\n'):
                if 'Start time:' in line:
                    parts = line.split('Start time:')
                    if len(parts) > 1:
                        start_time_pt = parts[1].strip()
        elif 'Charger is offline' in log_text:
            reason = 'Charger offline'
        elif 'No vehicle plugged in' in log_text:
            reason = 'No vehicle plugged in'
        elif 'Scheduled charging still active' in log_text:
            reason = 'Scheduled charging still active after window'
        elif 'Timeout' in log_text and 'Charging confirmed' in log_text:
            reason = 'Timeout but charging confirmed'
        else:
            reason = result_status
        
        record = {
            'run_id': str(run['databaseId']),
            'date': run_date.strftime('%Y-%m-%d'),
            'time_utc': run_date.astimezone(ZoneInfo('UTC')).strftime('%H:%M:%S'),
            'time_pt': run_date.strftime('%H:%M:%S'),
            'result': result_status,
            'start_time_pt': start_time_pt,
            'polling_duration_sec': polling_duration,
            'reason': reason,
            'details': ''
        }
        new_records.append(record)
    except Exception as e:
        print(f'Error processing run {run.get("databaseId")}: {e}')

# Load existing data
try:
    with open('data/runs.json') as f:
        data = json.load(f)
except:
    data = {'runs': []}

# Append new records (avoid duplicates)
existing_ids = {r['run_id'] for r in data['runs']}
for record in new_records:
    if record['run_id'] not in existing_ids:
        data['runs'].insert(0, record)  # Insert at top (newest first)

# Keep last 52 weeks
data['runs'] = data['runs'][:520]

# Save
with open('data/runs.json', 'w') as f:
    json.dump(data, f, indent=2)

print(f'Updated {len(new_records)} new runs')

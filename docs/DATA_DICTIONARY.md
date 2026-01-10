# Data Dictionary

This document describes all data files in the CPH50 Control system, their purpose, structure, and which components read/write them.

## Data Files

### `data/last_session.json`
**Purpose**: Dashboard snapshot of the current/most recent charging session  
**Format**: Flat JSON object  
**Created/Updated by**: `monitor_sessions.py` → `save_current_session()`  
**Read by**: `index.html` (dashboard)  
**Frequency**: Updated every 10 minutes (cron check)  

**Structure**:
```json
{
  "timestamp": "2026-01-10T22:30:00+00:00",
  "detected_at": "2026-01-10 14:30:00 PST",
  "power_kw": 8.61,
  "energy_kwh": 51.22,
  "duration_minutes": 359,
  "vehicle_id": "serenity_equinox_2024",
  "vehicle_confidence": 0.95,
  "connected": true,
  "charging": true
}
```

**Fields**:
- `timestamp`: UTC timestamp of last update
- `detected_at`: Local (PT) detection time for display
- `power_kw`: Current power draw (null if not charging)
- `energy_kwh`: Total energy delivered in current session
- `duration_minutes`: Session duration in minutes
- `vehicle_id`: Key to `vehicle_config.json`
- `vehicle_confidence`: ML classifier confidence (0-1)
- `connected`: Charger physically connected
- `charging`: Active charging in progress

---

### `data/sessions/YYYY/MM/DD/{session_id}.json`
**Purpose**: Detailed session data collected from ChargePoint API and ML classifier  
**Format**: JSON object with nested arrays  
**Created/Updated by**: `collect_session_data.py` → Writes after 5-minute collection window  
**Read by**: `history.html` (history page)  
**Frequency**: One file per session; approx. 1 per day  

**Structure**:
```json
{
  "session_id": "4751613101",
  "collection_start": "2026-01-07T06:00:01+00:00",
  "collection_end": "2026-01-07T06:05:10+00:00",
  "duration_seconds": 309.334991,
  "sample_count": 30,
  "valid_sample_count": 30,
  "interval_seconds": 10,
  "vehicle_id": "serenity_equinox_2024",
  "vehicle_confidence": 0.95,
  "labeled_by": "classifier",
  "labeled_at": "2026-01-07T06:06:00+00:00",
  "samples": [
    {
      "sample_number": 1,
      "timestamp": "2026-01-07T06:00:21+00:00",
      "timestamp_pt": "2026-01-06 22:00:21 PST",
      "session_id": "4751613101",
      "power_kw": 8.6075,
      "energy_kwh": 57.5667,
      "duration_minutes": null,
      "status": null
    },
    ...30 samples total...
  ]
}
```

**Notes**:
- Organized by session start date (handles midnight-spanning sessions)
- 30 samples collected at 10-second intervals (~5 minutes total)
- Each sample contains power and cumulative energy readings
- Vehicle classification (ML output) stored with confidence score

---

### `data/vehicle_config.json`
**Purpose**: Master vehicle metadata and configuration  
**Format**: Structured JSON with vehicle dictionary  
**Created/Updated by**: Manual (user updates)  
**Read by**: 
  - `history.html` (vehicle display names and efficiency)
  - `index.html` (vehicle display names)
  - Python scripts (reference data)  
**Frequency**: Updated when new vehicles added or details change  

**Structure**:
```json
{
  "vehicles": {
    "serenity_equinox_2024": {
      "nickname": "Serenity",
      "year": 2024,
      "make": "Chevrolet",
      "model": "Equinox EV",
      "trim": "2LT",
      "battery_capacity_kwh": 85,
      "max_charge_rate_kw": 11.5,
      "paint_color": "Bursting Blue",
      "paint_color_hex": "#2C5F8D",
      "display_color": "Blue",
      "efficiency_mi_per_kwh": 2.38,
      "characteristics": "Higher power draw, very consistent charging pattern"
    },
    ...additional vehicles...
  },
  "last_updated": "2026-01-10T00:00:00Z"
}
```

**Fields**:
- `nickname`: Display name (used if set)
- `year`, `make`, `model`, `trim`: Vehicle identification
- `battery_capacity_kwh`: Total battery size
- `max_charge_rate_kw`: Maximum charging power
- `paint_color`: Actual paint color name
- `paint_color_hex`: Hex code for paint color
- `display_color`: Simple color for disambiguation (e.g., "Blue", "Red")
- `efficiency_mi_per_kwh`: For converting energy to estimated miles
- `characteristics`: Human-readable notes on charging behavior

---

### `data/.last_session_id.json`
**Purpose**: Internal tracking of last detected session (not exposed to dashboard)  
**Format**: Flat JSON  
**Created/Updated by**: `monitor_sessions.py` → `save_session_tracking()`  
**Read by**: `monitor_sessions.py` (to detect new sessions)  
**Frequency**: Updated on session start/stop detection  

**Structure**:
```json
{
  "session_id": "4751613101",
  "timestamp": "2026-01-07T06:00:01+00:00"
}
```

**Notes**:
- Separate from `last_session.json` (which is dashboard-exposed)
- Used purely for monitoring loop to detect NEW session starts

---

### `data/runs.json`
**Purpose**: Automation/deployment test run history  
**Format**: Flat JSON with runs array  
**Created/Updated by**: Automation/CI system (external)  
**Read by**: Diagnostic only (not currently displayed)  
**Frequency**: One entry per test run  

**Structure**:
```json
{
  "runs": [
    {
      "run_id": "run_001",
      "date": "2026-01-10",
      "time_utc": "14:49:17",
      "time_pt": "06:49:17",
      "result": "other",
      "reason": "No vehicle plugged in",
      "run_type": "scheduled"
    }
  ]
}
```

---

### `data/classifier_summary.json`
**Purpose**: Aggregate statistics on ML vehicle classifier performance  
**Format**: JSON with accuracy metrics  
**Created/Updated by**: `train_vehicle_classifier.py`  
**Read by**: Diagnostic/reporting scripts  
**Frequency**: Updated after classifier training  

---

### `data/session_vehicle_map.json` (Legacy)
**Purpose**: Manual vehicle mapping (fallback if classifier unavailable)  
**Format**: Mapping of session_id to vehicle labels  
**Created/Updated by**: Manual or legacy scripts  
**Read by**: `monitor_sessions.py` (fallback lookup)  
**Status**: Deprecated; classifier is primary method  

---

## Web Pages & Components

### `index.html` (Dashboard)
**Reads**:
- `data/last_session.json` (current session status)
- `data/vehicle_config.json` (vehicle display metadata)

**Display**:
- Current power (kW)
- Energy delivered (kWh)
- Vehicle name with confidence
- Vehicle image

---

### `history.html` (History/Analytics)
**Reads**:
- All files in `data/sessions/YYYY/MM/DD/` (discovered recursively)
- `data/vehicle_config.json` (vehicle names and efficiency)

**Display**:
- Aggregated energy/miles/sessions by period (day/month/year)
- Interactive bar chart
- Session details table with filters
- Vehicle and metric selection dropdowns

---

### `blog/` (Jekyll blog posts)
**Reads**: None (static HTML)  
**Purpose**: Technical blog documenting the project

---

## Python Scripts & Data Flow

### `monitor_sessions.py`
**Schedule**: Cron `0 13,14 * * *` (13:00 and 14:00 UTC)  
**Reads**:
- ChargePoint API (authentication + session status)
- `data/.last_session_id.json` (to detect new sessions)
- `data/session_vehicle_map.json` (vehicle mapping fallback)

**Writes**:
- `data/last_session.json` (dashboard snapshot)
- `data/.last_session_id.json` (tracking)
- Triggers `collect_session_data.py` on new session detection

---

### `collect_session_data.py`
**Triggered by**: `monitor_sessions.py` on new session  
**Duration**: 5 minutes of collection (30 samples at 10s intervals)  
**Reads**:
- ChargePoint API (session power/energy data)
- `classify_vehicle.py` (ML inference)

**Writes**:
- `data/sessions/YYYY/MM/DD/{session_id}.json`
- Git commits the new session file

---

### `classify_vehicle.py`
**Triggered by**: `collect_session_data.py`  
**Reads**: Charging power samples from current session  
**Output**: Vehicle ID + confidence score (stored in session JSON)

**Vehicles Recognized**:
- `serenity_equinox_2024` (Chevrolet Equinox EV)
- `volvo_xc40_2021` (Volvo XC40 Recharge)
- Falls back to `unknown` if confidence too low

---

## Schema & Key Relationships

**Vehicle Identification Chain**:
```
ChargePoint Session
    ↓
collect_session_data.py
    ↓
classify_vehicle.py (ML inference)
    ↓
vehicle_id + confidence → session JSON
    ↓
vehicle_config.json lookup (for display name/efficiency)
    ↓
Dashboard & History display
```

**Session Data Organization**:
```
data/sessions/
  ├── 2025/
  │   └── 01/
  │       ├── 07/
  │       │   └── 4751613101.json
  │       └── 08/
  │           └── 4754846071.json
  └── 2026/
      └── 01/
          └── 10/
              └── 4758000341.json
```

---

## Data Persistence & Git

All `data/` files are committed to Git:
- `data/*.json` (last_session, vehicle_config, etc.) → Version controlled
- `data/sessions/YYYY/MM/DD/*.json` → New session files auto-committed by `collect_session_data.py`

This allows:
- Historical audit trail
- Recovery if local files corrupted
- Public sharing of anonymized charging patterns (via GitHub)

---

## Future Enhancements

- [ ] Implement recursive directory scanning for session discovery (instead of hardcoded paths)
- [ ] Add export functionality (CSV download of session data)
- [ ] Archive old sessions (compress 6+ months old)
- [ ] Database backend instead of JSON files (for faster querying)
- [ ] API endpoint for programmatic access to session data

---

**Last Updated**: 2026-01-10  
**Maintainer**: Keep this document in sync when adding/modifying data files or their usage.

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

### `data/session_cache/YYYY-MM.json`
**Purpose**: Full ChargePoint session data for history display (populated by `fetch_session_details.py`)  
**Format**: Array of session objects  
**Created/Updated by**: `fetch_session_details.py` (triggered after session completes)  
**Read by**: `history.html` (history page displays cached data)  
**Frequency**: One entry per charging session; file grows over the month (~30-40 sessions/month)  
**Organization**: Monthly files for efficient loading (single fetch = entire month)

**File Size**: ~60-150 KB per month (manageable for git, fast to load)

**Structure** (array of sessions):
```json
[
  {
    "session_id": "4751613101",
    "session_start_time": "2026-01-10T14:00:01+00:00",
    "session_end_time": "2026-01-10T22:30:15+00:00",
    "vehicle": {
      "vehicle_id": "serenity_equinox_2024",
      "vehicle_name": "Serenity",
      "model": "Equinox EV",
      "vin": "...",
      "make": "Chevrolet"
    },
    "location": {
      "location_id": "...",
      "name": "Home",
      "address": "...",
      "city": "Oceanside",
      "state": "CA",
      "zip_code": "92054"
    },
    "charger": {
      "charger_id": "...",
      "connector_type": "J1772",
      "charger_model": "CPH50",
      "level": 2
    },
    "session": {
      "energy_kwh": 51.22,
      "duration_seconds": 30614,
      "cost": 8.45,
      "peak_power_kw": 11.5,
      "status": "completed"
    },
    "utility": {
      "utility_name": "SDG&E",
      "utility_company": "San Diego Gas & Electric"
    },
    "vehicle_id": "serenity_equinox_2024",
    "vehicle_confidence": 0.95
  },
  ...additional sessions...
]
```

**Notes**:
- Organized by month (YYYY-MM.json) for efficient history page loading
- Contains vehicle classification merged from `data/sessions/{date}/{id}.json`
- Atomic writes (temp file + rename) prevent corruption
- Each commit shows full month snapshot for audit trail

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

### `data/session_vehicle_map.json`
**Purpose**: Master registry of vehicle assignments for all sessions (source of truth)  
**Format**: Mapping of session_id to vehicle labels  
**Created/Updated by**: 
  - `collect_session_data.py` (after classifier runs - auto-update with confidence)
  - `history.html` (future: user manual labeling UI)
**Read by**: 
  - `history.html` (to get correct vehicle for each session)
  - Any analysis/reporting that needs vehicle truth
**Frequency**: Updated after each charging session is classified

**Structure**:
```json
{
  "sessions": {
    "4751613101": {
      "vehicle": "serenity_equinox_2024",
      "confidence": 0.95,
      "source": "classifier",
      "labeled_at": "2026-01-10T14:06:00+00:00"
    },
    "4754846071": {
      "vehicle": "serenity_equinox_2024",
      "confidence": 0.88,
      "source": "classifier",
      "labeled_at": "2026-01-09T22:15:00+00:00"
    }
  },
  "unknown_sessions": ["4758000342", "4758000343"],
  "last_updated": "2026-01-10T14:06:00+00:00",
  "statistics": {
    "total_sessions": 45,
    "labeled_sessions": 43,
    "serenity_equinox_2024": 28,
    "volvo_xc40_2021": 15,
    "unknown": 2
  }
}
```

**Fields**:
- `vehicle`: Key to `vehicle_config.json` (e.g., "serenity_equinox_2024")
- `confidence`: 0-1 confidence score from ML classifier
- `source`: How vehicle was identified ("classifier", "manual", "chargepoint_corrected", etc)
- `labeled_at`: ISO timestamp of when assignment was made

**Important Notes**:
- ✅ **Authoritative source** for vehicle-to-session mapping (overrides ChargePoint data)
- ✅ **Updated by classifier** after power samples collected (each session)
- ✅ **Supports manual overrides** for when ML or ChargePoint is wrong
- ⚠️ **ChargePoint data is unreliable** - this map corrects those errors

---

## Web Pages & Components

### Sitewide Authentication
**Implemented by**: `assets/js/auth.js` (loaded by `_layouts/default.html`)  
**UI Component**: `_includes/auth.html` (displayed on all pages)  

**Features**:
- GitHub Personal Access Token (PAT) login form
- Verifies collaborator status against repo
- Stores token in localStorage for persistence
- Sets global `window.isContributor` flag for conditional features
- Available on all pages via shared layout

**Security**:
- PAT stored client-side (temporary solution - see KNOWN_ISSUES.md)
- Roadmap: OAuth2 with backend token exchange
- Currently: Best-effort for now to enable future admin features

---

### `index.html` (Dashboard)
**Reads**:
- `data/last_session.json` (current session status)
- `data/vehicle_config.json` (vehicle display metadata)

**Display**:
- Current power (kW)
- Energy delivered (kWh)
- Vehicle name with confidence
- Vehicle image

**Auth Integration**: Uses global `window.isContributor` (future feature gating)

---

### `history.html` (History/Analytics)
**Reads**:
- Monthly cache files from `data/session_cache/YYYY-MM.json` (via GitHub raw API)
- `data/vehicle_config.json` (vehicle names and efficiency)
- `data/session_vehicle_map.json` (correct vehicle assignments)

**Display**:
- Aggregated energy/miles/sessions by period (day/month/year)
- Interactive bar chart
- Session details table with filters
- Vehicle and metric selection dropdowns

**Data Flow**:
- Loads vehicle_config and session_vehicle_map from GitHub
- Discovers available monthly cache files (last 13 months)
- For each month: fetches `data/session_cache/YYYY-MM.json` from GitHub raw API
- Merges cache data (metrics) with vehicle_map (correct vehicle IDs)
- All data served from GitHub (no authentication needed for reads)

**Auth Integration**: Uses global `window.isContributor` (future manual labeling UI)

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
**Triggered by**: GitHub Actions workflow `collect-session-data.yml` (on new session detection)  
**Duration**: 5 minutes of collection (30 samples at 10s intervals)  
**Reads**:
- ChargePoint API (session power/energy data)
- `classify_vehicle.py` (ML inference)

**Writes**:
- `data/sessions/YYYY/MM/DD/{session_id}.json` (5-min power samples)
- `data/session_vehicle_map.json` (vehicle classification results)
- Git commits session data

**Then triggers**: `fetch_session_details.py` (next step in workflow)

---

### `fetch_session_details.py`
**Triggered by**: GitHub Actions workflow `collect-session-data.yml` (after `collect_session_data.py`)  
**Reads**:
- ChargePoint API (full session metrics)
- `data/sessions/YYYY/MM/DD/{session_id}.json` (for vehicle classification)

**Writes**:
- `data/session_cache/YYYY-MM.json` (appends session to monthly cache file)
- Git commits monthly cache file

**Purpose**: 
- Fetches complete ChargePoint session data (energy, duration, location, etc.)
- Merges with vehicle classification from session samples
- Organizes by month for efficient loading by `history.html`

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

data/session_cache/
  ├── 2025-01.json  (contains all sessions from January 2025)
  ├── 2025-02.json
  └── 2026-01.json  (contains all sessions from January 2026)
```

---

## GitHub Actions Workflows

All data collection and caching is orchestrated by GitHub Actions workflows:

### `monitor-sessions.yml`
**Schedule**: Every 10 minutes (cron: `*/10 * * * *`)  
**Runs**: `monitor_sessions.py`
**Flow**:
1. Detects new charging sessions via ChargePoint API
2. Saves session snapshot to `data/last_session.json` (dashboard)
3. On new session detected: Triggers `collect-session-data.yml` workflow

### `collect-session-data.yml`
**Triggered by**: `monitor-sessions.yml` on new session  
**Runs**:
1. `collect_session_data.py` - Collects 5 minutes of power samples + ML classification
2. `fetch_session_details.py` - Fetches full ChargePoint metrics, caches to monthly file
**Commits**: Session samples and monthly cache files to repo

**Result**: Both `data/sessions/` and `data/session_cache/` are populated and committed

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

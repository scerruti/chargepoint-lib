# ChargePoint API Discovery: Session History Support

## The Problem

The `python-chargepoint` library wraps ChargePoint's public API but has **critical limitations**:
- `get_charging_session(session_id)` - requires knowing the session ID
- `get_user_charging_status()` - only returns the current active session
- **NO method** for querying sessions by date range or listing historical sessions

This made it impossible to:
1. Automatically populate the session cache from historical data
2. Implement monthly cache update workflows
3. Backfill the history page for past months

## The Solution

### Undocumented Direct API Endpoints

ChargePoint's mobile/web app uses additional endpoints not exposed by `python-chargepoint`:

#### 1. **Current Session Status**
```
POST https://mc.chargepoint.com/map-prod/v2
{
  "user_status": {
    "mfhs": {}
  }
}
```
**Returns:** Current user status including any active charging session

#### 2. **Complete Session History** ✨ **KEY DISCOVERY**
```
POST https://mc.chargepoint.com/map-prod/v2
{
  "charging_activity_monthly": {
    "page_size": 50,
    "show_address_for_home_sessions": true
  }
}
```
**Returns:** ALL charging sessions organized by month, paginated

## Implementation

### `chargepoint_api.py`

New direct HTTP client that:
- Authenticates with ChargePoint via standard login
- Makes raw HTTP requests to `/map-prod/v2` endpoint
- Supports both single-session and bulk session fetching
- Extracts session data from API responses

**Key methods:**
- `get_user_sessions()` - Current status
- `get_session_details(session_id)` - Single session
- `get_session_history(page_size, show_address)` - **ALL sessions**
- `extract_sessions_from_activity(activity_data)` - Parse response

### `fetch_session_details.py` (Enhanced)

Three operational modes:

**1. Single Session Fetch**
```bash
python fetch_session_details.py 4751613101
```
- Fetches one session by ID
- Caches to `data/session_cache/YYYY/MM/YYYY-MM.json`
- Merges vehicle classification if available
- Commits to git

**2. Bulk Fetch (NEW)** 🚀
```bash
python fetch_session_details.py --bulk
```
- Fetches ALL sessions from ChargePoint API
- Processes entire charging history at once
- Automatically organizes by month and caches
- Perfect for initial setup and monthly cache population

**3. Month-Specific Fetch**
```bash
python fetch_session_details.py --month 2025-12
```
- Fetches sessions from local filesystem for a specific month
- Useful for targeted updates

## Workflow Integration

### Automated Cache Population

**Weekly refresh:**
```yaml
# .github/workflows/update-cache.yml
schedule:
  - cron: '0 2 * * 1'  # Mondays at 2am UTC
  
script: python fetch_session_details.py --bulk
```

**Monthly closure (2nd of month):**
```yaml
# .github/workflows/monthly-cache-update.yml
schedule:
  - cron: '0 10 2 * *'  # 2nd of month at 10am UTC
  
script: python fetch_session_details.py --bulk
```

## Data Flow

```
ChargePoint API (/map-prod/v2)
    ↓
chargepoint_api.py (authenticate + fetch)
    ↓
fetch_session_details.py (cache to monthly files)
    ↓
data/session_cache/YYYY/MM/YYYY-MM.json
    ↓
history.html (loads from GitHub raw API, no API calls needed)
    ↓
User sees complete charging history with zero latency
```

## Benefits

✅ **No API Limitations** - Bulk session fetching works
✅ **Automated Workflows** - GitHub Actions can populate cache on schedule
✅ **Fast Page Loads** - History page reads pre-cached JSON from GitHub
✅ **Historical Data** - Can backfill entire year in one run
✅ **Vehicle Classification** - Merged from ML classifier results
✅ **Git Audit Trail** - All cache updates committed with timestamps

## Known Caveats

- `/map-prod/v2` endpoint is undocumented (may change without notice)
- Requires valid ChargePoint credentials
- Session history pagination not yet implemented (page_size=50 should cover most users)
- First run with `--bulk` may take time depending on charging history volume

## Future Enhancements

- [ ] Implement pagination for large session histories (> 50 sessions)
- [ ] Add incremental mode: `--since YYYY-MM-DD` to only fetch new sessions
- [ ] Support for different metrics (miles, cost estimates, etc.)
- [ ] Session filtering by vehicle, date range, location

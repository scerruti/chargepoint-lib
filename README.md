# CPH50 Charge Controller

Automated charging system for ChargePoint Home Flex (CPH50) that starts charging at 6:00 AM America/Los_Angeles daily, respecting time-of-use rate plans and automatically identifying which vehicle is charging.

## Architecture

**GitHub Actions Based** (migrated from Cloudflare Workers)

```
ChargePoint API
    ↓
GitHub Actions Cron (every 10 min)
    ↓
monitor_sessions.py → Detect new charging sessions
    ↓
collect_session_data.py → Collect 5-min power curve
    ↓
VehicleClassifier → Identify vehicle (Volvo/Equinox)
    ↓
data/last_session.json → Real-time charging status
data/sessions/{id}.json → Historical session records
    ↓
Dashboard (GitHub Pages) → Live visualization
```

## Features

### 🚗 Vehicle Classification
- **Automatic identification** of charging vehicle from power curve
- **99%+ accuracy** using rolling statistics (mean power, CV, percentiles)
- Trained on historical data with robust feature extraction
- Handles partial capture windows and charging anomalies

### 📊 Real-Time Dashboard
- Live charging status visualization at GitHub Pages
- Shows current vehicle, power draw, energy added, session duration
- Classification confidence score
- Auto-refreshes every 10 seconds
- Mobile responsive design

### 📈 Data Collection & Monitoring
- GitHub Actions cron runs every 10 minutes
- Detects new charging sessions automatically
- Collects 5-minute power samples (30 readings at 10-second intervals)
- Stores historical sessions with vehicle labels for classifier refinement

### ⏰ 6AM Start Automation
- Python script (`charge_github.py`) triggers ChargePoint to start charging
- Respects America/Los_Angeles timezone
- Runs via GitHub Actions cron (13:00, 14:00 UTC to handle DST)

## Setup

### Prerequisites
- Python 3.12+ with virtual environment
- GitHub repository with Actions enabled
- ChargePoint account credentials
- ChargePoint Home Flex (CPH50) station

### Installation

1. **Clone and setup Python environment:**
   ```bash
   python3 -m venv test_env
   source test_env/bin/activate  # or test_env\Scripts\activate on Windows
   pip install -r requirements.txt
   ```

2. **Configure GitHub Secrets:**
   - Go to repository Settings → Secrets → Actions
   - Add:
     - `CP_USERNAME`: ChargePoint account username
     - `CP_PASSWORD`: ChargePoint account password
     - `CP_STATION_ID`: Your CPH50 station ID (get from ChargePoint app)

3. **Enable GitHub Actions:**
   - Workflows in `.github/workflows/` will run automatically
   - Monitor runs in Actions tab

## Usage

### Manual Charge Trigger
```bash
python3 charge_github.py
```

### Check Current Status
```bash
python3 monitor_sessions.py
cat data/last_session.json
```

### View Dashboard
Open: `https://scerruti.github.io/cph50-control/docs/dashboard.html`

### Train Classifier (after collecting more sessions)
```bash
python3 train_vehicle_classifier.py
# Updates data/classifier_summary.json with new statistics
```

### Classify a Session
```bash
python3 classify_vehicle.py
# Runs test predictions on seed data
```

## Files

### Python Scripts
- `charge_github.py` - Trigger 6AM charging
- `monitor_sessions.py` - Detect new sessions (runs every 10 min)
- `collect_session_data.py` - Collect power samples & classify vehicle
- `classify_vehicle.py` - Vehicle identification inference
- `train_vehicle_classifier.py` - Train classifier from historical data
- `check_status.py` - Check current charging status

### Data Files
- `data/last_session.json` - Current charging session (for dashboard)
- `data/sessions/{id}.json` - Historical session records
- `data/classifier_summary.json` - Pre-trained vehicle statistics
- `data/vehicle_config.json` - Vehicle metadata
- `data/session_vehicle_map.json` - Manual vehicle labels

### Dashboard
- `docs/dashboard.html` - Real-time charging visualization
- `docs/images/` - Vehicle images (Volvo, Equinox)

### Documentation
- `INTEGRATION.md` - Complete integration architecture guide
- `GITHUB_ACTIONS_SETUP.md` - GitHub Actions workflow documentation
- `docs/blog/` - Blog series documenting the project

## Migration History

**Previous Architecture**: Home Assistant → ESP32 → Cloudflare Workers → GitHub Actions

**Current Architecture**: Direct GitHub Actions automation

Benefits of migration:
- Simplified stack (fewer moving parts)
- No external infrastructure dependencies
- Better data persistence (git-backed storage)
- Easier debugging and monitoring via Actions logs
- Free hosting via GitHub Pages for dashboard

## Vehicle Classifier Details

### Current Vehicles
- **Volvo XC40 Recharge (2021)**: 8.50 kW mean power, CV=0.074
- **Chevrolet Equinox EV (2024)**: 9.01 kW mean power, CV=0.014

### Adding New Vehicles
1. Run a charging session
2. Label in `data/session_vehicle_map.json`
3. Run `python3 train_vehicle_classifier.py`
4. Classifier automatically includes new vehicle

### Features Used
- Mean power (primary discriminator)
- P25/P75 percentiles (robust to outliers)
- Coefficient of variation (stability metric)
- IQR (spread measurement)

## Links

- **Dashboard**: https://scerruti.github.io/cph50-control/docs/dashboard.html
- **Blog Series**: https://scerruti.github.io/cph50-control/docs/blog/
- **Repository**: https://github.com/scerruti/cph50-control

## Development

### Run Tests
```bash
./verify_integration.sh  # Verify all components
```

### Local Dashboard Testing
```bash
# Create sample data
echo '{"session_id":"test","power_kw":8.5,"energy_kwh":10,"duration_minutes":45,"vehicle_id":"volvo","vehicle_confidence":0.994}' > data/last_session.json

# Open docs/dashboard.html in browser
```

## Troubleshooting

### Monitor Job Fails
- Check GitHub Actions logs
- Verify secrets are set correctly
- Check for 403 WAF blocks (transient, tracked in issues)

### Classifier Not Working
- Ensure `data/classifier_summary.json` exists
- Check `requirements.txt` dependencies installed
- Verify numpy/scikit-learn versions

### Dashboard Not Updating
- Check `data/last_session.json` is being updated by monitor
- Verify images in `docs/images/` directory
- Check browser console for fetch errors

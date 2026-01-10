<!-- Use this file to provide workspace-specific custom instructions to Copilot. For more details, visit https://code.visualstudio.com/docs/copilot/copilot-customization#_use-a-githubcopilotinstructionsmd-file -->
- [x] Verify that the copilot-instructions.md file in the .github directory is created.

- [x] Clarify Project Requirements
	<!-- Ask for project type, language, and frameworks if not specified. Skip if already provided. -->

- [x] Scaffold the Project
	<!--
	Ensure that the previous step has been marked as completed.
	Call project setup tool with projectType parameter.
	Run scaffolding command to create project files and folders.
	Use '.' as the working directory.
	If no appropriate projectType is available, search documentation using available tools.
	Otherwise, create the project structure manually using available file creation tools.
	-->

- [x] Customize the Project
	<!--
	Verify that all previous steps have been completed successfully and you have marked the step as completed.
	Develop a plan to modify codebase according to user requirements.
	Apply modifications using appropriate tools and user-provided references.
	Skip this step for "Hello World" projects.
	-->

- [x] Install Required Extensions
	<!-- ONLY install extensions provided mentioned in the get_project_setup_info. Skip this step otherwise and mark as completed. -->

- [x] Compile the Project
	<!--
	Verify that all previous steps have been completed.
	Install any missing dependencies.
	Run diagnostics and resolve any issues.
	Check for markdown files in project folder for relevant instructions on how to do this.
	-->

- [x] Create and Run Task
	<!--
	Verify that all previous steps have been completed.
	Check https://code.visualstudio.com/docs/debugtest/tasks to determine if the project needs a task. If so, use the create_and_run_task to create and launch a task based on package.json, README.md, and project structure.
	Skip this step otherwise.
	 -->

- [ ] Launch the Project
	<!--
	Verify that all previous steps have been completed.
	Prompt user for debug mode, launch only if confirmed.
	 -->

- [ ] Ensure Documentation is Complete
	<!--
	Verify that all previous steps have been completed.
	Verify that README.md and the copilot-instructions.md file in the .github directory exists and contains current project information.
	Clean up the copilot-instructions.md file in the .github directory by removing all HTML comments.
	 -->

Cloudflare Worker & Data Stack Instructions for GitHub Copilot

## Project Overview
- **User**: Stephen (Oceanside, CA)
- **Hardware**: ChargePoint Home Flex (CPH50)
- **Goal**: Robustly automate EV charging to start at 6:00 AM PT daily
- **Architecture**: 
  - Cloudflare Worker (TypeScript) handles automation
  - Python scripts collect and process charging data
  - Jekyll static site displays history & analytics
  - GitHub Pages hosts the front-end

## Data Files & Documentation

**⚠️ CRITICAL: Keep data structures documented**

When modifying any data files or adding new ones:
1. Update `docs/SCHEMA.md` with JSON schema
2. Update `docs/DATA_DICTIONARY.md` with purpose/usage
3. Commit both docs with your code changes
4. Reference section below when working with data

**See also:**
- [`docs/DATA_DICTIONARY.md`](../../docs/DATA_DICTIONARY.md) - Complete reference for all data files, what reads/writes them
- [`docs/SCHEMA.md`](../../docs/SCHEMA.md) - JSON schemas for data structures
- [`KNOWN_ISSUES.md`](../../KNOWN_ISSUES.md) - Known limitations and edge cases

## Cloudflare Worker Configuration

**Platform**: V8 Isolate (TypeScript)  
**Schedule**: `0 13,14 * * *` (13:00 and 14:00 UTC)  
**Check Time**: Must verify `America/Los_Angeles` hour === 6 before charging

**ChargePoint API Endpoints**:
- Login: `POST https://account.chargepoint.com/account/v1/driver/auth/login`
- Start Charging: `POST https://mc.chargepoint.com/map-prod/v2`

**Failure Handling**:
- Retry: 3 attempts with exponential backoff (2s, 4s, 8s)
- Alert: Send MailChannels email to `env.ALERT_EMAIL` on failure

**Environment Variables** (wrangler.toml):
```
CP_USERNAME
CP_PASSWORD
CP_STATION_ID
ALERT_EMAIL
TZ_REGION = "America/Los_Angeles"
```

## Python Data Pipeline

**`monitor_sessions.py`** (Cron: 13:00, 14:00 UTC daily)
- Checks ChargePoint API for active charging
- Updates `data/last_session.json` (dashboard)
- Detects new sessions → triggers `collect_session_data.py`

**`collect_session_data.py`** (Triggered by monitor_sessions)
- Collects 5 minutes of power samples (30 x 10-second intervals)
- Runs ML classifier → `classify_vehicle.py`
- Writes `data/sessions/YYYY/MM/DD/{session_id}.json`

**`classify_vehicle.py`** (Invoked by collect_session_data)
- ML inference on power samples
- Output: vehicle_id + confidence → stored in session JSON

**`vehicle_config.json`** (Manual maintenance)
- Master vehicle registry
- Vehicle names, efficiency, display colors
- Reference for dashboard & history display

## Web Interface

**`index.html`** (Live Status Dashboard)
- Reads: `data/last_session.json`, `data/vehicle_config.json`
- Display: Current power, energy, vehicle name, vehicle image

**`history.html`** (Charging Analytics)
- Reads: All `data/sessions/YYYY/MM/DD/*.json` files, `vehicle_config.json`
- Features:
  - Day/Month/Year view toggle (default: Month)
  - Vehicle filter dropdown (All, Serenity, Volvo, Unknown)
  - Metric selection (Energy, Miles, Sessions)
  - Interactive bar chart
  - Session details table
- Vehicle Display: Nickname if available (e.g., "Serenity"), else model name (e.g., "XC40")
  - Disambiguation: If two vehicles share name, prefix with display_color (e.g., "Blue XC40")

**`blog/` & `_posts/`** (Jekyll Blog)
- 7 technical blog posts documenting the project
- Built with Jekyll, deployed to GitHub Pages

## Key Design Decisions

**Session Organization**: 
- Files organized by **start date** (handles midnight-spanning sessions)
- Path: `data/sessions/YYYY/MM/DD/{session_id}.json`

**Vehicle Identification**:
- Primary: ML classifier on power samples (stored in session JSON)
- Fallback: `session_vehicle_map.json` (manual mapping)
- Display: Use `nickname` from `vehicle_config.json` if set, else `model`

**Timezone Handling**:
- All data stored in UTC
- Dashboard converts to `America/Los_Angeles` for display
- ⚠️ DST transitions (Mar 2, Nov 1) may display incorrectly; see `KNOWN_ISSUES.md`

**Git Commits**:
- `monitor_sessions.py` commits `data/last_session.json` changes
- `collect_session_data.py` commits new session files
- Maintains audit trail of all charging events

## Common Tasks

**Add a new vehicle**: 
1. Update `vehicle_config.json` with `nickname`, `model`, `efficiency_mi_per_kwh`, `display_color`
2. Update `classify_vehicle.py` to recognize new patterns (if ML-based)
3. Update `SCHEMA.md` and `DATA_DICTIONARY.md` if structure changes

**Debug history page**:
1. Check browser console (F12) for JavaScript errors
2. Verify session JSON files are accessible (use curl)
3. Confirm `vehicle_config.json` is loaded and parsed
4. Check timezone conversion in `convertToLocalTime()` function

**Modify data structure**:
1. ⚠️ Update `docs/SCHEMA.md` with new/changed fields
2. ⚠️ Update `docs/DATA_DICTIONARY.md` with usage context
3. Update code to match schema
4. Commit all three together

## Known Limitations

See [`KNOWN_ISSUES.md`](../../KNOWN_ISSUES.md):
- DST transitions may display hour labels incorrectly
- Session discovery uses hardcoded file list (future: recursive scan)
- Miles calculation is estimate based on efficiency, not actual odometer

## References

- ChargePoint API: Undocumented mobile endpoint
- Cloudflare Workers: https://developers.cloudflare.com/workers/
- Jekyll: https://jekyllrb.com/

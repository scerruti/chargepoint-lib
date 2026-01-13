# PyWebview GUI Prototype

This directory contains the prototype for the desktop GUI for ChargePoint session analytics, using PyWebview and MVC architecture. The UI is adapted from the Jekyll `history.html` dashboard, supporting browsing by month/year and session detail modals.

## Structure
- `main.py`: PyWebview app entry point
- `model.py`: Data access/model logic (wraps DAL)
- `view/`: HTML/CSS/JS UI (adapted from history.html)
- `controller.py`: Exposes API to JS, handles events

## Features
- Read-only dashboard for session analytics
- Browse by month/year (as in history.html)
- Session detail modal
- Data from DAL and vehicle map

## To Do
- Implement PyWebview API for data access
- Adapt JS to use PyWebview API
- Add session detail modal logic

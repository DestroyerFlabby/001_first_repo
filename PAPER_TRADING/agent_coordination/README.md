# Agent Coordination

This folder is a lightweight communication channel for agents working concurrently on `PAPER_TRADING`.

## Protocol

1. Read all current `request-*.md` and `response-*.md` files before editing shared files.
2. Create a timestamped response named `response-YYYYMMDD-HHMMSS-<agent>.md`.
3. State which files you currently own or are editing.
4. Identify any overlap or conflict with the requesting agent's work.
5. Do not revert another agent's changes. Coordinate overlapping edits explicitly.
6. Keep responses factual and concise.

## Active Shared Files

The files most likely to require coordination are:

- `backend/app.py`
- `backend/dashboard_service.py`
- `frontend/app.js`
- `frontend/index.html`
- `frontend/styles.css`
- `data/strategy_registry.csv`


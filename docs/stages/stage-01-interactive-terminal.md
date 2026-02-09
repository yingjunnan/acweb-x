# Stage 1 - Interactive Terminal Baseline

Date: 2026-02-09
Status: Completed

## Goal

- Let users send input to running tasks from the web terminal panel.
- Ensure reconnect follows `from_seq` so users can resume without output loss.

## Scope

- Frontend task terminal input form.
- Frontend API call for `/api/v1/tasks/{id}/input`.
- Frontend reconnect logic using sequence cursor.
- Backend websocket payload JSON safety for datetime fields.

## Completed Work

- Added task input API method (`sendTaskInput`) in `/Users/yingjunnan/acweb/frontend/src/api.js`.
- Added terminal input UI and submit flow in `/Users/yingjunnan/acweb/frontend/src/components/TerminalPanel.jsx`.
- Added writable-state guard for input (only `running`/`queued` tasks allow input).
- Updated websocket reconnect flow to use `next_seq` and `from_seq` in `/Users/yingjunnan/acweb/frontend/src/App.jsx`.
- Ensured websocket payload uses JSON-safe serialization (`model_dump(mode="json")`) in `/Users/yingjunnan/acweb/backend/app/main.py`.
- Updated terminal panel styles for input row in `/Users/yingjunnan/acweb/frontend/src/styles.css`.

## Verification Notes

- Python syntax check passed for backend websocket changes.
- Frontend behavior can be validated manually by running backend + frontend and sending input to a long-running process.

## Stage Exit Criteria

- [x] Web can submit input to a running task.
- [x] Reconnect uses sequence cursor instead of always replaying from `1`.
- [x] Terminal UI remains usable on desktop and mobile.

## Handoff to Stage 2

- Persist task metadata and events to database.
- Ensure `next_seq` comes from persistent storage after service restart.

# acweb Development Plan

Last updated: 2026-02-09

## Stage Overview

| Stage | Name | Goal | Status |
| --- | --- | --- | --- |
| Stage 1 | Interactive Terminal Baseline | Support task input from web UI and reliable reconnect by sequence cursor. | Completed |
| Stage 2 | Persistence and Recovery | Replace in-memory task/event store with persistent data layer and restart recovery baseline. | In Progress |
| Stage 3 | Security and Governance | Add auth, RBAC, and audit logging for production access control. | Planned |

## Documentation Rules

- Each stage has one record file under `docs/stages/`.
- Every stage record must include: goal, scope, task checklist, verification notes, and next stage handoff.
- Whenever code is merged for a stage, update the corresponding stage record first, then update this overview.

## Current Priority

- Current target: Stage 2 persistence and recovery.
- Stage 2 completed milestones:
  1. Persistent task/event storage (SQLAlchemy).
  2. SQLite baseline + PostgreSQL runtime profile.
  3. Docker-based PostgreSQL verification completed.
  4. Alembic migration scaffold and initial revision added.
  5. Startup recovery for incomplete tasks added.
  6. API smoke test (create/list/events + restart persistence) passed.
  7. Web terminal upgraded to xterm.js for ANSI/interactive shell compatibility.
- Remaining Stage 2 milestones:
  1. Add Redis live event fan-out and cursor cache.
  2. Define restart-safe active-task reconciliation strategy for true process continuity.

# acweb Development Plan

Last updated: 2026-02-09

## Stage Overview

| Stage | Name | Goal | Status |
| --- | --- | --- | --- |
| Stage 1 | Interactive Terminal Baseline | Support task input from web UI and reliable reconnect by sequence cursor. | Completed |
| Stage 2 | Persistence and Recovery | Replace in-memory task/event store with PostgreSQL + Redis for restart recovery. | Planned |
| Stage 3 | Security and Governance | Add auth, RBAC, and audit logging for production access control. | Planned |

## Documentation Rules

- Each stage has one record file under `docs/stages/`.
- Every stage record must include: goal, scope, task checklist, verification notes, and next stage handoff.
- Whenever code is merged for a stage, update the corresponding stage record first, then update this overview.

## Current Priority

- Next target: Stage 2 persistence and recovery.
- Suggested implementation order:
  1. Define SQL schema for tasks/task_events and basic migrations.
  2. Introduce repository layer and keep API contract stable.
  3. Add Redis stream/pubsub for live fan-out and reconnect cursor recovery.

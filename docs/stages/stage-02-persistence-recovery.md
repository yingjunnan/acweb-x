# Stage 2 - Persistence and Recovery

Date: 2026-02-09
Status: Planned

## Goal

- Make tasks and events recoverable after backend restart.

## Planned Scope

- PostgreSQL schema and migrations for tasks/events.
- Redis-backed live fan-out and cursor state.
- Replace in-memory store with repository-backed implementation.

## Planned Exit Criteria

- [ ] Task/event history survives backend restart.
- [ ] `GET /tasks` and `GET /events` read from persistence.
- [ ] Websocket attach can continue from stored `next_seq`.

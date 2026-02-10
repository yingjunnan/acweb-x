# Stage 2 - Persistence and Recovery

Date: 2026-02-09
Status: In Progress

## Goal

- Make tasks and events recoverable after backend restart.

## Scope

- Replace in-memory task/event records with persistent storage.
- Keep existing API and websocket contracts compatible for frontend.
- Provide a database baseline that can be upgraded to PostgreSQL/Redis architecture.

## Completed Work

- Added SQLAlchemy async database layer and schema bootstrap in `/Users/yingjunnan/acweb/backend/app/db.py`.
- Added persistent tables for `tasks` and `task_events` with task-seq uniqueness.
- Added startup DB initialization in `/Users/yingjunnan/acweb/backend/app/main.py`.
- Refactored task store to read/write tasks and events from database in `/Users/yingjunnan/acweb/backend/app/store.py`.
- Switched command execution to PTY-backed runtime to support interactive shells (`zsh -i`) from web input.
- Added restart recovery for incomplete tasks (`queued`/`running` -> `failed` + recovery system event).
- Kept websocket/live subscribers and child process handles in memory while persisting event stream/history.
- Added backend dependencies: `SQLAlchemy`, `aiosqlite`, `asyncpg`, `alembic`, and explicit `greenlet` pin in `/Users/yingjunnan/acweb/backend/requirements.txt`.
- Added local DB ignores in `/Users/yingjunnan/acweb/.gitignore`.
- Added PostgreSQL service profile in `/Users/yingjunnan/acweb/docker-compose.yml`.
- Added backend env template for DB settings in `/Users/yingjunnan/acweb/backend/.env.example`.
- Added DB URL normalization (`postgres://`, `postgresql://` -> `postgresql+asyncpg://`) and startup retry config.
- Added Alembic migration scaffolding and initial revision under `/Users/yingjunnan/acweb/backend/migrations/`.
- Added backend smoke test script for manual verification in `/Users/yingjunnan/acweb/backend/scripts/smoke_test.py`.
- Added default command `zsh -i` in `/Users/yingjunnan/acweb/frontend/src/components/CommandComposer.jsx` for quick interactive shell sessions.
- Upgraded frontend terminal rendering to xterm.js and switched interactive input to WebSocket path for zsh theme/plugin compatibility.

## Verification Notes

- Backend modules compile successfully with `python3 -m py_compile backend/app/*.py`.
- PostgreSQL container started and healthy via `docker compose up -d postgres` and `docker compose ps postgres`.
- DB connectivity confirmed via `docker compose exec -T postgres psql -U acweb -d acweb -c "select current_database(), current_user;"`.
- Backend DB init against PostgreSQL verified via `docker compose run --rm backend python -c "import asyncio; from app.db import init_db; asyncio.run(init_db()); print('init_ok')"`.
- Created tables verified via `docker compose exec -T postgres psql -U acweb -d acweb -c "\\dt"`.
- Alembic migration verified on clean DB:
  - create db: `create database acweb_migrate_test;`
  - upgrade: `docker compose run --rm -e DATABASE_URL=postgresql+asyncpg://acweb:acweb_dev_pw@postgres:5432/acweb_migrate_test backend alembic upgrade head`
  - check: `alembic_version` + tables exist.
- Existing auto-created dev DB can be integrated by `docker compose run --rm backend alembic stamp head`.
- API runtime smoke test verified in container:
  - health endpoint OK
  - create task OK
  - events query OK
  - backend restart keeps tasks/events persisted.
  - `python scripts/smoke_test.py` passed in Docker backend container.
- PTY interactive shell flow validated (`sh -i` task + input + output marker + stop).

## Exit Criteria Tracking

- [x] Task/event history survives backend restart (SQLite baseline).
- [x] `GET /tasks` and `GET /events` read from persistence.
- [x] Websocket attach continues from stored `next_seq`.
- [x] PostgreSQL runtime profile and test instructions are available.
- [x] Migration workflow scaffold (Alembic) is available.
- [ ] Redis fan-out and restart reconciliation for active processes.

## Next Work

- Add Redis-backed event fan-out.
- Add restart-safe active process reconciliation strategy.
- Add Stage 3 auth/rbac/audit foundation.

# Stage 2 - Persistence and Recovery

Date: 2026-02-10
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
- Added backend dependencies: `SQLAlchemy`, `aiosqlite`, `asyncpg`, `alembic`, explicit `greenlet` pin, and optional Redis client dependency in `/Users/yingjunnan/acweb/backend/requirements.txt`.
- Added local DB ignores in `/Users/yingjunnan/acweb/.gitignore`.
- Added PostgreSQL service profile in `/Users/yingjunnan/acweb/docker-compose.yml`.
- Added Redis service profile and backend Redis URL wiring in `/Users/yingjunnan/acweb/docker-compose.yml`.
- Added backend env template for DB settings and optional Redis URL in `/Users/yingjunnan/acweb/backend/.env.example`.
- Added DB URL normalization (`postgres://`, `postgresql://` -> `postgresql+asyncpg://`) and startup retry config.
- Added Alembic migration scaffolding and initial revision under `/Users/yingjunnan/acweb/backend/migrations/`.
- Added backend smoke test script for manual verification in `/Users/yingjunnan/acweb/backend/scripts/smoke_test.py`.
- Added default command `zsh -i` in `/Users/yingjunnan/acweb/frontend/src/components/CommandComposer.jsx` for quick interactive shell sessions.
- Upgraded frontend terminal rendering to xterm.js and switched interactive input to WebSocket path for zsh theme/plugin compatibility.
- Added optional Redis pub/sub fan-out for websocket subscribers with local fallback dispatch and app lifecycle startup/shutdown hooks.
- Added terminal resize synchronization (`cols`/`rows`) and PTY controlling-terminal setup to improve zsh prompt layout, cursor visibility, and Ctrl+C behavior in web terminal sessions.
- Added frontend replay-input guard to prevent xterm terminal-query replies from being sent back as user input when switching tasks or replaying history.

## Verification Notes

- Backend modules compile successfully with `python3 -m py_compile backend/app/*.py`.
- PostgreSQL container started and healthy via `docker compose up -d postgres` and `docker compose ps postgres`.
- Backend and Redis started via `docker compose up -d backend` (backend depends on healthy Postgres + Redis).
- API runtime smoke test verified in container via `docker compose exec -T backend python scripts/smoke_test.py`.
- Alembic migration verified on clean DB:
  - create db: `create database acweb_migrate_test;`
  - upgrade: `docker compose run --rm -e DATABASE_URL=postgresql+asyncpg://acweb:acweb_dev_pw@postgres:5432/acweb_migrate_test backend alembic upgrade head`
  - check: `alembic_version` + tables exist.
- Existing auto-created dev DB can be integrated by `docker compose run --rm backend alembic stamp head`.
- PTY interactive shell flow validated (`sh -i` task + input + output marker + stop).

## Exit Criteria Tracking

- [x] Task/event history survives backend restart (SQLite baseline).
- [x] `GET /tasks` and `GET /events` read from persistence.
- [x] Websocket attach continues from stored `next_seq`.
- [x] PostgreSQL runtime profile and test instructions are available.
- [x] Migration workflow scaffold (Alembic) is available.
- [x] Redis fan-out baseline for websocket subscribers is available.
- [ ] Restart-safe active process reconciliation for true continuity across API restarts.

## Next Work

- Add restart-safe active process reconciliation strategy (runner/worker ownership + heartbeat).
- Add Stage 3 auth/rbac/audit foundation.

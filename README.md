# acweb

acweb is a web control plane for long-running CLI tasks. It gives you a browser UI to launch commands on a server and re-attach later without keeping the browser open.

## Repo structure

- `backend/` FastAPI API and WebSocket service.
- `frontend/` React + Vite dashboard.
- `docker-compose.yml` one-command local startup.

## Backend (FastAPI)

Features in this scaffold:

- `POST /api/v1/tasks` create CLI tasks.
- `GET /api/v1/tasks` list tasks.
- `GET /api/v1/tasks/{id}/events` replay logs by sequence cursor.
- `POST /api/v1/tasks/{id}/input` send stdin input to running task.
- `POST /api/v1/tasks/{id}/stop` terminate running tasks.
- `WS /ws/tasks/{id}` attach to live output and stream terminal events.

Persistence behavior:

- Tasks/events are persisted by SQLAlchemy.
- Default local DB is SQLite (`backend/acweb.db`) when `DATABASE_URL` is not set.
- PostgreSQL is supported with async driver (`postgresql+asyncpg://...`).
- `postgres://` and `postgresql://` are auto-normalized to `postgresql+asyncpg://`.
- Incomplete tasks are marked as failed on API restart (with recovery event).
- Optional Redis pub/sub fan-out can be enabled with `REDIS_URL` for websocket subscribers across processes.

Quick shell usage:

- Start a task with `zsh -i` to open an interactive shell session.
- Type directly inside the terminal pane to send commands (for example `ls`, `pwd`, `git status`).
- Terminal size changes are synced to the backend PTY, so zsh prompts and Ctrl+C/interactive behavior stay closer to a native terminal.

## Local development

### 1) Start backend (SQLite default)

```bash
cd /Users/yingjunnan/acweb/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

If you updated dependencies, rerun `pip install -r requirements.txt`.

### 2) Start frontend

```bash
cd /Users/yingjunnan/acweb/frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

If `npm install` cannot reach `registry.npmjs.org`, set a reachable mirror and retry:

```bash
cd /Users/yingjunnan/acweb/frontend
npm config set registry https://registry.npmmirror.com
npm install
```


### Troubleshooting: greenlet missing

If startup fails with `No module named 'greenlet'` or `greenlet library is required`, run:

```bash
cd /Users/yingjunnan/acweb/backend
source .venv/bin/activate
pip install -r requirements.txt
```

If greenlet installation fails from a custom mirror, install from PyPI directly:

```bash
pip install -i https://pypi.org/simple greenlet==3.1.1
```

If your local environment cannot access package indexes, run backend in Docker instead:

```bash
cd /Users/yingjunnan/acweb
docker compose up -d postgres backend
```

## PostgreSQL testing (recommended)

### Option A: Docker Compose full stack

```bash
cd /Users/yingjunnan/acweb
docker compose up --build
```

This starts:

- `postgres` on `localhost:5432`
- `redis` on `localhost:6379`
- `backend` with `DATABASE_URL=postgresql+asyncpg://acweb:acweb_dev_pw@postgres:5432/acweb` and `REDIS_URL=redis://redis:6379/0`
- `frontend` on `http://localhost:5173`

### Option B: Run backend locally, DB in Docker

1) Start only PostgreSQL container:

```bash
cd /Users/yingjunnan/acweb
docker compose up -d postgres
```

2) Run backend with Postgres URL:

```bash
cd /Users/yingjunnan/acweb/backend
source .venv/bin/activate
export DATABASE_URL='postgresql+asyncpg://acweb:acweb_dev_pw@localhost:5432/acweb'
export DB_INIT_RETRIES=30
export DB_INIT_RETRY_DELAY=1
uvicorn app.main:app --reload --port 8000
```

3) Keep frontend unchanged:

```bash
cd /Users/yingjunnan/acweb/frontend
npm run dev
```

### Optional: enable Redis fan-out for local backend

1) Start Redis container:

```bash
cd /Users/yingjunnan/acweb
docker compose up -d redis
```

2) Run backend with Redis URL:

```bash
cd /Users/yingjunnan/acweb/backend
source .venv/bin/activate
export REDIS_URL='redis://localhost:6379/0'
uvicorn app.main:app --reload --port 8000
```


### Optional: run migrations explicitly (Alembic)

```bash
cd /Users/yingjunnan/acweb/backend
source .venv/bin/activate
alembic upgrade head
```

If your DB was previously created by auto-create (without Alembic history), run once:

```bash
alembic stamp head
```

Notes:

- Migration files are in `backend/migrations/`.
- Startup keeps `AUTO_CREATE_TABLES=1` by default for easy local onboarding.
- In stricter environments, set `AUTO_CREATE_TABLES=0` and rely on Alembic migrations.

### Persistence verification checklist

1. Create a task from web UI (example: `echo "hello"`).
2. Confirm task appears in `/api/v1/tasks`.
3. Restart backend service/process.
4. Re-open UI and verify the task still exists.
5. Open `/api/v1/tasks/{task_id}/events?from_seq=1` and verify history remains.

Optional automated smoke test:

```bash
cd /Users/yingjunnan/acweb/backend
source .venv/bin/activate
python scripts/smoke_test.py
```

## Docker startup

```bash
cd /Users/yingjunnan/acweb
docker compose up --build
```

## Next iterations

- Add Runner service managed by systemd for stronger process continuity.
- Add HA cursor cache and multi-instance reconciliation optimization.
- Add auth, RBAC, and audit logging.

## Development stages

- Plan overview: `/Users/yingjunnan/acweb/docs/development-plan.md`
- Stage records: `/Users/yingjunnan/acweb/docs/stages/`
  - Stage 1: interactive terminal baseline (completed)
  - Stage 2: persistence and recovery (in progress; Redis fan-out baseline done)
  - Stage 3: auth, RBAC, and audit logging (planned)

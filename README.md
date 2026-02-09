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
- `POST /api/v1/tasks/{id}/stop` terminate running tasks.
- `WS /ws/tasks/{id}` attach to live output and stream terminal events.

Tasks keep running on the server even if the web page disconnects.

## Local development

### 1) Start backend

```bash
cd /Users/yingjunnan/acweb/backend
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --reload --port 8000
```

### 2) Start frontend

```bash
cd /Users/yingjunnan/acweb/frontend
npm install
npm run dev
```

Open `http://localhost:5173`.

## Docker startup

```bash
cd /Users/yingjunnan/acweb
docker compose up --build
```

## Next iterations

- Replace in-memory store with PostgreSQL + Redis.
- Add Runner service managed by systemd for stronger process continuity.
- Add auth, RBAC, and audit logging.
- Integrate xterm.js for interactive TTY behavior.


## Development stages

- Plan overview: `/Users/yingjunnan/acweb/docs/development-plan.md`
- Stage records: `/Users/yingjunnan/acweb/docs/stages/`
  - Stage 1: interactive terminal baseline (completed)
  - Stage 2: persistence and recovery (planned)
  - Stage 3: auth, RBAC, and audit logging (planned)

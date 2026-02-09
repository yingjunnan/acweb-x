from __future__ import annotations

import asyncio
import contextlib
from typing import Any

from fastapi import FastAPI, HTTPException, Query, WebSocket, WebSocketDisconnect
from fastapi.middleware.cors import CORSMiddleware

from .models import CreateTaskResponse, EventsResponse, TaskCreateRequest, TaskDetail, TaskInputRequest
from .store import store

app = FastAPI(title="acweb API", version="0.1.0")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/api/v1/health")
async def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/api/v1/projects")
async def list_projects() -> list[dict[str, Any]]:
    return [project.model_dump() for project in store.list_projects()]


@app.get("/api/v1/tasks")
async def list_tasks() -> list[dict[str, Any]]:
    records = await store.list_tasks()
    return [record.to_summary().model_dump() for record in records]


@app.post("/api/v1/tasks", response_model=CreateTaskResponse)
async def create_task(payload: TaskCreateRequest) -> CreateTaskResponse:
    task = await store.create_task(command=payload.command, cwd=payload.cwd)
    return CreateTaskResponse(
        task=TaskDetail(
            **task.to_summary().model_dump(),
            events_count=len(task.events),
        )
    )


@app.get("/api/v1/tasks/{task_id}")
async def get_task(task_id: str) -> dict[str, Any]:
    task = await store.get_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return TaskDetail(**task.to_summary().model_dump(), events_count=len(task.events)).model_dump()


@app.post("/api/v1/tasks/{task_id}/stop")
async def stop_task(task_id: str) -> dict[str, Any]:
    task = await store.stop_task(task_id)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return {"ok": True, "task_id": task_id}


@app.post("/api/v1/tasks/{task_id}/input")
async def write_input(task_id: str, payload: TaskInputRequest) -> dict[str, Any]:
    success = await store.write_input(task_id, payload.data)
    if not success:
        raise HTTPException(status_code=400, detail="Task is not writable")
    return {"ok": True}


@app.get("/api/v1/tasks/{task_id}/events", response_model=EventsResponse)
async def task_events(task_id: str, from_seq: int = Query(default=1, ge=1)) -> EventsResponse:
    task, events = await store.events_since(task_id, from_seq)
    if not task:
        raise HTTPException(status_code=404, detail="Task not found")
    return EventsResponse(
        task_id=task.id,
        from_seq=from_seq,
        next_seq=task.next_seq,
        items=events,
    )


@app.websocket("/ws/tasks/{task_id}")
async def task_socket(websocket: WebSocket, task_id: str, from_seq: int = 1) -> None:
    await websocket.accept()
    task, queue = await store.subscribe(task_id)
    if not task or not queue:
        await websocket.send_json({"type": "error", "message": "Task not found"})
        await websocket.close(code=4404)
        return

    snapshot = [event.model_dump(mode="json") for event in task.events if event.seq >= from_seq]
    await websocket.send_json(
        {
            "type": "attached",
            "task": task.to_summary().model_dump(mode="json"),
            "next_seq": task.next_seq,
            "snapshot": snapshot,
        }
    )

    sender = asyncio.create_task(_sender_loop(websocket, queue))
    receiver = asyncio.create_task(_receiver_loop(websocket, task_id))

    done, pending = await asyncio.wait(
        {sender, receiver},
        return_when=asyncio.FIRST_COMPLETED,
    )

    for work in pending:
        work.cancel()
    for work in done:
        with contextlib.suppress(Exception):
            await work

    await store.unsubscribe(task, queue)


async def _sender_loop(websocket: WebSocket, queue: asyncio.Queue[Any]) -> None:
    while True:
        event = await queue.get()
        await websocket.send_json({"type": "output", "event": event.model_dump(mode="json")})


async def _receiver_loop(websocket: WebSocket, task_id: str) -> None:
    while True:
        try:
            message = await websocket.receive_json()
        except WebSocketDisconnect:
            return

        event_type = message.get("type")
        if event_type == "ping":
            await websocket.send_json({"type": "pong"})
        elif event_type == "input":
            data = message.get("data", "")
            await store.write_input(task_id, data)
        elif event_type == "stop":
            await store.stop_task(task_id)

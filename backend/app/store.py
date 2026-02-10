from __future__ import annotations

import asyncio
import contextlib
import os
import pty
import shlex
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import cast
from uuid import uuid4

from sqlalchemy import func, select

from .db import SessionLocal, TaskEventRow, TaskRow
from .models import Project, StreamType, TaskEvent, TaskState, TaskSummary


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


@dataclass
class TaskRecord:
    id: str
    command: str
    cwd: str | None
    state: TaskState
    created_at: datetime
    started_at: datetime | None = None
    finished_at: datetime | None = None
    exit_code: int | None = None
    events: list[TaskEvent] = field(default_factory=list)
    next_seq: int = 1

    def to_summary(self) -> TaskSummary:
        return TaskSummary(
            id=self.id,
            command=self.command,
            cwd=self.cwd,
            state=self.state,
            created_at=self.created_at,
            started_at=self.started_at,
            finished_at=self.finished_at,
            exit_code=self.exit_code,
        )


@dataclass
class RuntimeHandle:
    process: asyncio.subprocess.Process
    master_fd: int
    reader_task: asyncio.Task[None]


class TaskStore:
    def __init__(self) -> None:
        self._subscribers: dict[str, set[asyncio.Queue[TaskEvent]]] = {}
        self._subscribers_lock = asyncio.Lock()
        self._event_lock = asyncio.Lock()
        self._runtime: dict[str, RuntimeHandle] = {}
        self._projects = [
            Project(id="default", name="Default Workspace", path=str(Path.cwd())),
            Project(id="docs", name="Content Studio", path=str(Path.cwd() / "content")),
        ]

    def list_projects(self) -> list[Project]:
        return self._projects

    async def list_tasks(self) -> list[TaskRecord]:
        async with SessionLocal() as session:
            result = await session.execute(select(TaskRow).order_by(TaskRow.created_at.desc()))
            rows = result.scalars().all()
        return [self._row_to_record(row=row, events=[], next_seq=1) for row in rows]

    async def get_task(self, task_id: str) -> TaskRecord | None:
        async with SessionLocal() as session:
            row = await session.get(TaskRow, task_id)
            if not row:
                return None
            events = await self._load_events(session, task_id)
            next_seq = await self._next_seq(session, task_id)
        return self._row_to_record(row=row, events=events, next_seq=next_seq)

    async def create_task(self, command: str, cwd: str | None) -> TaskRecord:
        task_id = str(uuid4())
        now = utc_now()

        row = TaskRow(
            id=task_id,
            command=command,
            cwd=cwd,
            state="queued",
            created_at=now,
            started_at=None,
            finished_at=None,
            exit_code=None,
        )

        async with SessionLocal() as session:
            session.add(row)
            await session.commit()

        task = self._row_to_record(row=row, events=[], next_seq=1)
        asyncio.create_task(self._run_task(task.id))
        return task

    async def recover_incomplete_tasks(self) -> int:
        async with SessionLocal() as session:
            result = await session.execute(select(TaskRow).where(TaskRow.state.in_(["queued", "running"])))
            rows = result.scalars().all()
            if not rows:
                return 0

            for row in rows:
                row.state = "failed"
                row.finished_at = utc_now()
                if row.exit_code is None:
                    row.exit_code = 255

            await session.commit()

        for row in rows:
            await self.append_event(
                row.id,
                "system",
                "[acweb] recovered after service restart; previous process ended unexpectedly\n",
            )

        return len(rows)

    async def stop_task(self, task_id: str) -> TaskRecord | None:
        runtime = self._runtime.get(task_id)

        async with SessionLocal() as session:
            row = await session.get(TaskRow, task_id)
            if not row:
                return None
            if runtime and runtime.process.returncode is None:
                row.state = "stopped"
                await session.commit()
                runtime.process.terminate()

        if runtime and runtime.process.returncode is None:
            await self.append_event(task_id, "system", "[acweb] terminate signal sent\n")

        return await self.get_task(task_id)

    async def write_input(self, task_id: str, data: str) -> bool:
        for _ in range(40):
            runtime = self._runtime.get(task_id)
            if runtime and runtime.process.returncode is None:
                try:
                    os.write(runtime.master_fd, data.encode("utf-8", errors="replace"))
                except OSError:
                    return False
                return True

            task = await self.get_task(task_id)
            if not task or task.state not in ("queued", "running"):
                return False

            await asyncio.sleep(0.05)

        return False

    async def subscribe(self, task_id: str) -> tuple[TaskRecord | None, asyncio.Queue[TaskEvent] | None]:
        task = await self.get_task(task_id)
        if not task:
            return None, None

        queue: asyncio.Queue[TaskEvent] = asyncio.Queue()
        async with self._subscribers_lock:
            if task_id not in self._subscribers:
                self._subscribers[task_id] = set()
            self._subscribers[task_id].add(queue)

        return task, queue

    async def unsubscribe(self, task: TaskRecord, queue: asyncio.Queue[TaskEvent]) -> None:
        async with self._subscribers_lock:
            queues = self._subscribers.get(task.id)
            if not queues:
                return
            queues.discard(queue)
            if not queues:
                self._subscribers.pop(task.id, None)

    async def events_since(self, task_id: str, from_seq: int) -> tuple[TaskRecord | None, list[TaskEvent]]:
        async with SessionLocal() as session:
            row = await session.get(TaskRow, task_id)
            if not row:
                return None, []
            next_seq = await self._next_seq(session, task_id)
            result = await session.execute(
                select(TaskEventRow)
                .where(TaskEventRow.task_id == task_id, TaskEventRow.seq >= from_seq)
                .order_by(TaskEventRow.seq.asc())
            )
            event_rows = result.scalars().all()

        events = [self._event_row_to_model(item) for item in event_rows]
        task = self._row_to_record(row=row, events=[], next_seq=next_seq)
        return task, events

    async def append_event(self, task_id: str, stream: str, data: str) -> TaskEvent:
        async with self._event_lock:
            now = utc_now()
            async with SessionLocal() as session:
                next_seq = await self._next_seq(session, task_id)
                row = TaskEventRow(
                    task_id=task_id,
                    seq=next_seq,
                    stream=stream,
                    data=data,
                    ts=now,
                )
                session.add(row)
                await session.commit()

        event = TaskEvent(
            seq=next_seq,
            task_id=task_id,
            stream=cast(StreamType, stream),
            data=data,
            ts=now,
        )

        async with self._subscribers_lock:
            queues = list(self._subscribers.get(task_id, set()))

        dead_queues: list[asyncio.Queue[TaskEvent]] = []
        for queue in queues:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)

        if dead_queues:
            async with self._subscribers_lock:
                current = self._subscribers.get(task_id)
                if current:
                    for queue in dead_queues:
                        current.discard(queue)

        return event

    async def _run_task(self, task_id: str) -> None:
        task = await self.get_task(task_id)
        if not task:
            return

        await self._mark_started(task_id)
        await self.append_event(task_id, "system", f"[acweb] started: {task.command}\n")

        exit_code: int | None = None
        final_state: TaskState = "failed"
        master_fd: int | None = None
        slave_fd: int | None = None
        reader_task: asyncio.Task[None] | None = None

        try:
            master_fd, slave_fd = pty.openpty()
            env = os.environ.copy()
            env.setdefault("TERM", "xterm-256color")

            process = await asyncio.create_subprocess_exec(
                *shlex.split(task.command),
                stdin=slave_fd,
                stdout=slave_fd,
                stderr=slave_fd,
                cwd=task.cwd,
                env=env,
                start_new_session=True,
            )

            os.close(slave_fd)
            slave_fd = None

            reader_task = asyncio.create_task(self._pty_reader(task_id, master_fd))
            self._runtime[task_id] = RuntimeHandle(process=process, master_fd=master_fd, reader_task=reader_task)

            exit_code = await process.wait()
            await reader_task

            current = await self.get_task(task_id)
            if current and current.state == "stopped":
                final_state = "stopped"
            else:
                final_state = "success" if exit_code == 0 else "failed"
        except FileNotFoundError as exc:
            exit_code = 127
            final_state = "failed"
            await self.append_event(task_id, "stderr", f"[acweb] command failed: {exc}\n")
        except Exception as exc:
            exit_code = 1
            final_state = "failed"
            await self.append_event(task_id, "stderr", f"[acweb] unexpected error: {exc}\n")
        finally:
            runtime = self._runtime.pop(task_id, None)
            if runtime:
                if not runtime.reader_task.done():
                    runtime.reader_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await runtime.reader_task
                with contextlib.suppress(OSError):
                    os.close(runtime.master_fd)
            else:
                if reader_task and not reader_task.done():
                    reader_task.cancel()
                    with contextlib.suppress(asyncio.CancelledError):
                        await reader_task
                if master_fd is not None:
                    with contextlib.suppress(OSError):
                        os.close(master_fd)

            if slave_fd is not None:
                with contextlib.suppress(OSError):
                    os.close(slave_fd)

            current = await self.get_task(task_id)
            if current and current.state == "stopped":
                final_state = "stopped"
            await self._mark_finished(task_id, final_state, exit_code)
            await self.append_event(
                task_id,
                "system",
                f"[acweb] finished with state={final_state} exit_code={exit_code}\n",
            )

    async def _pty_reader(self, task_id: str, master_fd: int) -> None:
        loop = asyncio.get_running_loop()
        while True:
            try:
                chunk = await loop.run_in_executor(None, os.read, master_fd, 1024)
            except OSError:
                return

            if not chunk:
                return

            text = chunk.decode("utf-8", errors="replace")
            await self.append_event(task_id, "stdout", text)

    async def _load_events(self, session, task_id: str) -> list[TaskEvent]:
        result = await session.execute(
            select(TaskEventRow).where(TaskEventRow.task_id == task_id).order_by(TaskEventRow.seq.asc())
        )
        return [self._event_row_to_model(item) for item in result.scalars().all()]

    async def _next_seq(self, session, task_id: str) -> int:
        result = await session.execute(select(func.max(TaskEventRow.seq)).where(TaskEventRow.task_id == task_id))
        max_seq = result.scalar_one_or_none() or 0
        return int(max_seq) + 1

    async def _mark_started(self, task_id: str) -> None:
        async with SessionLocal() as session:
            row = await session.get(TaskRow, task_id)
            if not row:
                return
            row.state = "running"
            row.started_at = utc_now()
            await session.commit()

    async def _mark_finished(self, task_id: str, state: TaskState, exit_code: int | None) -> None:
        async with SessionLocal() as session:
            row = await session.get(TaskRow, task_id)
            if not row:
                return
            if row.state == "stopped":
                state = "stopped"
            row.state = state
            row.exit_code = exit_code
            row.finished_at = utc_now()
            await session.commit()

    def _row_to_record(self, row: TaskRow, events: list[TaskEvent], next_seq: int) -> TaskRecord:
        return TaskRecord(
            id=row.id,
            command=row.command,
            cwd=row.cwd,
            state=cast(TaskState, row.state),
            created_at=row.created_at,
            started_at=row.started_at,
            finished_at=row.finished_at,
            exit_code=row.exit_code,
            events=events,
            next_seq=next_seq,
        )

    def _event_row_to_model(self, row: TaskEventRow) -> TaskEvent:
        return TaskEvent(
            seq=row.seq,
            task_id=row.task_id,
            stream=cast(StreamType, row.stream),
            data=row.data,
            ts=row.ts,
        )


store = TaskStore()

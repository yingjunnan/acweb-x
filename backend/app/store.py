from __future__ import annotations

import asyncio
from dataclasses import dataclass, field
from datetime import datetime, timezone
from pathlib import Path
import shlex
from uuid import uuid4

from .models import Project, TaskEvent, TaskState, TaskSummary


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
    process: asyncio.subprocess.Process | None = None
    subscribers: set[asyncio.Queue[TaskEvent]] = field(default_factory=set)

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


class TaskStore:
    def __init__(self) -> None:
        self._tasks: dict[str, TaskRecord] = {}
        self._lock = asyncio.Lock()
        self._projects = [
            Project(id="default", name="Default Workspace", path=str(Path.cwd())),
            Project(id="docs", name="Content Studio", path=str(Path.cwd() / "content")),
        ]

    def list_projects(self) -> list[Project]:
        return self._projects

    async def list_tasks(self) -> list[TaskRecord]:
        async with self._lock:
            return sorted(self._tasks.values(), key=lambda t: t.created_at, reverse=True)

    async def get_task(self, task_id: str) -> TaskRecord | None:
        async with self._lock:
            return self._tasks.get(task_id)

    async def create_task(self, command: str, cwd: str | None) -> TaskRecord:
        task = TaskRecord(
            id=str(uuid4()),
            command=command,
            cwd=cwd,
            state="queued",
            created_at=utc_now(),
        )
        async with self._lock:
            self._tasks[task.id] = task
        asyncio.create_task(self._run_task(task.id))
        return task

    async def stop_task(self, task_id: str) -> TaskRecord | None:
        task = await self.get_task(task_id)
        if not task:
            return None
        process = task.process
        if process and process.returncode is None:
            task.state = "stopped"
            process.terminate()
            await self.append_event(task, "system", "[acweb] terminate signal sent\n")
        return task

    async def write_input(self, task_id: str, data: str) -> bool:
        task = await self.get_task(task_id)
        if not task or not task.process or not task.process.stdin:
            return False
        if task.process.returncode is not None:
            return False
        task.process.stdin.write(data.encode("utf-8", errors="replace"))
        await task.process.stdin.drain()
        return True

    async def subscribe(self, task_id: str) -> tuple[TaskRecord | None, asyncio.Queue[TaskEvent] | None]:
        task = await self.get_task(task_id)
        if not task:
            return None, None
        queue: asyncio.Queue[TaskEvent] = asyncio.Queue()
        task.subscribers.add(queue)
        return task, queue

    async def unsubscribe(self, task: TaskRecord, queue: asyncio.Queue[TaskEvent]) -> None:
        task.subscribers.discard(queue)

    async def events_since(self, task_id: str, from_seq: int) -> tuple[TaskRecord | None, list[TaskEvent]]:
        task = await self.get_task(task_id)
        if not task:
            return None, []
        return task, [event for event in task.events if event.seq >= from_seq]

    async def append_event(self, task: TaskRecord, stream: str, data: str) -> TaskEvent:
        event = TaskEvent(
            seq=task.next_seq,
            task_id=task.id,
            stream=stream,  # type: ignore[arg-type]
            data=data,
            ts=utc_now(),
        )
        task.next_seq += 1
        task.events.append(event)

        dead_queues: list[asyncio.Queue[TaskEvent]] = []
        for queue in task.subscribers:
            try:
                queue.put_nowait(event)
            except asyncio.QueueFull:
                dead_queues.append(queue)
        for queue in dead_queues:
            task.subscribers.discard(queue)
        return event

    async def _run_task(self, task_id: str) -> None:
        task = await self.get_task(task_id)
        if not task:
            return

        task.state = "running"
        task.started_at = utc_now()
        await self.append_event(task, "system", f"[acweb] started: {task.command}\n")

        try:
            process = await asyncio.create_subprocess_exec(
                *shlex.split(task.command),
                stdin=asyncio.subprocess.PIPE,
                stdout=asyncio.subprocess.PIPE,
                stderr=asyncio.subprocess.PIPE,
                cwd=task.cwd,
            )
            task.process = process

            stdout_task = asyncio.create_task(self._stream_reader(task, process.stdout, "stdout"))
            stderr_task = asyncio.create_task(self._stream_reader(task, process.stderr, "stderr"))

            return_code = await process.wait()
            await asyncio.gather(stdout_task, stderr_task)
            task.exit_code = return_code

            if task.state != "stopped":
                task.state = "success" if return_code == 0 else "failed"
        except FileNotFoundError as exc:
            task.state = "failed"
            task.exit_code = 127
            await self.append_event(task, "stderr", f"[acweb] command failed: {exc}\n")
        except Exception as exc:
            task.state = "failed"
            task.exit_code = 1
            await self.append_event(task, "stderr", f"[acweb] unexpected error: {exc}\n")
        finally:
            task.finished_at = utc_now()
            await self.append_event(task, "system", f"[acweb] finished with state={task.state} exit_code={task.exit_code}\n")

    async def _stream_reader(
        self,
        task: TaskRecord,
        stream: asyncio.StreamReader | None,
        stream_name: str,
    ) -> None:
        if not stream:
            return
        while True:
            line = await stream.readline()
            if not line:
                return
            text = line.decode("utf-8", errors="replace")
            await self.append_event(task, stream_name, text)


store = TaskStore()

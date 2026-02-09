from __future__ import annotations

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TaskState = Literal["queued", "running", "success", "failed", "stopped"]
StreamType = Literal["stdout", "stderr", "system"]


class Project(BaseModel):
    id: str
    name: str
    path: str


class TaskCreateRequest(BaseModel):
    command: str = Field(min_length=1)
    cwd: str | None = None
    project_id: str | None = None


class TaskInputRequest(BaseModel):
    data: str


class TaskSummary(BaseModel):
    id: str
    command: str
    cwd: str | None
    state: TaskState
    created_at: datetime
    started_at: datetime | None
    finished_at: datetime | None
    exit_code: int | None


class TaskEvent(BaseModel):
    seq: int
    task_id: str
    stream: StreamType
    data: str
    ts: datetime


class TaskDetail(TaskSummary):
    events_count: int


class CreateTaskResponse(BaseModel):
    task: TaskDetail


class EventsResponse(BaseModel):
    task_id: str
    from_seq: int
    next_seq: int
    items: list[TaskEvent]

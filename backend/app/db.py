from __future__ import annotations

import asyncio
import os
from datetime import datetime

from sqlalchemy import DateTime, ForeignKey, Index, Integer, String, Text, UniqueConstraint
from sqlalchemy.ext.asyncio import async_sessionmaker, create_async_engine
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column


def _default_database_url() -> str:
    return "sqlite+aiosqlite:///./acweb.db"


def _normalize_database_url(raw_url: str) -> str:
    if raw_url.startswith("postgres://"):
        return "postgresql+asyncpg://" + raw_url[len("postgres://") :]
    if raw_url.startswith("postgresql://") and not raw_url.startswith("postgresql+asyncpg://"):
        return "postgresql+asyncpg://" + raw_url[len("postgresql://") :]
    return raw_url


DATABASE_URL = _normalize_database_url(os.getenv("DATABASE_URL", _default_database_url()))
DB_INIT_RETRIES = int(os.getenv("DB_INIT_RETRIES", "1"))
DB_INIT_RETRY_DELAY = float(os.getenv("DB_INIT_RETRY_DELAY", "1.5"))
AUTO_CREATE_TABLES = os.getenv("AUTO_CREATE_TABLES", "1") == "1"


class Base(DeclarativeBase):
    pass


class TaskRow(Base):
    __tablename__ = "tasks"

    id: Mapped[str] = mapped_column(String(64), primary_key=True)
    command: Mapped[str] = mapped_column(Text, nullable=False)
    cwd: Mapped[str | None] = mapped_column(Text, nullable=True)
    state: Mapped[str] = mapped_column(String(16), nullable=False)
    created_at: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)
    started_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    finished_at: Mapped[datetime | None] = mapped_column(DateTime(timezone=True), nullable=True)
    exit_code: Mapped[int | None] = mapped_column(Integer, nullable=True)


class TaskEventRow(Base):
    __tablename__ = "task_events"
    __table_args__ = (
        UniqueConstraint("task_id", "seq", name="uq_task_events_task_seq"),
        Index("ix_task_events_task_seq", "task_id", "seq"),
    )

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=True)
    task_id: Mapped[str] = mapped_column(String(64), ForeignKey("tasks.id", ondelete="CASCADE"), nullable=False)
    seq: Mapped[int] = mapped_column(Integer, nullable=False)
    stream: Mapped[str] = mapped_column(String(16), nullable=False)
    data: Mapped[str] = mapped_column(Text, nullable=False)
    ts: Mapped[datetime] = mapped_column(DateTime(timezone=True), nullable=False)


engine = create_async_engine(DATABASE_URL, future=True, pool_pre_ping=True)
SessionLocal = async_sessionmaker(engine, expire_on_commit=False)


async def init_db() -> None:
    retries = max(DB_INIT_RETRIES, 1)
    last_error: Exception | None = None

    for attempt in range(1, retries + 1):
        try:
            async with engine.connect() as conn:
                await conn.run_sync(lambda _: None)
            if AUTO_CREATE_TABLES:
                async with engine.begin() as conn:
                    await conn.run_sync(Base.metadata.create_all)
            return
        except ValueError as exc:
            if "greenlet library is required" in str(exc):
                raise RuntimeError(
                    "Missing dependency: greenlet. Run `pip install -r backend/requirements.txt` in your venv."
                ) from exc
            last_error = exc
            if attempt >= retries:
                break
            await asyncio.sleep(DB_INIT_RETRY_DELAY)
        except Exception as exc:  # noqa: BLE001
            last_error = exc
            if attempt >= retries:
                break
            await asyncio.sleep(DB_INIT_RETRY_DELAY)

    if last_error:
        raise last_error

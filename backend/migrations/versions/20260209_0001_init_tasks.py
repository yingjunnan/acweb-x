"""init tasks and task_events

Revision ID: 20260209_0001
Revises: 
Create Date: 2026-02-09 19:30:00

"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa


revision: str = "20260209_0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "tasks",
        sa.Column("id", sa.String(length=64), nullable=False),
        sa.Column("command", sa.Text(), nullable=False),
        sa.Column("cwd", sa.Text(), nullable=True),
        sa.Column("state", sa.String(length=16), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("started_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("finished_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column("exit_code", sa.Integer(), nullable=True),
        sa.PrimaryKeyConstraint("id"),
    )

    op.create_table(
        "task_events",
        sa.Column("id", sa.Integer(), autoincrement=True, nullable=False),
        sa.Column("task_id", sa.String(length=64), nullable=False),
        sa.Column("seq", sa.Integer(), nullable=False),
        sa.Column("stream", sa.String(length=16), nullable=False),
        sa.Column("data", sa.Text(), nullable=False),
        sa.Column("ts", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["task_id"], ["tasks.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("task_id", "seq", name="uq_task_events_task_seq"),
    )
    op.create_index("ix_task_events_task_seq", "task_events", ["task_id", "seq"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_task_events_task_seq", table_name="task_events")
    op.drop_table("task_events")
    op.drop_table("tasks")

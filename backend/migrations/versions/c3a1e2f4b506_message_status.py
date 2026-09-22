"""add messages.status for stopped/error streaming replies

Revision ID: c3a1e2f4b506
Revises: bf307b8f9d51
Create Date: 2026-09-22

Adds ``messages.status`` (``completed`` | ``stopped`` | ``error``) so a
partial assistant reply preserved when the client aborts the SSE stream (or
the provider fails mid-stream) is distinguishable from a complete one.
Existing rows default to ``completed`` — no conversation/message data is
modified.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "c3a1e2f4b506"
down_revision: Union[str, None] = "bf307b8f9d51"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.add_column(
        "messages",
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'completed'"),
            nullable=False,
        ),
    )


def downgrade() -> None:
    op.drop_column("messages", "status")

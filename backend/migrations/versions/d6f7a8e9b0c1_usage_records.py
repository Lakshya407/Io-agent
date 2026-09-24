"""add usage_records table + daily/enable flags on usage_allowances

Revision ID: d6f7a8e9b0c1
Revises: c3a1e2f4b506
Create Date: 2026-09-24 00:00:00.000000+00:00

Phase 9 (Usage + Token Tracking):

* ``usage_records`` — one row per LLM request (completed, failed or
  cancelled), recording who/what/when/how long/how many tokens. It is the
  persistent source of usage history; the monthly counters on
  ``usage_allowances`` remain the fast allowance check. ``conversation_id``
  and ``message_id`` are ``SET NULL`` on delete so usage history survives
  conversation deletion.
* ``usage_allowances`` gains optional daily token/request limits and an
  ``is_enabled`` flag so admins can cap per-day usage or suspend an
  allowance entirely without deleting it.

No existing rows are modified; new allowance columns default to "no daily
limit" (NULL) and enabled (true).
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "d6f7a8e9b0c1"
down_revision: Union[str, None] = "c3a1e2f4b506"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Per-request usage records -------------------------------------
    op.create_table(
        "usage_records",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("user_id", sa.UUID(), nullable=False),
        sa.Column("conversation_id", sa.UUID(), nullable=True),
        sa.Column("message_id", sa.UUID(), nullable=True),
        sa.Column("model", sa.String(length=255), nullable=False),
        sa.Column("provider", sa.String(length=100), nullable=False),
        sa.Column("prompt_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("completion_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("total_tokens", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column(
            "is_estimated",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="True when the provider did not report token counts and "
            "the values were estimated from text length.",
        ),
        sa.Column("request_timestamp", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("response_duration_ms", sa.Integer(), nullable=True),
        sa.Column(
            "request_status",
            sa.String(length=50),
            server_default=sa.text("'completed'"),
            nullable=False,
            comment="completed | failed | cancelled",
        ),
        sa.Column("error_info", postgresql.JSONB(astext_type=sa.Text()), nullable=True),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["conversation_id"], ["conversations.id"], ondelete="SET NULL"),
        sa.ForeignKeyConstraint(["message_id"], ["messages.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_usage_records_user_id", "usage_records", ["user_id"], unique=False)
    op.create_index(
        "ix_usage_records_conversation_id", "usage_records", ["conversation_id"], unique=False
    )
    op.create_index("ix_usage_records_model", "usage_records", ["model"], unique=False)
    op.create_index(
        "ix_usage_records_request_timestamp", "usage_records", ["request_timestamp"], unique=False
    )

    # --- Allowance: daily limits + enable flag -------------------------
    op.add_column(
        "usage_allowances",
        sa.Column(
            "daily_token_limit",
            sa.Integer(),
            nullable=True,
            comment="Optional per-UTC-day token cap (NULL = unlimited).",
        ),
    )
    op.add_column(
        "usage_allowances",
        sa.Column(
            "daily_request_limit",
            sa.Integer(),
            nullable=True,
            comment="Optional per-UTC-day request cap (NULL = unlimited).",
        ),
    )
    op.add_column(
        "usage_allowances",
        sa.Column(
            "is_enabled",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="When false the user may not send LLM requests at all.",
        ),
    )


def downgrade() -> None:
    op.drop_column("usage_allowances", "is_enabled")
    op.drop_column("usage_allowances", "daily_request_limit")
    op.drop_column("usage_allowances", "daily_token_limit")
    op.drop_index("ix_usage_records_request_timestamp", table_name="usage_records")
    op.drop_index("ix_usage_records_model", table_name="usage_records")
    op.drop_index("ix_usage_records_conversation_id", table_name="usage_records")
    op.drop_index("ix_usage_records_user_id", table_name="usage_records")
    op.drop_table("usage_records")

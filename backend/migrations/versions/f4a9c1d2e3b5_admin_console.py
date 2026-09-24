"""add prompts, routing_rules and rate_limit_rules tables (admin console)

Revision ID: f4a9c1d2e3b5
Revises: d6f7a8e9b0c1
Create Date: 2026-09-24 00:00:00.000000+00:00

Powers three admin-console sections that previously held demo data:

* ``prompts`` — editable system prompts; the active default one replaces the
  built-in chat system instruction (falling back to it when none is set).
* ``routing_rules`` — priority-ordered request-type → model routing applied
  when a chat request names no explicit model.
* ``rate_limit_rules`` — DB-configurable limits for the Redis rate limiter.
  An empty table means "use the built-in ``RATE_LIMIT_*`` settings", so
  upgrading never changes current behaviour.
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f4a9c1d2e3b5"
down_revision: Union[str, None] = "d6f7a8e9b0c1"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    # --- Prompt management ---------------------------------------------
    op.create_table(
        "prompts",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("name", sa.String(length=255), nullable=False),
        sa.Column("purpose", sa.String(length=255), server_default=sa.text("''"), nullable=False),
        sa.Column(
            "model",
            sa.String(length=255),
            nullable=True,
            comment="Optional model this prompt targets (informational).",
        ),
        sa.Column("version", sa.Integer(), server_default=sa.text("1"), nullable=False),
        sa.Column(
            "status",
            sa.String(length=20),
            server_default=sa.text("'draft'"),
            nullable=False,
            comment="active | draft | inactive",
        ),
        sa.Column("content", sa.Text(), nullable=False),
        sa.Column(
            "is_default",
            sa.Boolean(),
            server_default=sa.text("false"),
            nullable=False,
            comment="The single active default prompt used by chat.",
        ),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("name"),
    )
    op.create_index("ix_prompts_status", "prompts", ["status"], unique=False)
    # At most ONE default prompt can exist at a time (partial unique index).
    op.create_index(
        "uq_prompts_default",
        "prompts",
        ["is_default"],
        unique=True,
        postgresql_where=sa.text("is_default"),
    )

    # --- Model routing ---------------------------------------------------
    op.create_table(
        "routing_rules",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column("priority", sa.Integer(), nullable=False, comment="1 = highest"),
        sa.Column("request_type", sa.String(length=100), nullable=False),
        sa.Column("primary_model", sa.String(length=255), nullable=False),
        sa.Column("fallback_model", sa.String(length=255), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("request_type"),
    )
    op.create_index("ix_routing_rules_priority", "routing_rules", ["priority"], unique=False)

    # --- Rate limiting ----------------------------------------------------
    op.create_table(
        "rate_limit_rules",
        sa.Column("id", sa.UUID(), server_default=sa.text("gen_random_uuid()"), nullable=False),
        sa.Column(
            "scope",
            sa.String(length=50),
            server_default=sa.text("'all'"),
            nullable=False,
            comment="all | user | ip",
        ),
        sa.Column("limit", sa.Integer(), nullable=False, comment="Requests allowed per window"),
        sa.Column("window_seconds", sa.Integer(), nullable=False),
        sa.Column(
            "action",
            sa.String(length=30),
            server_default=sa.text("'block'"),
            nullable=False,
            comment="Only 'block' is enforced today",
        ),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), server_default=sa.text("now()"), nullable=False),
        sa.PrimaryKeyConstraint("id"),
    )
    op.create_index("ix_rate_limit_rules_is_active", "rate_limit_rules", ["is_active"], unique=False)


def downgrade() -> None:
    op.drop_index("ix_rate_limit_rules_is_active", table_name="rate_limit_rules")
    op.drop_table("rate_limit_rules")
    op.drop_index("ix_routing_rules_priority", table_name="routing_rules")
    op.drop_table("routing_rules")
    op.drop_index("uq_prompts_default", table_name="prompts")
    op.drop_index("ix_prompts_status", table_name="prompts")
    op.drop_table("prompts")

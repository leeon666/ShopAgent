"""add agent proposals, traces, and audit events

Revision ID: 0029_shopagent_agent_control
Revises: 0028_shopagent_domain
Create Date: 2026-11-15T21:30:00+00:00
"""

import sqlalchemy as sa
from sqlalchemy.dialects import postgresql
from sqlalchemy.dialects.postgresql import UUID as PG_UUID

from alembic import op

revision = "0029_shopagent_agent_control"
down_revision = "0028_shopagent_domain"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "shop_action_proposals",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("proposal_no", sa.String(40), nullable=False),
        sa.Column(
            "ticket_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("shop_after_sales_tickets.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("recommended_action", sa.String(32), nullable=False),
        sa.Column("refund_amount", sa.Numeric(12, 2), nullable=True),
        sa.Column("rationale", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "evidence",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'[]'::jsonb"),
        ),
        sa.Column("status", sa.String(20), nullable=False, server_default="pending"),
        sa.Column("agent_trace_id", sa.String(100), nullable=True),
        sa.Column(
            "decided_by_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("decision_note", sa.Text(), nullable=False, server_default=""),
        sa.Column("decided_at", sa.DateTime(timezone=True), nullable=True),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index(
        "ix_shop_action_proposals_proposal_no",
        "shop_action_proposals",
        ["proposal_no"],
        unique=True,
    )
    op.create_index("ix_shop_action_proposals_ticket_id", "shop_action_proposals", ["ticket_id"])
    op.create_index("ix_shop_action_proposals_user_id", "shop_action_proposals", ["user_id"])
    op.create_index("ix_shop_action_proposals_status", "shop_action_proposals", ["status"])
    op.create_index(
        "ix_shop_action_proposals_agent_trace_id",
        "shop_action_proposals",
        ["agent_trace_id"],
    )

    op.create_table(
        "shop_agent_runs",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column("trace_id", sa.String(100), nullable=False),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column(
            "user_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "conversation_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("conversations.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("model", sa.String(100), nullable=False),
        sa.Column("prompt_version", sa.String(50), nullable=False),
        sa.Column("prompt", sa.Text(), nullable=False, server_default=""),
        sa.Column("status", sa.String(20), nullable=False, server_default="running"),
        sa.Column("stop_reason", sa.String(100), nullable=True),
        sa.Column("input_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("output_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("total_tokens", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "run_metadata",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=True),
    )
    op.create_index("ix_shop_agent_runs_trace_id", "shop_agent_runs", ["trace_id"], unique=True)
    op.create_index("ix_shop_agent_runs_request_id", "shop_agent_runs", ["request_id"])
    op.create_index("ix_shop_agent_runs_user_id", "shop_agent_runs", ["user_id"])
    op.create_index("ix_shop_agent_runs_status", "shop_agent_runs", ["status"])

    op.create_table(
        "shop_agent_steps",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "run_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("shop_agent_runs.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("sequence", sa.Integer(), nullable=False),
        sa.Column("node", sa.String(50), nullable=False),
        sa.Column("status", sa.String(20), nullable=False),
        sa.Column("latency_ms", sa.Integer(), nullable=False, server_default="0"),
        sa.Column("tool_name", sa.String(100), nullable=True),
        sa.Column(
            "payload",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column("error", sa.Text(), nullable=False, server_default=""),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_shop_agent_steps_run_id", "shop_agent_steps", ["run_id"])

    op.create_table(
        "shop_audit_events",
        sa.Column(
            "id",
            PG_UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "actor_id",
            PG_UUID(as_uuid=True),
            sa.ForeignKey("users.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("action", sa.String(100), nullable=False),
        sa.Column("entity_type", sa.String(50), nullable=False),
        sa.Column("entity_id", PG_UUID(as_uuid=True), nullable=True),
        sa.Column("request_id", sa.String(100), nullable=True),
        sa.Column(
            "details",
            postgresql.JSONB(astext_type=sa.Text()),
            nullable=False,
            server_default=sa.text("'{}'::jsonb"),
        ),
        sa.Column(
            "created_at", sa.DateTime(timezone=True), server_default=sa.func.now(), nullable=False
        ),
    )
    op.create_index("ix_shop_audit_events_actor_id", "shop_audit_events", ["actor_id"])
    op.create_index("ix_shop_audit_events_action", "shop_audit_events", ["action"])
    op.create_index("ix_shop_audit_events_entity_type", "shop_audit_events", ["entity_type"])
    op.create_index("ix_shop_audit_events_entity_id", "shop_audit_events", ["entity_id"])
    op.create_index("ix_shop_audit_events_request_id", "shop_audit_events", ["request_id"])


def downgrade() -> None:
    op.drop_index("ix_shop_audit_events_request_id", table_name="shop_audit_events")
    op.drop_index("ix_shop_audit_events_entity_id", table_name="shop_audit_events")
    op.drop_index("ix_shop_audit_events_entity_type", table_name="shop_audit_events")
    op.drop_index("ix_shop_audit_events_action", table_name="shop_audit_events")
    op.drop_index("ix_shop_audit_events_actor_id", table_name="shop_audit_events")
    op.drop_table("shop_audit_events")
    op.drop_index("ix_shop_agent_steps_run_id", table_name="shop_agent_steps")
    op.drop_table("shop_agent_steps")
    op.drop_index("ix_shop_agent_runs_status", table_name="shop_agent_runs")
    op.drop_index("ix_shop_agent_runs_user_id", table_name="shop_agent_runs")
    op.drop_index("ix_shop_agent_runs_request_id", table_name="shop_agent_runs")
    op.drop_index("ix_shop_agent_runs_trace_id", table_name="shop_agent_runs")
    op.drop_table("shop_agent_runs")
    op.drop_index(
        "ix_shop_action_proposals_agent_trace_id", table_name="shop_action_proposals"
    )
    op.drop_index("ix_shop_action_proposals_status", table_name="shop_action_proposals")
    op.drop_index("ix_shop_action_proposals_user_id", table_name="shop_action_proposals")
    op.drop_index("ix_shop_action_proposals_ticket_id", table_name="shop_action_proposals")
    op.drop_index("ix_shop_action_proposals_proposal_no", table_name="shop_action_proposals")
    op.drop_table("shop_action_proposals")

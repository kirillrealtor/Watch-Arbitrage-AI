"""Business process layer — alert_rules, alert_deliveries, feedbacks, trade_outcomes, subscriptions, audit_events, outbox_events, feature_flags.

Revision ID: de4e1b0ff4a3
Revises: 12e1f9e711d2
Create Date: 2026-08-03 17:10:30

ADR corrections:
  ADR-0002 D1: No composite UNIQUE on alert_deliveries — idempotency_key only
  ADR-0002 D2: organization_id on alert_deliveries
  ADR-0002 D3: material_version on alert_deliveries
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "de4e1b0ff4a3"
down_revision: Union[str, None] = "12e1f9e711d2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE delivery_status AS ENUM ('pending', 'sent', 'failed', 'suppressed')")
    op.execute("CREATE TYPE feedback_decision AS ENUM ('purchased', 'contacted', 'dismissed')")
    op.execute("CREATE TYPE subscription_status AS ENUM ('trialing', 'active', 'past_due', 'canceled', 'unpaid')")
    op.execute("CREATE TYPE outbox_event_status AS ENUM ('pending', 'published', 'failed')")

    # 18. alert_rules
    op.create_table(
        "alert_rules",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=False),
        sa.Column("created_by", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("filters", postgresql.JSONB(), nullable=False),
        sa.Column("channels", postgresql.JSONB(), nullable=False),
        sa.Column("cooldown_minutes", sa.Integer(), server_default=sa.text("60"), nullable=False),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_alert_rules"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_alert_rules_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["created_by"], ["users.id"],
            name="fk_alert_rules_created_by",
        ),
    )

    # 19. alert_deliveries (ADR-0002: org_id, material_version, no composite UNIQUE)
    op.create_table(
        "alert_deliveries",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=False),
        sa.Column("rule_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("opportunity_id", sa.Text(), nullable=False),
        sa.Column("material_version", sa.Integer(), nullable=False),
        sa.Column("channel", sa.Text(), nullable=False),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column(
            "delivery_status",
            postgresql.ENUM("pending", "sent", "failed", "suppressed", name="delivery_status", create_type=False),
            nullable=False,
        ),
        sa.Column("provider_message_id", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_alert_deliveries"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_alert_deliveries_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["rule_id"], ["alert_rules.id"],
            name="fk_alert_deliveries_rule_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_alert_deliveries_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"],
            name="fk_alert_deliveries_opportunity_id",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_alert_deliveries_idempotency_key"),
    )

    # 20. feedbacks
    op.create_table(
        "feedbacks",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("opportunity_id", sa.Text(), nullable=False),
        sa.Column(
            "decision",
            postgresql.ENUM("purchased", "contacted", "dismissed", name="feedback_decision", create_type=False),
            nullable=False,
        ),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_feedbacks"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_feedbacks_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_feedbacks_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"],
            name="fk_feedbacks_opportunity_id",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_feedbacks_idempotency_key"),
    )

    # 21. trade_outcomes
    op.create_table(
        "trade_outcomes",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("opportunity_id", sa.Text(), nullable=True),
        sa.Column("reference_id", sa.Text(), nullable=False),
        sa.Column("acquisition_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("acquisition_currency", sa.String(3), nullable=True),
        sa.Column("resale_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("resale_currency", sa.String(3), nullable=True),
        sa.Column("actual_profit", sa.Numeric(18, 2), nullable=True),
        sa.Column("days_to_sell", sa.Integer(), nullable=True),
        sa.Column("idempotency_key", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_trade_outcomes"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_trade_outcomes_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_trade_outcomes_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"],
            name="fk_trade_outcomes_opportunity_id",
        ),
        sa.ForeignKeyConstraint(
            ["reference_id"], ["references.id"],
            name="fk_trade_outcomes_reference_id",
        ),
        sa.UniqueConstraint("idempotency_key", name="uq_trade_outcomes_idempotency_key"),
    )

    # 22. subscriptions
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=False),
        sa.Column("stripe_customer_id", sa.Text(), nullable=True),
        sa.Column("stripe_subscription_id", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("trialing", "active", "past_due", "canceled", "unpaid", name="subscription_status", create_type=False),
            nullable=False,
        ),
        sa.Column("plan_id", sa.Text(), nullable=True),
        sa.Column("current_period_start", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("current_period_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("trial_end", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_subscriptions"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_subscriptions_organization_id",
        ),
    )

    # 23. audit_events
    op.create_table(
        "audit_events",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=True),
        sa.Column("user_id", sa.Text(), nullable=True),
        sa.Column("action", sa.Text(), nullable=False),
        sa.Column("resource_type", sa.Text(), nullable=False),
        sa.Column("resource_id", sa.Text(), nullable=False),
        sa.Column("details", postgresql.JSONB(), nullable=True),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column("client_ip", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_audit_events"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_audit_events_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_audit_events_user_id",
        ),
    )

    # 24. outbox_events
    op.create_table(
        "outbox_events",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("event_name", sa.Text(), nullable=False),
        sa.Column("event_version", sa.Text(), nullable=False),
        sa.Column("payload", postgresql.JSONB(), nullable=False),
        sa.Column("trace_id", sa.Text(), nullable=True),
        sa.Column(
            "status",
            postgresql.ENUM("pending", "published", "failed", name="outbox_event_status", create_type=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_outbox_events"),
    )

    # 25. feature_flags
    op.create_table(
        "feature_flags",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("key", sa.Text(), nullable=False),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("organization_ids", postgresql.JSONB(), nullable=True),
        sa.Column("rollout_pct", sa.Integer(), server_default=sa.text("0"), nullable=False),
        sa.Column("expires_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_feature_flags"),
        sa.UniqueConstraint("key", name="uq_feature_flags_key"),
    )


def downgrade() -> None:
    op.drop_table("feature_flags")
    op.drop_table("outbox_events")
    op.drop_table("audit_events")
    op.drop_table("subscriptions")
    op.drop_table("trade_outcomes")
    op.drop_table("feedbacks")
    op.drop_table("alert_deliveries")
    op.drop_table("alert_rules")

    op.execute("DROP TYPE outbox_event_status")
    op.execute("DROP TYPE subscription_status")
    op.execute("DROP TYPE feedback_decision")
    op.execute("DROP TYPE delivery_status")

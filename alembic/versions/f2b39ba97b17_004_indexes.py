"""Performance indexes — 12 application indexes across all tables established by migrations 001-003.

Revision ID: f2b39ba97b17
Revises: de4e1b0ff4a3
Create Date: 2026-08-03 17:31:51

Excluded (redundant with UNIQUE constraints):
  idx_alert_deliveries_idem  → uq_alert_deliveries_idempotency_key
  idx_feedbacks_idem         → uq_feedbacks_idempotency_key
  idx_trade_outcomes_idem    → uq_trade_outcomes_idempotency_key
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

revision: str = "f2b39ba97b17"
down_revision: Union[str, None] = "de4e1b0ff4a3"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_index("idx_memberships_org_user", "memberships", ["organization_id", "user_id"])
    op.create_index(
        "idx_opportunities_org_state",
        "opportunities",
        ["organization_id", "state", sa.text("published_at DESC")],
    )
    op.create_index("idx_alert_rules_org", "alert_rules", ["organization_id", "is_enabled"])
    op.create_index("idx_feedbacks_org_opp", "feedbacks", ["organization_id", "opportunity_id"])
    op.create_index(
        "idx_opportunities_published",
        "opportunities",
        ["state", sa.text("published_at DESC")],
        postgresql_where=sa.text("state = 'published'"),
    )
    op.create_index(
        "idx_normalized_listings_ref",
        "normalized_listings",
        ["reference_id", "status", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_normalized_listings_active",
        "normalized_listings",
        ["status", "reference_id"],
        postgresql_where=sa.text("status = 'active'"),
    )
    op.create_index(
        "idx_alert_deliveries_org_user",
        "alert_deliveries",
        ["organization_id", "user_id", sa.text("created_at DESC")],
    )
    op.create_index(
        "idx_alert_deliveries_opp",
        "alert_deliveries",
        ["opportunity_id", "material_version"],
    )
    op.create_index(
        "idx_outbox_pending",
        "outbox_events",
        ["status", "created_at"],
        postgresql_where=sa.text("status = 'pending'"),
    )
    op.create_index(
        "idx_audit_org_time",
        "audit_events",
        ["organization_id", sa.text("created_at DESC")],
    )
    op.create_index("idx_audit_resource", "audit_events", ["resource_type", "resource_id"])


def downgrade() -> None:
    op.drop_index("idx_audit_resource", table_name="audit_events")
    op.drop_index("idx_audit_org_time", table_name="audit_events")
    op.drop_index("idx_outbox_pending", table_name="outbox_events")
    op.drop_index("idx_alert_deliveries_opp", table_name="alert_deliveries")
    op.drop_index("idx_alert_deliveries_org_user", table_name="alert_deliveries")
    op.drop_index("idx_normalized_listings_active", table_name="normalized_listings")
    op.drop_index("idx_normalized_listings_ref", table_name="normalized_listings")
    op.drop_index("idx_opportunities_published", table_name="opportunities")
    op.drop_index("idx_feedbacks_org_opp", table_name="feedbacks")
    op.drop_index("idx_alert_rules_org", table_name="alert_rules")
    op.drop_index("idx_opportunities_org_state", table_name="opportunities")
    op.drop_index("idx_memberships_org_user", table_name="memberships")

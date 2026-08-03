"""Pipeline data layer — raw_snapshots, parsed_listings, normalized_listings, duplicate_groups, duplicate_group_members, valuations, opportunities, opportunity_views.

Revision ID: 12e1f9e711d2
Revises: a40b5bfef9a2
Create Date: 2026-08-03 16:35:04

ADR corrections:
  ADR-0004: observation_at TIMESTAMPTZ NOT NULL on normalized_listings
  ADR-0005: fx_source TEXT NOT NULL, fx_date DATE NOT NULL on normalized_listings
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "12e1f9e711d2"
down_revision: Union[str, None] = "a40b5bfef9a2"
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE listing_status AS ENUM ('active', 'quarantined', 'suppressed', 'stale')")
    op.execute("CREATE TYPE opportunity_state AS ENUM ('published', 'dismissed', 'contacted', 'purchased', 'expired')")

    # 10. raw_snapshots
    op.create_table(
        "raw_snapshots",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("source_id", sa.Text(), nullable=False),
        sa.Column("external_id", sa.Text(), nullable=False),
        sa.Column("adapter_version", sa.Text(), nullable=False),
        sa.Column("checksum", sa.Text(), nullable=False),
        sa.Column("raw_payload", postgresql.JSONB(), nullable=True),
        sa.Column("fetched_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_raw_snapshots"),
        sa.ForeignKeyConstraint(
            ["source_id"], ["sources.id"],
            name="fk_raw_snapshots_source_id",
        ),
        sa.UniqueConstraint(
            "source_id", "external_id", "adapter_version", "checksum",
            name="uq_raw_snapshots",
        ),
    )

    # 11. parsed_listings
    op.create_table(
        "parsed_listings",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("snapshot_id", sa.Text(), nullable=False),
        sa.Column("parser_version", sa.Text(), nullable=False),
        sa.Column("listing_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("price_currency", sa.String(3), nullable=True),
        sa.Column("listing_title", sa.Text(), nullable=True),
        sa.Column("description", sa.Text(), nullable=True),
        sa.Column("parsed_attributes", postgresql.JSONB(), nullable=True),
        sa.Column("external_url", sa.Text(), nullable=True),
        sa.Column("listed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_parsed_listings"),
        sa.ForeignKeyConstraint(
            ["snapshot_id"], ["raw_snapshots.id"],
            name="fk_parsed_listings_snapshot_id",
        ),
        sa.UniqueConstraint("snapshot_id", name="uq_parsed_listings_snapshot_id"),
    )

    # 12. normalized_listings
    op.create_table(
        "normalized_listings",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("parsed_listing_id", sa.Text(), nullable=False),
        sa.Column("reference_id", sa.Text(), nullable=False),
        sa.Column("normalization_version", sa.Text(), nullable=False),
        sa.Column("match_confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("match_method", sa.Text(), nullable=True),
        sa.Column("match_features", postgresql.JSONB(), nullable=True),
        sa.Column("condition", sa.Text(), nullable=True),
        sa.Column("set_status", sa.Text(), nullable=True),
        sa.Column("seller_geography", sa.Text(), nullable=True),
        sa.Column("normalized_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("normalized_currency", sa.String(3), nullable=True),
        sa.Column("fx_rate", sa.Numeric(18, 8), nullable=False),
        sa.Column("fx_source", sa.Text(), nullable=False),
        sa.Column("fx_date", sa.Date(), nullable=False),
        sa.Column("observation_at", sa.TIMESTAMP(timezone=True), nullable=False),
        sa.Column(
            "status",
            postgresql.ENUM("active", "quarantined", "suppressed", "stale", name="listing_status", create_type=False),
            nullable=False,
        ),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_normalized_listings"),
        sa.ForeignKeyConstraint(
            ["parsed_listing_id"], ["parsed_listings.id"],
            name="fk_normalized_listings_parsed_listing_id",
        ),
        sa.ForeignKeyConstraint(
            ["reference_id"], ["references.id"],
            name="fk_normalized_listings_reference_id",
        ),
        sa.UniqueConstraint("parsed_listing_id", name="uq_normalized_listings_parsed_listing_id"),
    )

    # 13. duplicate_groups
    op.create_table(
        "duplicate_groups",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("representative_id", sa.Text(), nullable=False),
        sa.Column("method", sa.Text(), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_duplicate_groups"),
        sa.ForeignKeyConstraint(
            ["representative_id"], ["normalized_listings.id"],
            name="fk_duplicate_groups_representative_id",
        ),
    )

    # 14. duplicate_group_members
    op.create_table(
        "duplicate_group_members",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("group_id", sa.Text(), nullable=False),
        sa.Column("listing_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_duplicate_group_members"),
        sa.ForeignKeyConstraint(
            ["group_id"], ["duplicate_groups.id"],
            name="fk_duplicate_group_members_group_id",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"], ["normalized_listings.id"],
            name="fk_duplicate_group_members_listing_id",
        ),
        sa.UniqueConstraint("group_id", "listing_id", name="uq_duplicate_group_members"),
    )

    # 15. valuations
    op.create_table(
        "valuations",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("listing_id", sa.Text(), nullable=False),
        sa.Column("model_version", sa.Text(), nullable=False),
        sa.Column("config_version", sa.Text(), nullable=False),
        sa.Column("cost_assumptions_version", sa.Text(), nullable=False),
        sa.Column("expected_exit_price", sa.Numeric(18, 2), nullable=True),
        sa.Column("exit_price_currency", sa.String(3), nullable=True),
        sa.Column("all_in_acquisition", sa.Numeric(18, 2), nullable=True),
        sa.Column("expected_net_resale", sa.Numeric(18, 2), nullable=True),
        sa.Column("expected_net_profit", sa.Numeric(18, 2), nullable=True),
        sa.Column("roi", sa.Numeric(10, 6), nullable=True),
        sa.Column("low_estimate", sa.Numeric(18, 2), nullable=True),
        sa.Column("high_estimate", sa.Numeric(18, 2), nullable=True),
        sa.Column("confidence", sa.Numeric(5, 4), nullable=True),
        sa.Column("comparable_count", sa.Integer(), nullable=True),
        sa.Column("sample_dispersion", sa.Numeric(10, 4), nullable=True),
        sa.Column("adjustment_details", postgresql.JSONB(), nullable=True),
        sa.Column("risk_reserve_details", postgresql.JSONB(), nullable=True),
        sa.Column("cost_breakdown", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_valuations"),
        sa.ForeignKeyConstraint(
            ["listing_id"], ["normalized_listings.id"],
            name="fk_valuations_listing_id",
        ),
    )

    # 16. opportunities
    op.create_table(
        "opportunities",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=False),
        sa.Column("listing_id", sa.Text(), nullable=False),
        sa.Column("valuation_id", sa.Text(), nullable=False),
        sa.Column("material_version", sa.Integer(), nullable=False),
        sa.Column("score", sa.Numeric(10, 4), nullable=True),
        sa.Column(
            "state",
            postgresql.ENUM("published", "dismissed", "contacted", "purchased", "expired", name="opportunity_state", create_type=False),
            nullable=False,
        ),
        sa.Column("positive_factors", postgresql.JSONB(), nullable=True),
        sa.Column("negative_factors", postgresql.JSONB(), nullable=True),
        sa.Column("published_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("state_changed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_opportunities"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_opportunities_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["listing_id"], ["normalized_listings.id"],
            name="fk_opportunities_listing_id",
        ),
        sa.ForeignKeyConstraint(
            ["valuation_id"], ["valuations.id"],
            name="fk_opportunities_valuation_id",
        ),
        sa.UniqueConstraint(
            "organization_id", "listing_id", "material_version",
            name="uq_opportunities_org_listing_version",
        ),
    )

    # 17. opportunity_views
    op.create_table(
        "opportunity_views",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("opportunity_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column("viewed_at", sa.TIMESTAMP(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_opportunity_views"),
        sa.ForeignKeyConstraint(
            ["opportunity_id"], ["opportunities.id"],
            name="fk_opportunity_views_opportunity_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_opportunity_views_user_id",
        ),
        sa.UniqueConstraint("opportunity_id", "user_id", name="uq_opportunity_views"),
    )


def downgrade() -> None:
    op.drop_table("opportunity_views")
    op.drop_table("opportunities")
    op.drop_table("valuations")
    op.drop_table("duplicate_group_members")
    op.drop_table("duplicate_groups")
    op.drop_table("normalized_listings")
    op.drop_table("parsed_listings")
    op.drop_table("raw_snapshots")

    op.execute("DROP TYPE opportunity_state")
    op.execute("DROP TYPE listing_status")

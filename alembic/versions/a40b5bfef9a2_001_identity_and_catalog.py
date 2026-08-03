"""Identity and catalog foundation — organizations, users, memberships, brands, references, aliases, watch_lists, watch_list_entries, sources.

Revision ID: a40b5bfef9a2
Revises: (none)
Create Date: 2026-08-03 16:03:02.823574
"""

from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import postgresql

revision: str = "a40b5bfef9a2"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.execute("CREATE TYPE membership_role AS ENUM ('owner', 'admin', 'dealer', 'viewer')")

    # 1. organizations (no FKs)
    op.create_table(
        "organizations",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("settings", postgresql.JSONB(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_organizations"),
        sa.UniqueConstraint("slug", name="uq_organizations_slug"),
    )

    # 2. users (no FKs)
    op.create_table(
        "users",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("cognito_sub", sa.Text(), nullable=False),
        sa.Column("email", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.Column("updated_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_users"),
        sa.UniqueConstraint("cognito_sub", name="uq_users_cognito_sub"),
        sa.UniqueConstraint("email", name="uq_users_email"),
    )

    # 3. brands (no FKs)
    op.create_table(
        "brands",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("slug", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_brands"),
        sa.UniqueConstraint("name", name="uq_brands_name"),
        sa.UniqueConstraint("slug", name="uq_brands_slug"),
    )

    # 4. sources (no FKs)
    op.create_table(
        "sources",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("source_key", sa.Text(), nullable=False),
        sa.Column("display_name", sa.Text(), nullable=False),
        sa.Column("adapter_version", sa.Text(), nullable=False),
        sa.Column("access_mode", sa.Text(), nullable=False),
        sa.Column("rate_policy", postgresql.JSONB(), nullable=True),
        sa.Column("approval_ref", sa.Text(), nullable=True),
        sa.Column("is_enabled", sa.Boolean(), server_default=sa.text("false"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_sources"),
        sa.UniqueConstraint("source_key", name="uq_sources_source_key"),
    )

    # 5. watch_lists (FK → organizations)
    op.create_table(
        "watch_lists",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=False),
        sa.Column("name", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_watch_lists"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_watch_lists_organization_id",
        ),
    )

    # 6. references (FK → brands)
    op.create_table(
        "references",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("brand_id", sa.Text(), nullable=False),
        sa.Column("ref_code", sa.Text(), nullable=False),
        sa.Column("model_name", sa.Text(), nullable=True),
        sa.Column("generation", sa.Text(), nullable=True),
        sa.Column("attributes", postgresql.JSONB(), nullable=True),
        sa.Column("is_active", sa.Boolean(), server_default=sa.text("true"), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_references"),
        sa.ForeignKeyConstraint(
            ["brand_id"], ["brands.id"],
            name="fk_references_brand_id",
        ),
        sa.UniqueConstraint("brand_id", "ref_code", name="uq_references_brand_ref"),
    )

    # 7. memberships (FK → organizations, users, users)
    op.create_table(
        "memberships",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("organization_id", sa.Text(), nullable=False),
        sa.Column("user_id", sa.Text(), nullable=False),
        sa.Column(
            "role",
            postgresql.ENUM("owner", "admin", "dealer", "viewer", name="membership_role", create_type=False),
            nullable=False,
        ),
        sa.Column("invited_by", sa.Text(), nullable=True),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_memberships"),
        sa.ForeignKeyConstraint(
            ["organization_id"], ["organizations.id"],
            name="fk_memberships_organization_id",
        ),
        sa.ForeignKeyConstraint(
            ["user_id"], ["users.id"],
            name="fk_memberships_user_id",
        ),
        sa.ForeignKeyConstraint(
            ["invited_by"], ["users.id"],
            name="fk_memberships_invited_by",
        ),
        sa.UniqueConstraint("user_id", "organization_id", name="uq_memberships_user_org"),
    )

    # 8. aliases (FK → references)
    op.create_table(
        "aliases",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("reference_id", sa.Text(), nullable=False),
        sa.Column("alias_text", sa.Text(), nullable=False),
        sa.Column("source", sa.Text(), nullable=True),
        sa.PrimaryKeyConstraint("id", name="pk_aliases"),
        sa.ForeignKeyConstraint(
            ["reference_id"], ["references.id"],
            name="fk_aliases_reference_id",
        ),
        sa.UniqueConstraint("alias_text", "source", name="uq_aliases_text_source"),
    )

    # 9. watch_list_entries (FK → watch_lists, references)
    op.create_table(
        "watch_list_entries",
        sa.Column("id", sa.Text(), nullable=False),
        sa.Column("watch_list_id", sa.Text(), nullable=False),
        sa.Column("reference_id", sa.Text(), nullable=False),
        sa.Column("created_at", sa.TIMESTAMP(timezone=True), server_default=sa.func.now(), nullable=False),
        sa.PrimaryKeyConstraint("id", name="pk_watch_list_entries"),
        sa.ForeignKeyConstraint(
            ["watch_list_id"], ["watch_lists.id"],
            name="fk_watch_list_entries_watch_list_id",
        ),
        sa.ForeignKeyConstraint(
            ["reference_id"], ["references.id"],
            name="fk_watch_list_entries_reference_id",
        ),
        sa.UniqueConstraint("watch_list_id", "reference_id", name="uq_watch_list_entries_list_ref"),
    )


def downgrade() -> None:
    op.drop_table("watch_list_entries")
    op.drop_table("aliases")
    op.drop_table("memberships")
    op.drop_table("references")
    op.drop_table("watch_lists")
    op.drop_table("sources")
    op.drop_table("brands")
    op.drop_table("users")
    op.drop_table("organizations")

    op.execute("DROP TYPE membership_role")

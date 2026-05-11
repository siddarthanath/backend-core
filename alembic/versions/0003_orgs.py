"""Create organisations and memberships tables.

Revision ID: 0003
Revises: 0002
Create Date: 2026-05-11

"""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
import sqlalchemy as sa
from alembic import op

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

revision: str = "0003"
down_revision: str | None = "0002"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create organisations and memberships tables."""
    op.create_table(
        "organisations",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("name", sa.String(length=200), nullable=False),
        sa.Column("slug", sa.String(length=100), nullable=False),
        sa.Column("is_personal", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("slug"),
        sa.UniqueConstraint("stripe_customer_id"),
    )
    op.create_index("ix_organisations_slug", "organisations", ["slug"])
    op.create_index("ix_organisations_stripe_customer_id", "organisations", ["stripe_customer_id"])

    op.create_table(
        "memberships",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("user_id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("role", sa.String(), nullable=False, server_default="member"),
        sa.Column("status", sa.String(), nullable=False, server_default="invited"),
        sa.Column("invited_by", sa.Uuid(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["user_id"], ["user_profiles.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["org_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.ForeignKeyConstraint(["invited_by"], ["user_profiles.id"], ondelete="SET NULL"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("user_id", "org_id", name="uq_membership_user_org"),
    )
    op.create_index("ix_memberships_user_id", "memberships", ["user_id"])
    op.create_index("ix_memberships_org_id", "memberships", ["org_id"])


def downgrade() -> None:
    """Drop memberships and organisations tables."""
    op.drop_index("ix_memberships_org_id", table_name="memberships")
    op.drop_index("ix_memberships_user_id", table_name="memberships")
    op.drop_table("memberships")
    op.drop_index("ix_organisations_stripe_customer_id", table_name="organisations")
    op.drop_index("ix_organisations_slug", table_name="organisations")
    op.drop_table("organisations")

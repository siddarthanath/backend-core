"""Create subscriptions table.

Revision ID: 0004
Revises: 0003
Create Date: 2026-05-11

"""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
import sqlalchemy as sa
from alembic import op

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

revision: str = "0004"
down_revision: str | None = "0003"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create subscriptions table."""
    op.create_table(
        "subscriptions",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("org_id", sa.Uuid(), nullable=False),
        sa.Column("plan", sa.String(), nullable=False, server_default="free"),
        sa.Column("status", sa.String(), nullable=False, server_default="active"),
        sa.Column("stripe_subscription_id", sa.String(), nullable=True),
        sa.Column("stripe_price_id", sa.String(), nullable=True),
        sa.Column("current_period_end", sa.DateTime(timezone=True), nullable=True),
        sa.Column("cancel_at_period_end", sa.Boolean(), nullable=False, server_default="false"),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.ForeignKeyConstraint(["org_id"], ["organisations.id"], ondelete="CASCADE"),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("org_id"),
        sa.UniqueConstraint("stripe_subscription_id"),
    )
    op.create_index("ix_subscriptions_org_id", "subscriptions", ["org_id"])
    op.create_index(
        "ix_subscriptions_stripe_subscription_id",
        "subscriptions",
        ["stripe_subscription_id"],
    )


def downgrade() -> None:
    """Drop subscriptions table."""
    op.drop_index("ix_subscriptions_stripe_subscription_id", table_name="subscriptions")
    op.drop_index("ix_subscriptions_org_id", table_name="subscriptions")
    op.drop_table("subscriptions")

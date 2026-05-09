"""Create user_profiles table.

Revision ID: 0002
Revises: 0001
Create Date: 2026-05-09

"""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
import sqlalchemy as sa
from alembic import op

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

revision: str = "0002"
down_revision: str | None = "0001"
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    """Create user_profiles table mirroring Supabase auth.users."""
    op.create_table(
        "user_profiles",
        sa.Column("id", sa.Uuid(), nullable=False),
        sa.Column("email", sa.String(length=320), nullable=False),
        sa.Column("first_name", sa.String(length=100), nullable=True),
        sa.Column("last_name", sa.String(length=100), nullable=True),
        sa.Column("stripe_customer_id", sa.String(), nullable=True),
        sa.Column("created_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.Column("deleted_at", sa.DateTime(timezone=True), nullable=True),
        sa.PrimaryKeyConstraint("id"),
        sa.UniqueConstraint("email"),
        sa.UniqueConstraint("stripe_customer_id"),
    )
    op.create_index("ix_user_profiles_email", "user_profiles", ["email"])
    op.create_index("ix_user_profiles_stripe_customer_id", "user_profiles", ["stripe_customer_id"])


def downgrade() -> None:
    """Drop user_profiles table."""
    op.drop_index("ix_user_profiles_stripe_customer_id", table_name="user_profiles")
    op.drop_index("ix_user_profiles_email", table_name="user_profiles")
    op.drop_table("user_profiles")

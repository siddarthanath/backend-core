"""0002_fk_cascade_deletes

Revision ID: 0002
Revises: 3f0588b39450
Create Date: 2026-05-12 00:00:00.000000

"""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from alembic import op

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

revision: str = '3f0588b39450'
down_revision: str | None = '2f0588b39450'
branch_labels: str | None = None
depends_on: str | None = None


def upgrade() -> None:
    # Drop existing FKs without CASCADE, re-add with ON DELETE CASCADE.
    #
    # memberships.user_id  -> user_profiles.id  CASCADE  (membership gone when user deleted)
    # memberships.org_id   -> organisations.id  CASCADE  (membership gone when org deleted)
    # subscriptions.org_id -> organisations.id  CASCADE  (subscription gone when org deleted)
    #
    # memberships.invited_by is intentionally left without CASCADE — deleting the inviter
    # should not cascade-delete the invited member's membership.

    op.drop_constraint('memberships_user_id_fkey', 'memberships', type_='foreignkey')
    op.create_foreign_key(
        'memberships_user_id_fkey', 'memberships',
        'user_profiles', ['user_id'], ['id'],
        ondelete='CASCADE',
    )

    op.drop_constraint('memberships_org_id_fkey', 'memberships', type_='foreignkey')
    op.create_foreign_key(
        'memberships_org_id_fkey', 'memberships',
        'organisations', ['org_id'], ['id'],
        ondelete='CASCADE',
    )

    op.drop_constraint('subscriptions_org_id_fkey', 'subscriptions', type_='foreignkey')
    op.create_foreign_key(
        'subscriptions_org_id_fkey', 'subscriptions',
        'organisations', ['org_id'], ['id'],
        ondelete='CASCADE',
    )


def downgrade() -> None:
    op.drop_constraint('subscriptions_org_id_fkey', 'subscriptions', type_='foreignkey')
    op.create_foreign_key(
        'subscriptions_org_id_fkey', 'subscriptions',
        'organisations', ['org_id'], ['id'],
    )

    op.drop_constraint('memberships_org_id_fkey', 'memberships', type_='foreignkey')
    op.create_foreign_key(
        'memberships_org_id_fkey', 'memberships',
        'organisations', ['org_id'], ['id'],
    )

    op.drop_constraint('memberships_user_id_fkey', 'memberships', type_='foreignkey')
    op.create_foreign_key(
        'memberships_user_id_fkey', 'memberships',
        'user_profiles', ['user_id'], ['id'],
    )

"""Hard-delete soft-deleted user profiles older than a grace period (GDPR/data retention).

UserService.delete only SOFT-deletes a profile (sets deleted_at) so that a failed
Supabase auth-delete can be retried safely. That leaves the user's email and name in
the database indefinitely. This script permanently removes rows whose deleted_at is
older than the grace period, freeing the PII (and the email's unique-index slot).

Run it on a schedule — cron, a Supabase scheduled function, or a CI cron job:

    python -m scripts.purge_deleted_users               # default 30-day grace
    python -m scripts.purge_deleted_users --days 7
    python -m scripts.purge_deleted_users --dry-run     # report only, no delete

Org/membership/subscription rows cascade at the DB level when the profile is removed.
See docs/DEPLOYMENT.md.
"""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import argparse
import asyncio
from datetime import datetime, timedelta, timezone

# Third-Party Library
from sqlalchemy import delete, func, select

# Private Library
from src.models.user import UserProfile
from src.services.sessions.database import DatabaseSession

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


async def purge(days: int, dry_run: bool) -> int:
    """Delete (or count) profiles soft-deleted more than `days` ago.

    Args:
        days (int): Grace period — rows soft-deleted before now-days are purged.
        dry_run (bool): If True, only count; make no changes.

    Returns:
        int: Number of rows purged (or that would be purged in dry-run).

    """
    cutoff = datetime.now(timezone.utc) - timedelta(days=days)
    db = DatabaseSession()
    db.initialise()
    session = db.get_session()
    try:
        condition = UserProfile.deleted_at.is_not(None) & (
            UserProfile.deleted_at < cutoff
        )
        count = await session.scalar(
            select(func.count()).select_from(UserProfile).where(condition)
        )
        count = count or 0
        if not dry_run and count:
            await session.execute(delete(UserProfile).where(condition))
            await session.commit()
        return count
    finally:
        await session.close()
        await db.close()


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--days", type=int, default=30, help="Grace period in days (default: 30)"
    )
    parser.add_argument(
        "--dry-run", action="store_true", help="Report only, make no changes"
    )
    args = parser.parse_args()

    count = asyncio.run(purge(args.days, args.dry_run))
    verb = "Would purge" if args.dry_run else "Purged"
    print(f"{verb} {count} profile(s) soft-deleted more than {args.days} day(s) ago.")


if __name__ == "__main__":
    main()

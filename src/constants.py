"""Domain constants — StrEnum definitions for all domain-level categorical values."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
from enum import StrEnum

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class Role(StrEnum):
    OWNER = "owner"
    ADMIN = "admin"
    MEMBER = "member"


class MembershipStatus(StrEnum):
    ACTIVE = "active"
    INVITED = "invited"
    SUSPENDED = "suspended"


class Plan(StrEnum):
    FREE = "free"
    PRO = "pro"
    MAX = "max"
    ENTERPRISE = "enterprise"


class BillingPeriod(StrEnum):
    MONTHLY = "monthly"
    YEARLY = "yearly"


class SubscriptionStatus(StrEnum):
    ACTIVE = "active"
    TRIALING = "trialing"
    PAST_DUE = "past_due"
    CANCELED = "canceled"
    INCOMPLETE = "incomplete"


class JobStatus(StrEnum):
    PENDING = "pending"
    RUNNING = "running"
    COMPLETED = "completed"
    FAILED = "failed"
    CANCELED = "canceled"


class MediaType(StrEnum):
    IMAGE = "image"
    VIDEO = "video"
    AUDIO = "audio"
    DOCUMENT = "document"
    OTHER = "other"

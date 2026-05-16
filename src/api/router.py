"""API router — mounts all v1 routers under /api/v1."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third Party
from fastapi import APIRouter

# Internal
from src.api.v1 import api_keys, audit, billing, flags, health, org, user

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

router = APIRouter(prefix="/api/v1")

router.include_router(health.router)
router.include_router(user.router)
router.include_router(org.router)
router.include_router(billing.router)
router.include_router(audit.router)
router.include_router(flags.router)
router.include_router(api_keys.router)

# NOTE: Dynamic router auto-discovery (alternative pattern).
# Instead of explicit includes above, routers can be discovered at startup via pkgutil.iter_modules
# over the src/api/v1/ package, importing any module that exposes a `router` attribute.
# Tradeoff: zero-touch registration (drop a file, it's live) vs silent failures (a broken module
# is skipped rather than crashing startup). Adopt in the product layer once router count is 15+,
# but always raise on import errors — never swallow them with logger.error().

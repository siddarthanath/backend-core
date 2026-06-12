# Architecture — backend-core

---

## Layer Rules

Every file has exactly one job. A handler never touches the database. A repository never contains business logic. Violating this makes the codebase hard to test and hard to change.

| Layer | Location | Rule |
|---|---|---|
| DB models | `src/models/` | SQLModel `table=True` only. Never returned from handlers. |
| API schemas | `src/schemas/` | Pydantic `BaseModel` only. One file per domain. |
| Settings | `src/configs/settings/` | Pydantic `BaseSettings`. All config from env vars. |
| Handlers | `src/api/v1/` | Validate → call service → return schema. No business logic. |
| Services | `src/services/` | Business logic. Takes Pydantic in, returns Pydantic out. |
| Repositories | `src/repositories/` | DB queries only. Returns SQLModel instances. |

**Data flow (enforced):**
```
HTTP Request
  → Pydantic schema (FastAPI validates automatically)
  → Handler (thin)
  → Service (business logic)
  → Repository (DB query)
  → SQLModel instance
  → Service converts via XResponse.model_validate()
  → Pydantic response schema
  → HTTP Response
```

Every endpoint must declare `response_model=XResponse`. No `Any`, no raw `dict`.

---

## Registry Pattern

Long-lived objects — the database session factory, future LLM clients — are created once at startup and stored in a typed registry. Handlers never instantiate these themselves.

```python
# src/core/registry.py
db_registry: DbRegistry = {}

def register_db(session_factory: async_sessionmaker) -> None:
    db_registry["session_factory"] = session_factory

def get_session_factory() -> async_sessionmaker:
    return db_registry["session_factory"]
```

Registered once in `lifespan()` in `factory.py`. Resolved in `src/core/dependencies/database.py` to yield a session per request. Adding a new long-lived client (e.g. Redis, LLM) follows the same pattern — register in `lifespan`, add a typed registry dict, resolve in `dependencies/`.

---

## Dependency Injection

FastAPI's `Depends()` system wires services into handlers. Typed aliases in `src/core/dependencies/__init__.py` keep handler signatures clean:

```python
# Aliases — what handlers actually declare
CurrentUserID   = Annotated[uuid.UUID, Depends(get_current_user_id)]
CurrentUserClaims = Annotated[UserClaims, Depends(get_current_user)]
UserSvc         = Annotated[UserService, Depends(get_user_service)]
OrgSvc          = Annotated[OrgService, Depends(get_org_service)]
```

A handler declares what it needs, FastAPI resolves the chain:

```python
@router.get("/me", response_model=UserMeResponse)
async def get_me(claims: CurrentUserClaims, service: UserSvc) -> UserMeResponse:
    ...
```

Services receive repositories via their `__init__`. Repositories receive the `AsyncSession` from `get_db()`. Nothing is instantiated inside a handler.

---

## Exception Hierarchy

All application exceptions inherit from `CoreException`. Exception handlers in `src/core/exceptions/handlers.py` map them to HTTP responses with a consistent `ErrorEnvelope`:

```
CoreException
  AuthException          → 401
  ForbiddenError         → 403
  NotFoundError          → 404
  ConflictError          → 409
  AppValidationError     → 422
  AccountDeletedError    → 403 (ACCOUNT_DELETED code — frontend redirects to login)
  RateLimitError         → 429
```

Services raise typed exceptions. Handlers never catch them — the handlers registered in `factory.py` do. This means handler code has no `try/except` for business errors.

---

## Savepoint Pattern (Idempotency)

`begin_nested()` creates a PostgreSQL savepoint. An `IntegrityError` inside it rolls back only to the savepoint, leaving the outer transaction intact.

Used in two places:

**`SubscriptionRepository.upsert_free()`** — concurrent first-logins for the same org both attempt to insert a FREE subscription. One wins, one hits the unique constraint. The savepoint ensures the loser can fall back to `get_by_org()` and return the winner's row without poisoning the outer transaction.

**`StripeWebhookEventRepository.record()`** — two Stripe retries arriving simultaneously both pass the `exists()` check and both attempt to insert the idempotency row. The savepoint ensures only one succeeds; the other swallows the `IntegrityError` and returns — the subscription update in the outer transaction commits normally. Without the savepoint, the `IntegrityError` would roll back the subscription update and return 500, causing Stripe to retry indefinitely.

---

## Rate Limiting

`slowapi` applies a default limit (from `RATE_LIMIT_DEFAULT` in settings) to all routes. Per-route overrides use `@limiter.limit("N/minute")`.

The key function in `src/core/middleware/rate_limit.py` keys authenticated requests by `user_id` from the JWT (decoded without signature verification — verification happens in `get_current_user`, not here), and falls back to IP for unauthenticated endpoints. This prevents IP rotation bypassing rate limits on authenticated routes.

---

## Middleware Stack

Registered in order in `factory.py`. Executes inside-out (last registered = outermost):

```
CORS
  → slowapi (rate limit)
    → BodySizeLimit
      → RequestLogging (binds request_id to structlog context)
        → APILogging (logs method/path/status/duration)
          → Timeout (asyncio.wait_for, default 30s)
            → FastAPI routing
```

`request_id` is bound in `RequestLogging` and flows into all downstream structlog calls automatically via contextvars.

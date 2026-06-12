# Testing — backend-core

---

## Two-Tier Model

| Tier | Location | DB | Mocks | Purpose |
|---|---|---|---|---|
| Unit | `tests/unit/` | None | Repos, Stripe, email | Business logic in services |
| Integration | `tests/integration/` | Real (Supabase) | Stripe, email only | Repository queries, constraints, savepoints |

Unit tests run in CI with no credentials. Integration tests require `DATABASE_URL` in `.env`.

---

## Unit Tests

### Class-per-concept

Group tests by the operation being tested, not by file or method. One class = one service method or one logical scenario.

```python
class TestCreateCheckout:
    async def test_raises_forbidden_for_non_admin(self): ...
    async def test_raises_conflict_for_non_stripe_plan(self): ...
    async def test_raises_not_found_for_unknown_org(self): ...
    async def test_creates_checkout_session(self): ...

class TestHandleWebhook:
    async def test_skips_duplicate_event(self): ...
    async def test_activates_subscription_on_checkout_complete(self): ...
```

### Marks

```python
@pytest.mark.unit       # Always on unit tests
@pytest.mark.asyncio    # Always on async tests
```

### Factory Functions

Use `make_*` factory functions instead of constructing mocks inline. They centralise the default shape and let individual tests override only what they care about.

```python
def make_subscription(**kwargs):
    sub = MagicMock()
    sub.id = kwargs.get("id", uuid.uuid4())
    sub.plan = kwargs.get("plan", Plan.FREE)
    sub.status = kwargs.get("status", SubscriptionStatus.ACTIVE)
    sub.stripe_subscription_id = kwargs.get("stripe_subscription_id", None)
    return sub
```

Call with overrides only: `make_subscription(plan=Plan.PRO)`.

### Orchestrator/Service Setup

Use a `make_<service>()` helper that wires `AsyncMock` repos to the service under test. Return a tuple for easy destructuring.

```python
def make_orchestrator():
    subscription_repo = AsyncMock(spec=SubscriptionRepository)
    org_repo          = AsyncMock(spec=OrgRepository)
    membership_repo   = AsyncMock(spec=MembershipRepository)
    billing_svc       = AsyncMock(spec=BaseBillingService)
    webhook_repo      = AsyncMock(spec=StripeWebhookEventRepository)
    webhook_repo.exists.return_value = False  # safe default
    orchestrator = BillingOrchestrator(
        subscription_repo=subscription_repo,
        org_repo=org_repo,
        membership_repo=membership_repo,
        billing_svc=billing_svc,
        webhook_event_repo=webhook_repo,
    )
    return orchestrator, subscription_repo, org_repo, membership_repo, billing_svc, webhook_repo
```

In tests, unpack only what you need:

```python
orchestrator, subscription_repo, org_repo, membership_repo, _, _ = make_orchestrator()
```

### Mocking External Calls

Mock at the boundary — the service method that wraps Stripe/email, not deep inside it.

```python
billing_svc.create_checkout_session.return_value = MagicMock(url="https://checkout.stripe.com/xyz")
```

Use `patch` for module-level functions:

```python
with patch("src.services.billing.service._build_price_map", return_value={}):
    ...
```

### Example Unit Test

```python
class TestCreateCheckout:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_raises_forbidden_for_non_admin(self) -> None:
        orchestrator, _, org_repo, membership_repo, _, _ = make_orchestrator()
        org_repo.get_by_id.return_value = make_org()
        membership_repo.user_has_role.return_value = False

        with pytest.raises(ForbiddenError):
            await orchestrator.create_checkout(
                uuid.uuid4(), uuid.uuid4(),
                Plan.PRO, BillingPeriod.MONTHLY,
                "https://success.example.com",
                "https://cancel.example.com",
            )
```

---

## Integration Tests

### When to Write One

Write an integration test when the correctness of the code depends on database behaviour that a mock cannot replicate:

- Unique constraints (does `upsert_free` survive concurrent inserts?)
- Savepoints (does `record()` leave the outer transaction intact on duplicate?)
- Soft-delete filters (does `get_by_id` exclude deleted rows?)
- Cascade deletes (does deleting an org cascade to memberships?)

### conftest.py

`tests/conftest.py` provides:

```python
@pytest.fixture
async def db_session() -> AsyncGenerator[AsyncSession, None]:
    """Yields a real AsyncSession, rolls back after each test."""

@pytest.fixture
async def client(db_session) -> AsyncGenerator[AsyncClient, None]:
    """httpx AsyncClient wired to the FastAPI app with the test session."""
```

Each test gets a transaction that is rolled back on teardown — no data bleeds between tests and no manual cleanup is needed.

### Marks

```python
@pytest.mark.integration
@pytest.mark.asyncio
```

Run only integration tests: `pytest tests/integration/ -v`
Run only unit tests: `pytest tests/unit/ -v`

### Example Integration Test

```python
class TestUpsertFree:
    @pytest.mark.integration
    @pytest.mark.asyncio
    async def test_idempotent_on_concurrent_insert(self, db_session: AsyncSession) -> None:
        repo = SubscriptionRepository(db_session)
        org_id = uuid.uuid4()

        sub1 = await repo.upsert_free(org_id)
        sub2 = await repo.upsert_free(org_id)

        assert sub1.id == sub2.id
        assert sub1.plan == Plan.FREE
```

---

## Running Tests

```bash
# All tests
pytest tests/ -v

# Unit only (no DB needed)
pytest tests/unit/ -v

# Integration only (requires DATABASE_URL)
pytest tests/integration/ -v

# Specific class
pytest tests/unit/test_billing_service.py::TestCreateCheckout -v
```

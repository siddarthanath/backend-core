# Backend Testing Skill

## Core Rules

- **Real DB always** — tests hit the real Supabase PostgreSQL via `DATABASE_URL` from env. No DB mocks.
- **Mock only external services** — Stripe webhooks, Resend email, LLM APIs. Never mock SQLAlchemy or the registry.
- **Async tests** — all tests that touch the DB or the HTTP client use `@pytest.mark.asyncio`. `asyncio_mode = auto` is set in `pyproject.toml`.
- **Fixtures live in conftest.py** — shared fixtures only. Test-specific setup stays in the test file.

## Fixture Conventions

```python
# conftest.py — the only two fixtures every integration test needs
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    session = db_registry.get("default").get_session()
    async with session:
        yield session
```

The `client` fixture boots the full app (including lifespan), so `db_registry` is populated before any test runs.

## What to Test

| Layer | Test type | What to assert |
|---|---|---|
| Handlers | Integration (via `client`) | Status code, response shape, error envelopes |
| Services | Integration (via `db`) | State changes in DB, return values |
| Repositories | Integration (via `db`) | SQL correctness, correct ORM objects returned |
| Utils / pure logic | Unit | Input → output, edge cases |

## Test Structure

```python
@pytest.mark.asyncio
async def test_thing_does_x(client: AsyncClient) -> None:
    # Arrange
    payload = {"field": "value"}

    # Act
    response = await client.post("/api/v1/thing", json=payload)

    # Assert
    assert response.status_code == 201
    data = response.json()
    assert data["field"] == "value"
```

One assertion concept per test. Name tests `test_<thing>_<condition>_<expected>`.

## What NOT to Mock

- SQLAlchemy sessions
- The registry
- `DatabaseSession`
- Settings (use real env vars via `pytest-env` in `pyproject.toml`)

## conftest.py Rules

- **One `conftest.py` per directory** — `tests/conftest.py` for shared fixtures, `tests/integration/conftest.py` for integration-only fixtures, `tests/unit/conftest.py` for unit-only fixtures (rare).
- **Only shared fixtures go in conftest** — if a fixture is used by exactly one test file, define it in that file instead.
- **No business logic in fixtures** — fixtures set up state, not assert it.
- **Fixture scope**: use `scope="session"` for expensive once-per-run setup (e.g., a read-only seed). Use default `scope="function"` for anything that mutates DB state.

```python
# tests/conftest.py — the two root fixtures
@pytest_asyncio.fixture
async def client() -> AsyncGenerator[AsyncClient, None]:
    """Full ASGI app client. Boots lifespan (real DB). Use for handler tests."""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c

@pytest_asyncio.fixture
async def db() -> AsyncGenerator[AsyncSession, None]:
    """Direct DB session from the registry. Use for service/repository tests."""
    session = db_registry.get("default").get_session()
    async with session:
        yield session
```

## Unit vs Integration

| | Unit | Integration |
|---|---|---|
| Location | `tests/unit/` | `tests/integration/` |
| DB connection | No | Yes (real Supabase) |
| HTTP client | No | Yes (ASGI) |
| Speed | Fast | Slower (network) |
| What belongs here | Pure functions, utils, schema validation | Handlers, services, repositories |

**Unit test example** (no fixtures needed):
```python
def test_error_envelope_includes_code() -> None:
    env = ErrorEnvelope.from_exception(code="AUTH_ERROR", message="Unauthorized")
    assert env.error.code == "AUTH_ERROR"
```

**Integration test example**:
```python
@pytest.mark.asyncio
async def test_health_returns_ok(client: AsyncClient) -> None:
    response = await client.get("/api/v1/health")
    assert response.status_code == 200
    assert response.json()["status"] == "ok"
```

## Cleanup

If a test creates DB rows, clean them up in a fixture teardown (`yield` then delete). Never leave test data in the shared Supabase project. Prefer using a dedicated test schema or prefixed IDs to isolate test data.
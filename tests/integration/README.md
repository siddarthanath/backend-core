Integration tests that require a real database connection.

**These tests are NOT run in the default test suite.** They require a dedicated test database (separate Supabase project or local Postgres) pointed to by `TEST_DATABASE_URL`. They should never run against the production database.

Mock only external services (Stripe, Resend, Supabase admin SDK). DB and session are real. One file per domain (e.g., `test_user.py`, `test_org.py`).

Run with: `pytest tests/integration/ -m integration --env=test`

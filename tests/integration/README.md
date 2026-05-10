Integration tests that hit a real database — no mocks for DB or session.

Tests use the `async_client` and `db_session` fixtures from `conftest.py`. Mock only external services (Stripe, Resend, Supabase admin SDK). One file per domain (e.g., `test_user.py`, `test_org.py`).

# services/sessions/

Async SQLAlchemy engine and session factory management.

`DatabaseSession` is instantiated once in `factory.py` lifespan, registered as `db_registry.get("default")`, and resolved per-request via the `get_db` dependency. To swap databases, change `DATABASE_URL` in settings only — no code changes.
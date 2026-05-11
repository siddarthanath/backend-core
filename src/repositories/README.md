Database access layer — one file per domain (e.g., `user.py`, `org.py`).

Repositories return SQLModel instances only. No business logic, no Pydantic schemas, no HTTP concepts. Services own all decision-making; repositories own all SQL.

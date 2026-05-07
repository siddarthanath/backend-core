# alembic/

Database migration management via Alembic with async SQLAlchemy.

`versions/0001_baseline.py` — empty starting point that establishes Alembic history. All future schema changes: `alembic revision --autogenerate -m "description"` then review and `alembic upgrade head`. Never edit the DB schema directly.
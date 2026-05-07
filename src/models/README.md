# models/

SQLModel table definitions (`table=True`) only. No API schemas here.

`base.py` provides `UUIDMixin`, `TimestampMixin`, and `SoftDeleteMixin`. All table models must inherit from at least `UUIDMixin` and `TimestampMixin`. Never return SQLModel instances directly from handlers — convert to a Pydantic response schema in the service layer.
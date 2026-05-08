# schemas/

Pydantic `BaseModel` API contracts only — no SQLModel tables here.

One file per domain (e.g., `health.py`, `auth.py`, `project.py`). Each file contains request bodies (`CreateXRequest`, `UpdateXRequest`) and response shapes (`XResponse`). Response schemas must include `model_config = ConfigDict(from_attributes=True)` to allow `model_validate(orm_obj)`.
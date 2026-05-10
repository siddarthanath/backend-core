Pydantic request and response schemas for org and membership endpoints.

`requests.py` — validated input bodies. `responses.py` — serialised output shapes. Never import SQLModel table classes here; use `ConfigDict(from_attributes=True)` to map from ORM objects.

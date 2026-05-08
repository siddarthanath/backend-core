# api/

FastAPI routers. `router.py` mounts all versioned routers under `/api/v1`.

Handlers are thin: validate input schema → call service → return response schema. No business logic, no direct DB access, no `dict` or `Any` return types. Every endpoint declares `response_model=XResponse`.
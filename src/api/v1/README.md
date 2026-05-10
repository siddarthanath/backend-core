FastAPI route handlers for API version 1.

Handlers are thin: validate input schema → call service via `XSvc` dependency → return response schema. No business logic, no direct DB access, no `session: DBSession` in signatures. Every endpoint declares `response_model=XResponse`.

# core/exceptions/

Typed exception classes and FastAPI exception handlers that format all errors as `ErrorEnvelope`.

Raise `AuthException`, `NotFoundError`, `ValidationError`, or `RateLimitError` — never `HTTPException` directly. All map to `{ error: { code, message, detail, request_id } }`.
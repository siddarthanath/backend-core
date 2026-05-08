# core/middleware/

Request middleware: CORS, rate limiting, request ID injection and logging, and timeout enforcement.

Call `add_middleware(app)` once in `factory.py`. Middleware is applied outermost-first: CORS → SlowAPI → RequestLogging → Timeout → handler.
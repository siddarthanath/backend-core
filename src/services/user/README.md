Business logic for user profile lifecycle.

`UserService` is wired via `get_user_service()` in `core/dependencies/__init__.py` — never instantiated directly in handlers. Raises typed exceptions from `core/exceptions/types.py`; never `HTTPException`.

"""Middleware (logging) helpers for safe decoding, truncation, and redaction of sensitive request/response payloads."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import json

# Third Party Library

# Private Library

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

MAX_BODY_LOG_BYTES = 10_000
SENSITIVE_KEYS = {
    "password",
    "token",
    "access_token",
    "refresh_token",
    "authorization",
    "api_key",
    "secret",
    "client_secret",
    "cookie",
    "set-cookie",
}

def _truncate(value: str, limit: int = MAX_BODY_LOG_BYTES) -> str:
    """Truncate oversized payloads safely."""
    if len(value) <= limit:
        return value

    return f"{value[:limit]}... [TRUNCATED]"

def _redact(data: object) -> object:
    """Recursively redact sensitive fields."""
    if isinstance(data, dict):
        return {
            key: (
                "***REDACTED***"
                if key.lower() in SENSITIVE_KEYS
                else _redact(value)
            )
            for key, value in data.items()
        }

    if isinstance(data, list):
        return [_redact(item) for item in data]

    return data

def _decode_body(body: bytes) -> object:
    """Decode request/response body safely."""
    if not body:
        return None

    try:
        parsed = json.loads(body)
        return _redact(parsed)

    except (json.JSONDecodeError, UnicodeDecodeError):
        return _truncate(body.decode(errors="ignore"))
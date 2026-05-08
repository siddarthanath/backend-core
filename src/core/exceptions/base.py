"""Base exception — all application exceptions extend CoreException."""

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #


class CoreException(Exception):
    """Base class for all application exceptions.

    Args:
        code (str): Machine-readable error code.
        message (str): Human-readable summary.
        detail (str | None): Optional extra context.
        status_code (int): HTTP status code to return.

    """

    def __init__(
        self,
        code: str,
        message: str,
        detail: str | None = None,
        status_code: int = 500,
    ) -> None:
        self.code = code
        self.message = message
        self.detail = detail
        self.status_code = status_code
        super().__init__(message)
"""EmailService — sends transactional emails via the Resend API."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Standard Library
import json
import urllib.error
import urllib.request

# Third Party
import anyio

# Internal
from src.configs.settings import external_settings
from src.utils.logging import get_logger

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

log = get_logger(__name__)


class EmailService:
    """Thin wrapper around the Resend REST API.

    Sends fire-and-forget transactional emails. All methods are no-ops when
    RESEND_API_KEY is empty so the app starts cleanly in dev without credentials.

    """

    _RESEND_URL = "https://api.resend.com/emails"

    def __init__(self) -> None:
        self._api_key = external_settings.RESEND_API_KEY
        self._from_address = external_settings.EMAIL_FROM

    async def send(self, *, to: str, subject: str, html: str) -> None:
        """Send a transactional email.

        Args:
            to (str): Recipient email address.
            subject (str): Email subject line.
            html (str): HTML body of the email.

        """
        if not self._api_key:
            log.debug("email.skipped_no_api_key", to=to, subject=subject)
            return

        payload = json.dumps({
            "from": self._from_address,
            "to": [to],
            "subject": subject,
            "html": html,
        }).encode()

        await anyio.to_thread.run_sync(lambda: self._post(payload))

    def _post(self, payload: bytes) -> None:
        req = urllib.request.Request(
            self._RESEND_URL,
            data=payload,
            headers={
                "Authorization": f"Bearer {self._api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=10) as resp:
                log.info("email.sent", status=resp.status)
        except urllib.error.HTTPError as exc:
            body = exc.read().decode(errors="replace")
            log.error("email.send_failed", status=exc.code, body=body)
            raise

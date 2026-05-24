"""Unit tests for custom middleware — isolated app fixtures, no database."""

# ───────────────────────────────────────────────────── Imports ────────────────────────────────────────────────────── #

# Third-Party Library
import pytest
from fastapi import FastAPI
from fastapi.responses import JSONResponse
from httpx import ASGITransport, AsyncClient

# Private Library
from src.core.middleware.body_limit import BodySizeLimitMiddleware

# ────────────────────────────────────────────────────── Code ──────────────────────────────────────────────────────── #

_BODY_LIMIT = 100  # bytes — small enough to test easily


def _make_app_with_body_limit() -> FastAPI:
    app = FastAPI()
    app.add_middleware(BodySizeLimitMiddleware, max_bytes=_BODY_LIMIT)

    @app.post("/echo")
    async def echo() -> JSONResponse:
        return JSONResponse({"ok": True})

    return app


@pytest.fixture
async def body_limit_client():
    async with AsyncClient(transport=ASGITransport(app=_make_app_with_body_limit()), base_url="http://test") as c:
        yield c


class TestBodySizeLimitMiddleware:
    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_passes_through_when_under_limit(self, body_limit_client: AsyncClient) -> None:
        body = b"x" * _BODY_LIMIT
        response = await body_limit_client.post("/echo", content=body, headers={"content-length": str(len(body))})
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_413_when_over_limit(self, body_limit_client: AsyncClient) -> None:
        body = b"x" * (_BODY_LIMIT + 1)
        response = await body_limit_client.post("/echo", content=body, headers={"content-length": str(len(body))})
        assert response.status_code == 413
        data = response.json()
        assert data["error"]["code"] == "PAYLOAD_TOO_LARGE"

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_passes_through_when_no_content_length(self, body_limit_client: AsyncClient) -> None:
        response = await body_limit_client.post("/echo")
        assert response.status_code == 200

    @pytest.mark.unit
    @pytest.mark.asyncio
    async def test_returns_400_for_invalid_content_length(self, body_limit_client: AsyncClient) -> None:
        response = await body_limit_client.post("/echo", headers={"content-length": "not-a-number"})
        assert response.status_code == 400
        data = response.json()
        assert data["error"]["code"] == "BAD_REQUEST"

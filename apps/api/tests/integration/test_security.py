import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_security_headers_present(client: AsyncClient):
    resp = await client.get("/health")
    assert resp.status_code == 200
    assert resp.headers.get("x-content-type-options") == "nosniff"
    assert resp.headers.get("x-frame-options") == "DENY"
    assert resp.headers.get("referrer-policy") == "strict-origin-when-cross-origin"
    assert "permissions-policy" in resp.headers


@pytest.mark.asyncio
async def test_oversized_payload_returns_413(client: AsyncClient):
    resp = await client.post(
        "/v1/users",
        headers={"Content-Length": "999999999"},
        json={"display_name": "x"},
    )
    assert resp.status_code == 413
    payload = resp.json()
    assert payload.get("error", {}).get("code") == "PAYLOAD_TOO_LARGE"

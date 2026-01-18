from __future__ import annotations

import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_guest_feed_public_and_unauthenticated(client: AsyncClient):
    resp = await client.get("/v1/feed?k=1&cursor=0")
    assert resp.status_code == 200
    payload = resp.json()
    assert "data" in payload
    assert "meta" in payload

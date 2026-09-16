"""Test configuration and fixtures"""
import pytest
import pytest_asyncio
from httpx import AsyncClient, ASGITransport
from app.main import app


@pytest_asyncio.fixture
async def client():
    """Create test client"""
    async with AsyncClient(transport=ASGITransport(app=app), base_url="http://test") as c:
        yield c


@pytest.fixture
def auth_headers(client):
    """Get auth headers for admin"""
    return {"Authorization": "Bearer test-token"}

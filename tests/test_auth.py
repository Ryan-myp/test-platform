"""Tests for authentication API"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_register_user(client: AsyncClient):
    """Test user registration"""
    response = await client.post("/api/auth/register", json={
        "username": "testuser",
        "password": "testpass123",
        "email": "test@example.com",
        "role": "member"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["username"] == "testuser"


@pytest.mark.asyncio
async def test_login_admin(client: AsyncClient):
    """Test admin login"""
    response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "admin123"
    })
    assert response.status_code == 200
    data = response.json()
    assert "access_token" in data
    assert data["user"]["username"] == "admin"


@pytest.mark.asyncio
async def test_login_invalid_credentials(client: AsyncClient):
    """Test login with invalid credentials"""
    response = await client.post("/api/auth/login", json={
        "username": "admin",
        "password": "wrongpassword"
    })
    assert response.status_code == 401


@pytest.mark.asyncio
async def test_register_duplicate_user(client: AsyncClient):
    """Test registering duplicate username"""
    # First registration
    await client.post("/api/auth/register", json={
        "username": "dupuser",
        "password": "testpass123"
    })
    # Second registration should fail
    response = await client.post("/api/auth/register", json={
        "username": "dupuser",
        "password": "testpass123"
    })
    assert response.status_code == 400

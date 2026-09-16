"""Tests for bugs API"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_bugs(client: AsyncClient):
    """Test listing bugs"""
    response = await client.get("/api/bugs")
    assert response.status_code == 200
    data = response.json()
    assert "bugs" in data


@pytest.mark.asyncio
async def test_create_bug(client: AsyncClient):
    """Test creating a bug"""
    response = await client.post("/api/bugs", json={
        "title": "Test Bug",
        "description": "This is a test bug",
        "severity": "major",
        "module": "Test Module"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["title"] == "Test Bug"
    assert "id" in data


@pytest.mark.asyncio
async def test_update_bug_status(client: AsyncClient):
    """Test updating bug status"""
    # Create a bug
    create_resp = await client.post("/api/bugs", json={
        "title": "Status Test",
        "severity": "minor"
    })
    bug_id = create_resp.json()["id"]
    
    # Update status
    response = await client.patch(f"/api/bugs/{bug_id}", json={
        "status": "fixed"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "fixed"

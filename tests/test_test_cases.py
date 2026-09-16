"""Tests for test cases API"""
import pytest
from httpx import AsyncClient


@pytest.mark.asyncio
async def test_list_test_cases(client: AsyncClient):
    """Test listing test cases"""
    response = await client.get("/api/test-cases")
    assert response.status_code == 200
    data = response.json()
    assert "cases" in data
    assert "total" in data


@pytest.mark.asyncio
async def test_create_test_case(client: AsyncClient):
    """Test creating a test case"""
    response = await client.post("/api/test-cases", json={
        "name": "New Test Case",
        "module": "Test Module",
        "priority": "P1",
        "case_type": "api",
        "status": "draft"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "New Test Case"
    assert "id" in data


@pytest.mark.asyncio
async def test_get_test_case(client: AsyncClient):
    """Test getting a single test case"""
    # First create a case
    create_resp = await client.post("/api/test-cases", json={
        "name": "Get Test",
        "priority": "P2",
        "case_type": "api"
    })
    case_id = create_resp.json()["id"]
    
    # Then get it
    response = await client.get(f"/api/test-cases/{case_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["name"] == "Get Test"


@pytest.mark.asyncio
async def test_update_test_case(client: AsyncClient):
    """Test updating a test case"""
    # Create a case
    create_resp = await client.post("/api/test-cases", json={
        "name": "Update Test",
        "priority": "P2",
        "case_type": "api"
    })
    case_id = create_resp.json()["id"]
    
    # Update it
    response = await client.patch(f"/api/test-cases/{case_id}", json={
        "priority": "P0",
        "status": "active"
    })
    assert response.status_code == 200
    data = response.json()
    assert data["priority"] == "P0"


@pytest.mark.asyncio
async def test_delete_test_case(client: AsyncClient):
    """Test deleting a test case"""
    # Create a case
    create_resp = await client.post("/api/test-cases", json={
        "name": "Delete Test",
        "priority": "P2",
        "case_type": "api"
    })
    case_id = create_resp.json()["id"]
    
    # Delete it
    response = await client.delete(f"/api/test-cases/{case_id}")
    assert response.status_code == 200
    
    # Verify deleted
    get_resp = await client.get(f"/api/test-cases/{case_id}")
    assert get_resp.status_code == 404

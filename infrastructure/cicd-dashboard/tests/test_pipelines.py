"""Tests for pipeline API endpoints."""

import pytest


@pytest.mark.asyncio
async def test_list_pipelines_empty(client):
    """Test that pipeline list is empty initially."""
    response = await client.get("/api/v1/pipelines")
    assert response.status_code == 200
    assert response.json() == []


@pytest.mark.asyncio
async def test_create_pipeline(client):
    """Test creating a new pipeline."""
    pipeline_data = {
        "repo": "obtFusi/network-agent",
        "ref": "main",
        "version": "0.10.0",
        "trigger": "manual",
    }
    response = await client.post("/api/v1/pipelines", json=pipeline_data)
    assert response.status_code == 201
    data = response.json()
    assert data["repo"] == "obtFusi/network-agent"
    assert data["ref"] == "main"
    assert data["version"] == "0.10.0"
    assert data["trigger"] == "manual"
    assert data["status"] == "pending"
    assert "id" in data
    assert "created_at" in data


@pytest.mark.asyncio
async def test_get_pipeline(client):
    """Test getting a specific pipeline."""
    # First create a pipeline
    pipeline_data = {
        "repo": "obtFusi/network-agent",
        "ref": "feature/test",
        "trigger": "manual",
    }
    create_response = await client.post("/api/v1/pipelines", json=pipeline_data)
    assert create_response.status_code == 201
    pipeline_id = create_response.json()["id"]

    # Then retrieve it
    response = await client.get(f"/api/v1/pipelines/{pipeline_id}")
    assert response.status_code == 200
    data = response.json()
    assert data["id"] == pipeline_id
    assert data["repo"] == "obtFusi/network-agent"
    assert data["steps"] == []
    assert data["approvals"] == []


@pytest.mark.asyncio
async def test_get_pipeline_not_found(client):
    """Test getting a non-existent pipeline returns 404."""
    response = await client.get("/api/v1/pipelines/non-existent-id")
    assert response.status_code == 404
    assert response.json()["detail"] == "Pipeline not found"


@pytest.mark.asyncio
async def test_list_pipelines_with_data(client):
    """Test that pipeline list returns created pipelines."""
    # Create two pipelines
    for i in range(2):
        await client.post(
            "/api/v1/pipelines",
            json={"repo": "test/repo", "ref": f"branch-{i}", "trigger": "manual"},
        )

    response = await client.get("/api/v1/pipelines")
    assert response.status_code == 200
    data = response.json()
    assert len(data) == 2


@pytest.mark.asyncio
async def test_list_pipelines_pagination(client):
    """Test pagination of pipeline list."""
    # Create 5 pipelines
    for i in range(5):
        await client.post(
            "/api/v1/pipelines",
            json={"repo": "test/repo", "ref": f"branch-{i}", "trigger": "manual"},
        )

    # Get first 2
    response = await client.get("/api/v1/pipelines?limit=2&offset=0")
    assert response.status_code == 200
    assert len(response.json()) == 2

    # Get next 2
    response = await client.get("/api/v1/pipelines?limit=2&offset=2")
    assert response.status_code == 200
    assert len(response.json()) == 2

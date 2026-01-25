"""Tests for pipeline API endpoints."""

import pytest

from app.models import (
    Approval,
    Pipeline,
    PipelineStatus,
    PipelineStep,
    StepStatus,
)


@pytest.mark.asyncio
async def test_start_pipeline(client, db_session):
    """Test starting a pipeline via API."""
    # Create a pending pipeline
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    response = await client.post(f"/api/v1/pipelines/{pipeline.id}/start")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "running"
    assert len(data["steps"]) > 0


@pytest.mark.asyncio
async def test_start_pipeline_not_found(client):
    """Test starting a non-existent pipeline returns 400."""
    response = await client.post("/api/v1/pipelines/non-existent-id/start")
    assert response.status_code == 400
    assert "not found" in response.json()["detail"]


@pytest.mark.asyncio
async def test_abort_pipeline(client, db_session):
    """Test aborting a running pipeline via API."""
    # Create a running pipeline with a step
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
        status=PipelineStatus.RUNNING,
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    step = PipelineStep(
        pipeline_id=pipeline.id,
        name="test-step",
        stage="validate",
        status=StepStatus.RUNNING,
    )
    db_session.add(step)
    await db_session.commit()

    response = await client.post(f"/api/v1/pipelines/{pipeline.id}/abort")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "aborted"


@pytest.mark.asyncio
async def test_retry_step(client, db_session):
    """Test retrying a failed step via API."""
    # Create a failed pipeline with a failed step
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
        status=PipelineStatus.FAILED,
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    step = PipelineStep(
        pipeline_id=pipeline.id,
        name="test-step",
        stage="validate",
        status=StepStatus.FAILED,
        error="Test error",
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    response = await client.post(f"/api/v1/pipelines/{pipeline.id}/retry/{step.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "pending"
    assert data["message"] == "Step reset for retry"


@pytest.mark.asyncio
async def test_list_running_pipelines(client, db_session):
    """Test listing running pipelines."""
    # Create pipelines with different statuses
    running = Pipeline(
        repo="test/repo1",
        ref="main",
        trigger="manual",
        status=PipelineStatus.RUNNING,
    )
    waiting = Pipeline(
        repo="test/repo2",
        ref="main",
        trigger="manual",
        status=PipelineStatus.WAITING_APPROVAL,
    )
    completed = Pipeline(
        repo="test/repo3",
        ref="main",
        trigger="manual",
        status=PipelineStatus.COMPLETED,
    )
    db_session.add_all([running, waiting, completed])
    await db_session.commit()

    response = await client.get("/api/v1/pipelines/running")

    assert response.status_code == 200
    data = response.json()
    # Should only return running and waiting_approval
    assert len(data) == 2
    repos = {p["repo"] for p in data}
    assert "test/repo1" in repos
    assert "test/repo2" in repos
    assert "test/repo3" not in repos


@pytest.mark.asyncio
async def test_list_pending_approvals(client, db_session):
    """Test listing pending approvals."""
    # Create a pipeline with pending approval
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
        status=PipelineStatus.WAITING_APPROVAL,
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    step = PipelineStep(
        pipeline_id=pipeline.id,
        name="pr-merge",
        stage="review",
        requires_approval=True,
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    approval = Approval(
        pipeline_id=pipeline.id,
        step_id=step.id,
    )
    db_session.add(approval)
    await db_session.commit()

    response = await client.get("/api/v1/approvals/pending")

    assert response.status_code == 200
    data = response.json()
    assert len(data) == 1
    assert data[0]["step_name"] == "pr-merge"
    assert data[0]["stage"] == "review"


@pytest.mark.asyncio
async def test_approve_approval(client, db_session):
    """Test approving an approval via API."""
    # Create pipeline with pending approval
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
        status=PipelineStatus.WAITING_APPROVAL,
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    step = PipelineStep(
        pipeline_id=pipeline.id,
        name="test-step",
        stage="review",
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    approval = Approval(
        pipeline_id=pipeline.id,
        step_id=step.id,
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)

    response = await client.post(
        f"/api/v1/approvals/{approval.id}/approve",
        json={"user": "testuser", "comment": "LGTM"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "approved"
    assert data["responded_by"] == "testuser"
    assert data["comment"] == "LGTM"


@pytest.mark.asyncio
async def test_reject_approval(client, db_session):
    """Test rejecting an approval via API."""
    # Create pipeline with pending approval
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
        status=PipelineStatus.WAITING_APPROVAL,
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    step = PipelineStep(
        pipeline_id=pipeline.id,
        name="test-step",
        stage="review",
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    approval = Approval(
        pipeline_id=pipeline.id,
        step_id=step.id,
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)

    response = await client.post(
        f"/api/v1/approvals/{approval.id}/reject",
        json={"user": "testuser", "reason": "Needs more work"},
    )

    assert response.status_code == 200
    data = response.json()
    assert data["status"] == "rejected"
    assert data["responded_by"] == "testuser"


@pytest.mark.asyncio
async def test_get_approval(client, db_session):
    """Test getting approval details."""
    # Create pipeline with approval
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    step = PipelineStep(
        pipeline_id=pipeline.id,
        name="test-step",
        stage="review",
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    approval = Approval(
        pipeline_id=pipeline.id,
        step_id=step.id,
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)

    response = await client.get(f"/api/v1/approvals/{approval.id}")

    assert response.status_code == 200
    data = response.json()
    assert data["id"] == approval.id
    assert data["pipeline_id"] == pipeline.id
    assert data["step_id"] == step.id
    assert data["status"] == "pending"


@pytest.mark.asyncio
async def test_get_approval_not_found(client):
    """Test getting non-existent approval returns 404."""
    response = await client.get("/api/v1/approvals/non-existent-id")
    assert response.status_code == 404

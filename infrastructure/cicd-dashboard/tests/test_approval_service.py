"""Tests for approval service."""

import pytest

from app.models import (
    Approval,
    ApprovalStatus,
    Pipeline,
    PipelineStatus,
    PipelineStep,
)
from app.services.approval_service import ApprovalError, ApprovalService


@pytest.mark.asyncio
async def test_request_approval(db_session):
    """Test requesting approval for a step."""
    # Create a pipeline and step
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
        stage="review",
        requires_approval=True,
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    service = ApprovalService(db_session)

    # Request approval
    approval = await service.request_approval(pipeline.id, step.id)
    await db_session.commit()

    assert approval is not None
    assert approval.pipeline_id == pipeline.id
    assert approval.step_id == step.id
    assert approval.status == ApprovalStatus.PENDING

    # Pipeline should be waiting approval
    await db_session.refresh(pipeline)
    assert pipeline.status == PipelineStatus.WAITING_APPROVAL


@pytest.mark.asyncio
async def test_request_approval_returns_existing(db_session):
    """Test requesting approval returns existing pending approval."""
    # Create a pipeline and step
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
        stage="review",
        requires_approval=True,
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    service = ApprovalService(db_session)

    # Request approval twice
    approval1 = await service.request_approval(pipeline.id, step.id)
    await db_session.commit()

    approval2 = await service.request_approval(pipeline.id, step.id)
    await db_session.commit()

    # Should return same approval
    assert approval1.id == approval2.id


@pytest.mark.asyncio
async def test_request_approval_pipeline_not_found(db_session):
    """Test requesting approval for non-existent pipeline raises error."""
    service = ApprovalService(db_session)

    with pytest.raises(ApprovalError, match="Pipeline .* not found"):
        await service.request_approval("non-existent", "step-id")


@pytest.mark.asyncio
async def test_approve_request(db_session):
    """Test approving an approval request."""
    # Create a pipeline and step
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
        requires_approval=True,
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    # Create pending approval
    approval = Approval(
        pipeline_id=pipeline.id,
        step_id=step.id,
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)

    service = ApprovalService(db_session)

    # Approve
    result = await service.approve(approval.id, "testuser", "Looks good!")
    await db_session.commit()

    assert result is True

    # Check approval status
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.APPROVED
    assert approval.responded_by == "testuser"
    assert approval.comment == "Looks good!"
    assert approval.responded_at is not None

    # Pipeline should be running again
    await db_session.refresh(pipeline)
    assert pipeline.status == PipelineStatus.RUNNING


@pytest.mark.asyncio
async def test_approve_request_not_found(db_session):
    """Test approving non-existent approval raises error."""
    service = ApprovalService(db_session)

    with pytest.raises(ApprovalError, match="not found"):
        await service.approve("non-existent", "testuser")


@pytest.mark.asyncio
async def test_approve_request_not_pending(db_session):
    """Test approving non-pending approval raises error."""
    # Create a pipeline and step
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

    # Create already approved approval
    approval = Approval(
        pipeline_id=pipeline.id,
        step_id=step.id,
        status=ApprovalStatus.APPROVED,
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)

    service = ApprovalService(db_session)

    with pytest.raises(ApprovalError, match="not pending"):
        await service.approve(approval.id, "testuser")


@pytest.mark.asyncio
async def test_reject_request(db_session):
    """Test rejecting an approval request."""
    # Create a pipeline and step
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
        requires_approval=True,
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    # Create pending approval
    approval = Approval(
        pipeline_id=pipeline.id,
        step_id=step.id,
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)

    service = ApprovalService(db_session)

    # Reject
    result = await service.reject(approval.id, "testuser", "Needs more work")
    await db_session.commit()

    assert result is True

    # Check approval status
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.REJECTED
    assert approval.responded_by == "testuser"
    assert approval.comment == "Needs more work"

    # Pipeline should be failed
    await db_session.refresh(pipeline)
    assert pipeline.status == PipelineStatus.FAILED


@pytest.mark.asyncio
async def test_get_pending_approvals(db_session):
    """Test getting all pending approvals."""
    # Create pipelines and steps
    pipeline1 = Pipeline(repo="test/repo1", ref="main", trigger="manual")
    pipeline2 = Pipeline(repo="test/repo2", ref="main", trigger="manual")
    db_session.add_all([pipeline1, pipeline2])
    await db_session.commit()
    await db_session.refresh(pipeline1)
    await db_session.refresh(pipeline2)

    step1 = PipelineStep(pipeline_id=pipeline1.id, name="step1", stage="review")
    step2 = PipelineStep(pipeline_id=pipeline2.id, name="step2", stage="review")
    db_session.add_all([step1, step2])
    await db_session.commit()
    await db_session.refresh(step1)
    await db_session.refresh(step2)

    # Create approvals with different statuses
    approval1 = Approval(pipeline_id=pipeline1.id, step_id=step1.id)  # PENDING
    approval2 = Approval(pipeline_id=pipeline2.id, step_id=step2.id)  # PENDING
    approval3 = Approval(
        pipeline_id=pipeline1.id,
        step_id=step1.id,
        status=ApprovalStatus.APPROVED,
    )  # APPROVED
    db_session.add_all([approval1, approval2, approval3])
    await db_session.commit()

    service = ApprovalService(db_session)
    pending = await service.get_pending_approvals()

    # Should only return pending approvals
    assert len(pending) == 2
    statuses = {a.status for a in pending}
    assert statuses == {ApprovalStatus.PENDING}


@pytest.mark.asyncio
async def test_check_timeout_not_expired(db_session):
    """Test check_timeout returns False for non-expired approval."""
    # Create a pipeline and step
    pipeline = Pipeline(repo="test/repo", ref="main", trigger="manual")
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    step = PipelineStep(pipeline_id=pipeline.id, name="step", stage="review")
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    # Create recent approval
    approval = Approval(
        pipeline_id=pipeline.id,
        step_id=step.id,
    )
    db_session.add(approval)
    await db_session.commit()
    await db_session.refresh(approval)

    service = ApprovalService(db_session)
    result = await service.check_timeout(approval.id)

    assert result is False
    await db_session.refresh(approval)
    assert approval.status == ApprovalStatus.PENDING


@pytest.mark.asyncio
async def test_get_approvals_for_pipeline(db_session):
    """Test getting all approvals for a pipeline."""
    # Create pipeline and steps
    pipeline = Pipeline(repo="test/repo", ref="main", trigger="manual")
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    step1 = PipelineStep(pipeline_id=pipeline.id, name="step1", stage="review")
    step2 = PipelineStep(pipeline_id=pipeline.id, name="step2", stage="release")
    db_session.add_all([step1, step2])
    await db_session.commit()
    await db_session.refresh(step1)
    await db_session.refresh(step2)

    # Create approvals
    approval1 = Approval(pipeline_id=pipeline.id, step_id=step1.id)
    approval2 = Approval(pipeline_id=pipeline.id, step_id=step2.id)
    db_session.add_all([approval1, approval2])
    await db_session.commit()

    service = ApprovalService(db_session)
    approvals = await service.get_approvals_for_pipeline(pipeline.id)

    assert len(approvals) == 2

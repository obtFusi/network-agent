"""Tests for pipeline executor service."""

import pytest
from sqlalchemy import select

from app.models import (
    Pipeline,
    PipelineStatus,
    PipelineStep,
    StepStatus,
)
from app.services.pipeline_executor import (
    PipelineExecutor,
    PipelineExecutorError,
)


@pytest.mark.asyncio
async def test_start_pipeline(db_session):
    """Test starting a pipeline creates steps and updates status."""
    # Create a pending pipeline
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    executor = PipelineExecutor(db_session)

    # Start the pipeline
    result = await executor.start_pipeline(pipeline.id)
    await db_session.commit()

    assert result.status == PipelineStatus.RUNNING

    # Check steps were created
    steps_result = await db_session.execute(
        select(PipelineStep).where(PipelineStep.pipeline_id == pipeline.id)
    )
    steps = list(steps_result.scalars().all())

    # Should have steps for all stages
    assert len(steps) > 0
    stage_names = {s.stage for s in steps}
    assert "validate" in stage_names
    assert "review" in stage_names
    assert "release" in stage_names


@pytest.mark.asyncio
async def test_start_pipeline_not_found(db_session):
    """Test starting a non-existent pipeline raises error."""
    executor = PipelineExecutor(db_session)

    with pytest.raises(PipelineExecutorError, match="not found"):
        await executor.start_pipeline("non-existent-id")


@pytest.mark.asyncio
async def test_start_pipeline_wrong_status(db_session):
    """Test starting a running pipeline raises error."""
    # Create a running pipeline
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
        status=PipelineStatus.RUNNING,
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    executor = PipelineExecutor(db_session)

    with pytest.raises(PipelineExecutorError, match="cannot be started"):
        await executor.start_pipeline(pipeline.id)


@pytest.mark.asyncio
async def test_abort_pipeline(db_session):
    """Test aborting a running pipeline."""
    # Create a running pipeline
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
        status=PipelineStatus.RUNNING,
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    # Add a running step
    step = PipelineStep(
        pipeline_id=pipeline.id,
        name="test-step",
        stage="validate",
        status=StepStatus.RUNNING,
    )
    db_session.add(step)
    await db_session.commit()

    executor = PipelineExecutor(db_session)

    # Abort the pipeline
    result = await executor.abort_pipeline(pipeline.id)
    await db_session.commit()

    assert result.status == PipelineStatus.ABORTED
    assert result.completed_at is not None

    # Check step was skipped
    await db_session.refresh(step)
    assert step.status == StepStatus.SKIPPED


@pytest.mark.asyncio
async def test_abort_pipeline_not_found(db_session):
    """Test aborting a non-existent pipeline raises error."""
    executor = PipelineExecutor(db_session)

    with pytest.raises(PipelineExecutorError, match="not found"):
        await executor.abort_pipeline("non-existent-id")


@pytest.mark.asyncio
async def test_retry_step(db_session):
    """Test retrying a failed step."""
    # Create a failed pipeline
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
        status=PipelineStatus.FAILED,
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    # Add a failed step
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

    executor = PipelineExecutor(db_session)

    # Retry the step
    result = await executor.retry_step(pipeline.id, step.id)
    await db_session.commit()

    assert result.status == StepStatus.PENDING
    assert result.error is None

    # Pipeline should be running again
    await db_session.refresh(pipeline)
    assert pipeline.status == PipelineStatus.RUNNING


@pytest.mark.asyncio
async def test_retry_step_not_found(db_session):
    """Test retrying a non-existent step raises error."""
    # Create a pipeline
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    executor = PipelineExecutor(db_session)

    with pytest.raises(PipelineExecutorError, match="not found"):
        await executor.retry_step(pipeline.id, "non-existent-step")


@pytest.mark.asyncio
async def test_retry_step_wrong_status(db_session):
    """Test retrying a non-failed step raises error."""
    # Create a pipeline
    pipeline = Pipeline(
        repo="test/repo",
        ref="main",
        trigger="manual",
    )
    db_session.add(pipeline)
    await db_session.commit()
    await db_session.refresh(pipeline)

    # Add a completed step
    step = PipelineStep(
        pipeline_id=pipeline.id,
        name="test-step",
        stage="validate",
        status=StepStatus.COMPLETED,
    )
    db_session.add(step)
    await db_session.commit()
    await db_session.refresh(step)

    executor = PipelineExecutor(db_session)

    with pytest.raises(PipelineExecutorError, match="cannot be retried"):
        await executor.retry_step(pipeline.id, step.id)


@pytest.mark.asyncio
async def test_get_running_pipelines(db_session):
    """Test getting list of running pipeline IDs."""
    executor = PipelineExecutor(db_session)

    # Initially empty
    assert executor.get_running_pipelines() == []

"""Pipeline management API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Pipeline, PipelineStatus
from app.schemas import PipelineResponse
from app.services.pipeline_executor import PipelineExecutor, PipelineExecutorError

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/pipelines", tags=["pipelines"])

# Type alias for database dependency
DB = Annotated[AsyncSession, Depends(get_db)]


# Shared executor instance (will be properly managed in production)
_executor: PipelineExecutor | None = None


def get_executor(db: AsyncSession) -> PipelineExecutor:
    """Get or create the pipeline executor."""
    global _executor
    if _executor is None:
        _executor = PipelineExecutor(db)
    else:
        _executor.db = db
    return _executor


@router.post("/{pipeline_id}/start", response_model=PipelineResponse)
async def start_pipeline(pipeline_id: str, db: DB):
    """Start a pipeline execution.

    This initiates the pipeline orchestration process, creating steps
    and beginning execution through all stages.

    Args:
        pipeline_id: UUID of the pipeline to start

    Returns:
        Updated pipeline with status RUNNING
    """
    executor = get_executor(db)

    try:
        await executor.start_pipeline(pipeline_id)
        await db.commit()

        # Reload with relationships
        result = await db.execute(
            select(Pipeline)
            .options(
                selectinload(Pipeline.steps),
                selectinload(Pipeline.approvals),
            )
            .where(Pipeline.id == pipeline_id)
        )
        return result.scalar_one()

    except PipelineExecutorError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{pipeline_id}/abort", response_model=PipelineResponse)
async def abort_pipeline(pipeline_id: str, db: DB):
    """Abort a running pipeline.

    This stops the pipeline execution immediately, marking it as ABORTED
    and skipping any remaining steps.

    Args:
        pipeline_id: UUID of the pipeline to abort

    Returns:
        Updated pipeline with status ABORTED
    """
    executor = get_executor(db)

    try:
        await executor.abort_pipeline(pipeline_id)
        await db.commit()

        # Reload with relationships
        result = await db.execute(
            select(Pipeline)
            .options(
                selectinload(Pipeline.steps),
                selectinload(Pipeline.approvals),
            )
            .where(Pipeline.id == pipeline_id)
        )
        return result.scalar_one()

    except PipelineExecutorError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{pipeline_id}/retry/{step_id}")
async def retry_step(pipeline_id: str, step_id: str, db: DB):
    """Retry a failed step in the pipeline.

    This resets the step status to PENDING and allows re-execution.

    Args:
        pipeline_id: UUID of the pipeline
        step_id: UUID of the step to retry

    Returns:
        Updated step information
    """
    executor = get_executor(db)

    try:
        step = await executor.retry_step(pipeline_id, step_id)
        await db.commit()

        return {
            "id": step.id,
            "name": step.name,
            "stage": step.stage,
            "status": step.status.value,
            "message": "Step reset for retry",
        }

    except PipelineExecutorError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.get("/running")
async def list_running_pipelines(db: DB):
    """List all currently running pipelines.

    Returns:
        List of running pipeline IDs and their status
    """
    result = await db.execute(
        select(Pipeline)
        .where(
            Pipeline.status.in_(
                [PipelineStatus.RUNNING, PipelineStatus.WAITING_APPROVAL]
            )
        )
        .order_by(Pipeline.created_at.desc())
    )
    pipelines = result.scalars().all()

    return [
        {
            "id": p.id,
            "repo": p.repo,
            "status": p.status.value,
            "trigger": p.trigger,
            "created_at": p.created_at.isoformat(),
        }
        for p in pipelines
    ]

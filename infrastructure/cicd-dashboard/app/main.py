"""FastAPI application for CI/CD Dashboard."""

from contextlib import asynccontextmanager
from typing import Annotated

from fastapi import Depends, FastAPI, HTTPException
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app import __version__
from app.api.webhooks import router as webhooks_router
from app.config import settings
from app.database import get_db, init_db
from app.models import Pipeline
from app.schemas import (
    PipelineCreate,
    PipelineListResponse,
    PipelineResponse,
)


@asynccontextmanager
async def lifespan(app: FastAPI):
    """Application lifespan: initialize database on startup."""
    await init_db()
    yield


app = FastAPI(
    title="CI/CD Dashboard API",
    description="Backend API for the Network Agent CI/CD Dashboard",
    version=__version__,
    lifespan=lifespan,
)

# Include routers
app.include_router(webhooks_router)


# Type alias for database dependency
DB = Annotated[AsyncSession, Depends(get_db)]


@app.get("/health")
async def health_check():
    """Health check endpoint for Docker/Kubernetes probes."""
    return {"status": "healthy", "version": __version__}


@app.get(f"{settings.api_prefix}/pipelines", response_model=list[PipelineListResponse])
async def list_pipelines(db: DB, limit: int = 50, offset: int = 0):
    """List all pipelines with pagination."""
    result = await db.execute(
        select(Pipeline)
        .order_by(Pipeline.created_at.desc())
        .limit(limit)
        .offset(offset)
    )
    return result.scalars().all()


@app.get(
    f"{settings.api_prefix}/pipelines/{{pipeline_id}}", response_model=PipelineResponse
)
async def get_pipeline(pipeline_id: str, db: DB):
    """Get a specific pipeline with all its steps and approvals."""
    result = await db.execute(
        select(Pipeline)
        .options(
            selectinload(Pipeline.steps),
            selectinload(Pipeline.approvals),
        )
        .where(Pipeline.id == pipeline_id)
    )
    pipeline = result.scalar_one_or_none()

    if not pipeline:
        raise HTTPException(status_code=404, detail="Pipeline not found")

    return pipeline


@app.post(
    f"{settings.api_prefix}/pipelines",
    response_model=PipelineListResponse,
    status_code=201,
)
async def create_pipeline(pipeline_data: PipelineCreate, db: DB):
    """Create a new pipeline (manual trigger).

    Returns PipelineListResponse (not PipelineResponse) because a newly created
    pipeline has no steps or approvals yet.
    """
    pipeline = Pipeline(
        repo=pipeline_data.repo,
        ref=pipeline_data.ref,
        version=pipeline_data.version,
        trigger=pipeline_data.trigger,
        trigger_data=pipeline_data.trigger_data,
    )
    db.add(pipeline)
    await db.flush()
    await db.refresh(pipeline)
    return pipeline

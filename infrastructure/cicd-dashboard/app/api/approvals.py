"""Approval management API endpoints."""

import logging
from typing import Annotated

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from app.database import get_db
from app.models import Approval
from app.services.approval_service import ApprovalError, ApprovalService

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/api/v1/approvals", tags=["approvals"])

# Type alias for database dependency
DB = Annotated[AsyncSession, Depends(get_db)]


class ApproveRequest(BaseModel):
    """Request body for approving a request."""

    user: str
    comment: str | None = None


class RejectRequest(BaseModel):
    """Request body for rejecting a request."""

    user: str
    reason: str | None = None


class ApprovalResponse(BaseModel):
    """Response model for approval details."""

    id: str
    pipeline_id: str
    step_id: str
    status: str
    requested_at: str
    responded_at: str | None
    responded_by: str | None
    comment: str | None

    model_config = {"from_attributes": True}


class PendingApprovalResponse(BaseModel):
    """Response model for pending approval with context."""

    id: str
    pipeline_id: str
    step_id: str
    step_name: str
    stage: str
    repo: str
    requested_at: str


@router.get("/pending", response_model=list[PendingApprovalResponse])
async def list_pending_approvals(db: DB):
    """List all pending approval requests.

    Returns approvals that are waiting for user action, with
    additional context about the associated pipeline and step.

    Returns:
        List of pending approvals with context
    """
    service = ApprovalService(db)
    approvals = await service.get_pending_approvals()

    result = []
    for approval in approvals:
        # Load relationships manually
        approval_result = await db.execute(
            select(Approval)
            .options(
                selectinload(Approval.pipeline),
                selectinload(Approval.step),
            )
            .where(Approval.id == approval.id)
        )
        approval_with_rels = approval_result.scalar_one()

        result.append(
            PendingApprovalResponse(
                id=approval_with_rels.id,
                pipeline_id=approval_with_rels.pipeline_id,
                step_id=approval_with_rels.step_id,
                step_name=approval_with_rels.step.name
                if approval_with_rels.step
                else "unknown",
                stage=approval_with_rels.step.stage
                if approval_with_rels.step
                else "unknown",
                repo=approval_with_rels.pipeline.repo
                if approval_with_rels.pipeline
                else "unknown",
                requested_at=approval_with_rels.requested_at.isoformat(),
            )
        )

    return result


@router.get("/{approval_id}", response_model=ApprovalResponse)
async def get_approval(approval_id: str, db: DB):
    """Get details of a specific approval.

    Args:
        approval_id: UUID of the approval

    Returns:
        Approval details including status and response
    """
    service = ApprovalService(db)
    approval = await service.get_approval(approval_id)

    if not approval:
        raise HTTPException(status_code=404, detail="Approval not found")

    return ApprovalResponse(
        id=approval.id,
        pipeline_id=approval.pipeline_id,
        step_id=approval.step_id,
        status=approval.status.value,
        requested_at=approval.requested_at.isoformat(),
        responded_at=approval.responded_at.isoformat()
        if approval.responded_at
        else None,
        responded_by=approval.responded_by,
        comment=approval.comment,
    )


@router.post("/{approval_id}/approve", response_model=ApprovalResponse)
async def approve_request(approval_id: str, request: ApproveRequest, db: DB):
    """Approve a pending approval request.

    This grants approval for the associated pipeline step, allowing
    the pipeline to continue execution.

    Args:
        approval_id: UUID of the approval to approve
        request: Approval details including user and optional comment

    Returns:
        Updated approval with APPROVED status
    """
    service = ApprovalService(db)

    try:
        await service.approve(approval_id, request.user, request.comment)
        await db.commit()

        approval = await service.get_approval(approval_id)

        logger.info(
            "Approval %s approved by %s",
            approval_id,
            request.user,
        )

        return ApprovalResponse(
            id=approval.id,
            pipeline_id=approval.pipeline_id,
            step_id=approval.step_id,
            status=approval.status.value,
            requested_at=approval.requested_at.isoformat(),
            responded_at=approval.responded_at.isoformat()
            if approval.responded_at
            else None,
            responded_by=approval.responded_by,
            comment=approval.comment,
        )

    except ApprovalError as e:
        raise HTTPException(status_code=400, detail=str(e))


@router.post("/{approval_id}/reject", response_model=ApprovalResponse)
async def reject_request(approval_id: str, request: RejectRequest, db: DB):
    """Reject a pending approval request.

    This denies approval for the associated pipeline step, causing
    the pipeline to fail.

    Args:
        approval_id: UUID of the approval to reject
        request: Rejection details including user and optional reason

    Returns:
        Updated approval with REJECTED status
    """
    service = ApprovalService(db)

    try:
        await service.reject(approval_id, request.user, request.reason)
        await db.commit()

        approval = await service.get_approval(approval_id)

        logger.info(
            "Approval %s rejected by %s: %s",
            approval_id,
            request.user,
            request.reason,
        )

        return ApprovalResponse(
            id=approval.id,
            pipeline_id=approval.pipeline_id,
            step_id=approval.step_id,
            status=approval.status.value,
            requested_at=approval.requested_at.isoformat(),
            responded_at=approval.responded_at.isoformat()
            if approval.responded_at
            else None,
            responded_by=approval.responded_by,
            comment=approval.comment,
        )

    except ApprovalError as e:
        raise HTTPException(status_code=400, detail=str(e))

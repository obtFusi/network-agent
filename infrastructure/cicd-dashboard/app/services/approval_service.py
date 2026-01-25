"""Approval service for managing pipeline approval gates."""

import logging
from datetime import UTC, datetime, timedelta

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import Approval, ApprovalStatus, Pipeline, PipelineStatus, PipelineStep

logger = logging.getLogger(__name__)


class ApprovalError(Exception):
    """Base exception for approval service errors."""

    pass


class ApprovalService:
    """Service for managing approval requests."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def request_approval(self, pipeline_id: str, step_id: str) -> Approval:
        """Create an approval request for a pipeline step.

        Args:
            pipeline_id: Pipeline UUID
            step_id: Step UUID requiring approval

        Returns:
            Created Approval object
        """
        # Verify pipeline and step exist
        pipeline_result = await self.db.execute(
            select(Pipeline).where(Pipeline.id == pipeline_id)
        )
        pipeline = pipeline_result.scalar_one_or_none()
        if not pipeline:
            raise ApprovalError(f"Pipeline {pipeline_id} not found")

        step_result = await self.db.execute(
            select(PipelineStep).where(PipelineStep.id == step_id)
        )
        step = step_result.scalar_one_or_none()
        if not step:
            raise ApprovalError(f"Step {step_id} not found")

        # Check for existing pending approval
        existing_result = await self.db.execute(
            select(Approval).where(
                Approval.pipeline_id == pipeline_id,
                Approval.step_id == step_id,
                Approval.status == ApprovalStatus.PENDING,
            )
        )
        existing = existing_result.scalar_one_or_none()
        if existing:
            logger.info(
                "Returning existing pending approval %s for step %s",
                existing.id,
                step_id,
            )
            return existing

        # Create new approval request
        approval = Approval(
            pipeline_id=pipeline_id,
            step_id=step_id,
        )
        self.db.add(approval)

        # Update pipeline status to waiting approval
        pipeline.status = PipelineStatus.WAITING_APPROVAL
        await self.db.flush()
        await self.db.refresh(approval)

        logger.info(
            "Created approval request %s for pipeline %s step %s",
            approval.id,
            pipeline_id,
            step_id,
        )

        return approval

    async def approve(
        self, approval_id: str, user: str, comment: str | None = None
    ) -> bool:
        """Approve a pending approval request.

        Args:
            approval_id: Approval UUID
            user: Username of the approver
            comment: Optional approval comment

        Returns:
            True if approval was successful
        """
        result = await self.db.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            raise ApprovalError(f"Approval {approval_id} not found")

        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalError(
                f"Approval {approval_id} is not pending (status: {approval.status})"
            )

        # Update approval
        approval.status = ApprovalStatus.APPROVED
        approval.responded_at = datetime.now(UTC)
        approval.responded_by = user
        approval.comment = comment

        # Get the pipeline and update status back to running
        pipeline_result = await self.db.execute(
            select(Pipeline).where(Pipeline.id == approval.pipeline_id)
        )
        pipeline = pipeline_result.scalar_one_or_none()
        if pipeline:
            pipeline.status = PipelineStatus.RUNNING

        logger.info(
            "Approval %s approved by %s for pipeline %s",
            approval_id,
            user,
            approval.pipeline_id,
        )

        return True

    async def reject(
        self, approval_id: str, user: str, reason: str | None = None
    ) -> bool:
        """Reject a pending approval request.

        Args:
            approval_id: Approval UUID
            user: Username of the rejector
            reason: Optional rejection reason

        Returns:
            True if rejection was successful
        """
        result = await self.db.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval:
            raise ApprovalError(f"Approval {approval_id} not found")

        if approval.status != ApprovalStatus.PENDING:
            raise ApprovalError(
                f"Approval {approval_id} is not pending (status: {approval.status})"
            )

        # Update approval
        approval.status = ApprovalStatus.REJECTED
        approval.responded_at = datetime.now(UTC)
        approval.responded_by = user
        approval.comment = reason

        # Get the pipeline and update status to failed
        pipeline_result = await self.db.execute(
            select(Pipeline).where(Pipeline.id == approval.pipeline_id)
        )
        pipeline = pipeline_result.scalar_one_or_none()
        if pipeline:
            pipeline.status = PipelineStatus.FAILED

        # Update the step to failed
        step_result = await self.db.execute(
            select(PipelineStep).where(PipelineStep.id == approval.step_id)
        )
        step = step_result.scalar_one_or_none()
        if step:
            step.status = "failed"
            step.error = f"Rejected by {user}: {reason or 'No reason provided'}"

        logger.info(
            "Approval %s rejected by %s for pipeline %s: %s",
            approval_id,
            user,
            approval.pipeline_id,
            reason,
        )

        return True

    async def get_pending_approvals(self) -> list[Approval]:
        """Get all pending approval requests.

        Returns:
            List of pending Approval objects
        """
        result = await self.db.execute(
            select(Approval)
            .where(Approval.status == ApprovalStatus.PENDING)
            .order_by(Approval.requested_at.desc())
        )
        return list(result.scalars().all())

    async def get_approval(self, approval_id: str) -> Approval | None:
        """Get an approval by ID.

        Args:
            approval_id: Approval UUID

        Returns:
            Approval object or None if not found
        """
        result = await self.db.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        return result.scalar_one_or_none()

    async def check_timeout(self, approval_id: str) -> bool:
        """Check if an approval has timed out.

        Args:
            approval_id: Approval UUID

        Returns:
            True if the approval has timed out
        """
        result = await self.db.execute(
            select(Approval).where(Approval.id == approval_id)
        )
        approval = result.scalar_one_or_none()

        if not approval or approval.status != ApprovalStatus.PENDING:
            return False

        timeout = timedelta(hours=settings.approval_timeout_hours)
        # Handle both naive and aware datetimes (SQLite stores naive)
        requested_at = approval.requested_at
        if requested_at.tzinfo is None:
            requested_at = requested_at.replace(tzinfo=UTC)
        deadline = requested_at + timeout

        if datetime.now(UTC) > deadline:
            # Mark as rejected due to timeout
            approval.status = ApprovalStatus.REJECTED
            approval.responded_at = datetime.now(UTC)
            approval.responded_by = "system"
            approval.comment = (
                f"Timed out after {settings.approval_timeout_hours} hours"
            )

            # Update pipeline status
            pipeline_result = await self.db.execute(
                select(Pipeline).where(Pipeline.id == approval.pipeline_id)
            )
            pipeline = pipeline_result.scalar_one_or_none()
            if pipeline:
                pipeline.status = PipelineStatus.FAILED

            logger.warning(
                "Approval %s timed out for pipeline %s",
                approval_id,
                approval.pipeline_id,
            )

            return True

        return False

    async def get_approvals_for_pipeline(self, pipeline_id: str) -> list[Approval]:
        """Get all approvals for a pipeline.

        Args:
            pipeline_id: Pipeline UUID

        Returns:
            List of Approval objects
        """
        result = await self.db.execute(
            select(Approval)
            .where(Approval.pipeline_id == pipeline_id)
            .order_by(Approval.requested_at.asc())
        )
        return list(result.scalars().all())

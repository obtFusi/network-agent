"""Pipeline executor for orchestrating CI/CD pipelines."""

import asyncio
import logging
from dataclasses import dataclass, field
from datetime import UTC, datetime
from enum import Enum
from typing import Callable

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.config import settings
from app.models import (
    ApprovalStatus,
    Pipeline,
    PipelineStatus,
    PipelineStep,
    StepStatus,
)
from app.services.approval_service import ApprovalService
from app.services.github_client import GitHubClient, WorkflowConclusion, WorkflowStatus

logger = logging.getLogger(__name__)


class StepType(str, Enum):
    """Type of pipeline step."""

    WORKFLOW = "workflow"  # GitHub Actions workflow
    ACTION = "action"  # Custom Python action


class OnFailure(str, Enum):
    """Behavior when a step fails."""

    ABORT = "abort"  # Stop pipeline immediately
    NOTIFY = "notify"  # Continue but notify
    ROLLBACK = "rollback"  # Attempt rollback


@dataclass
class Step:
    """Definition of a pipeline step."""

    name: str
    step_type: StepType = StepType.ACTION
    workflow: str | None = None  # For WORKFLOW type
    job: str | None = None  # Specific job in workflow
    action: Callable | None = None  # For ACTION type
    requires_approval: bool = False
    timeout_minutes: int = 30


@dataclass
class Stage:
    """Definition of a pipeline stage containing multiple steps."""

    name: str
    steps: list[Step] = field(default_factory=list)
    on_failure: OnFailure = OnFailure.ABORT


# Default pipeline stages
PIPELINE_STAGES = [
    Stage(
        name="validate",
        steps=[
            Step("lint", StepType.WORKFLOW, workflow="ci.yml", job="lint"),
            Step("test", StepType.WORKFLOW, workflow="ci.yml", job="test"),
            Step("security", StepType.WORKFLOW, workflow="ci.yml", job="security"),
            Step("docker-build", StepType.WORKFLOW, workflow="ci.yml", job="docker"),
        ],
        on_failure=OnFailure.ABORT,
    ),
    Stage(
        name="review",
        steps=[
            Step("create-pr", StepType.ACTION),
            Step("wait-ci", StepType.ACTION),
            Step("pr-merge", StepType.ACTION, requires_approval=True),
        ],
        on_failure=OnFailure.NOTIFY,
    ),
    Stage(
        name="release",
        steps=[
            Step("create-release", StepType.ACTION, requires_approval=True),
            Step("docker-push", StepType.WORKFLOW, workflow="docker-build.yml"),
            Step("appliance-build", StepType.WORKFLOW, workflow="appliance-build.yml"),
            Step("close-issue", StepType.ACTION),
        ],
        on_failure=OnFailure.ROLLBACK,
    ),
]


class PipelineExecutorError(Exception):
    """Base exception for pipeline executor errors."""

    pass


class PipelineExecutor:
    """Executes pipeline stages and steps."""

    def __init__(
        self,
        db: AsyncSession,
        github: GitHubClient | None = None,
        approval_service: ApprovalService | None = None,
    ):
        self.db = db
        self.github = github or GitHubClient()
        self.approval_service = approval_service or ApprovalService(db)
        self._running_pipelines: dict[str, asyncio.Task] = {}

    async def start_pipeline(self, pipeline_id: str) -> Pipeline:
        """Start executing a pipeline.

        Args:
            pipeline_id: Pipeline UUID to start

        Returns:
            Updated Pipeline object
        """
        result = await self.db.execute(
            select(Pipeline).where(Pipeline.id == pipeline_id)
        )
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            raise PipelineExecutorError(f"Pipeline {pipeline_id} not found")

        if pipeline.status not in (PipelineStatus.PENDING, PipelineStatus.FAILED):
            raise PipelineExecutorError(
                f"Pipeline {pipeline_id} cannot be started (status: {pipeline.status})"
            )

        # Create steps for all stages
        await self._create_pipeline_steps(pipeline)

        # Update pipeline status
        pipeline.status = PipelineStatus.RUNNING

        logger.info("Starting pipeline %s for %s", pipeline_id, pipeline.repo)

        # Start execution in background task
        task = asyncio.create_task(self._execute_pipeline(pipeline_id))
        self._running_pipelines[pipeline_id] = task

        return pipeline

    async def abort_pipeline(self, pipeline_id: str) -> Pipeline:
        """Abort a running pipeline.

        Args:
            pipeline_id: Pipeline UUID to abort

        Returns:
            Updated Pipeline object
        """
        result = await self.db.execute(
            select(Pipeline).where(Pipeline.id == pipeline_id)
        )
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            raise PipelineExecutorError(f"Pipeline {pipeline_id} not found")

        # Cancel running task if exists
        if pipeline_id in self._running_pipelines:
            self._running_pipelines[pipeline_id].cancel()
            del self._running_pipelines[pipeline_id]

        # Update pipeline status
        pipeline.status = PipelineStatus.ABORTED
        pipeline.completed_at = datetime.now(UTC)

        # Mark any running steps as skipped
        steps_result = await self.db.execute(
            select(PipelineStep).where(
                PipelineStep.pipeline_id == pipeline_id,
                PipelineStep.status.in_([StepStatus.PENDING, StepStatus.RUNNING]),
            )
        )
        for step in steps_result.scalars():
            step.status = StepStatus.SKIPPED

        logger.info("Aborted pipeline %s", pipeline_id)

        return pipeline

    async def retry_step(self, pipeline_id: str, step_id: str) -> PipelineStep:
        """Retry a failed step.

        Args:
            pipeline_id: Pipeline UUID
            step_id: Step UUID to retry

        Returns:
            Updated PipelineStep object
        """
        step_result = await self.db.execute(
            select(PipelineStep).where(
                PipelineStep.id == step_id,
                PipelineStep.pipeline_id == pipeline_id,
            )
        )
        step = step_result.scalar_one_or_none()

        if not step:
            raise PipelineExecutorError(f"Step {step_id} not found")

        if step.status != StepStatus.FAILED:
            raise PipelineExecutorError(
                f"Step {step_id} cannot be retried (status: {step.status})"
            )

        # Reset step status
        step.status = StepStatus.PENDING
        step.error = None
        step.started_at = None
        step.completed_at = None

        # Update pipeline status if it was failed
        pipeline_result = await self.db.execute(
            select(Pipeline).where(Pipeline.id == pipeline_id)
        )
        pipeline = pipeline_result.scalar_one_or_none()
        if pipeline and pipeline.status == PipelineStatus.FAILED:
            pipeline.status = PipelineStatus.RUNNING

        logger.info("Reset step %s for retry in pipeline %s", step_id, pipeline_id)

        return step

    async def _create_pipeline_steps(self, pipeline: Pipeline) -> None:
        """Create all steps for a pipeline based on stage definitions."""
        for stage in PIPELINE_STAGES:
            for step_def in stage.steps:
                step = PipelineStep(
                    pipeline_id=pipeline.id,
                    name=step_def.name,
                    stage=stage.name,
                    requires_approval=step_def.requires_approval,
                )
                self.db.add(step)

        await self.db.flush()
        logger.info("Created steps for pipeline %s", pipeline.id)

    async def _execute_pipeline(self, pipeline_id: str) -> None:
        """Execute a pipeline through all stages.

        This runs as a background task and handles the sequential
        execution of all stages and steps.
        """
        try:
            for stage in PIPELINE_STAGES:
                await self._execute_stage(pipeline_id, stage)

            # Pipeline completed successfully
            result = await self.db.execute(
                select(Pipeline).where(Pipeline.id == pipeline_id)
            )
            pipeline = result.scalar_one_or_none()
            if pipeline:
                pipeline.status = PipelineStatus.COMPLETED
                pipeline.completed_at = datetime.now(UTC)
                await self.db.commit()

            logger.info("Pipeline %s completed successfully", pipeline_id)

        except asyncio.CancelledError:
            logger.info("Pipeline %s was cancelled", pipeline_id)
            raise

        except Exception:
            logger.exception("Pipeline %s failed with error", pipeline_id)

            # Update pipeline status
            result = await self.db.execute(
                select(Pipeline).where(Pipeline.id == pipeline_id)
            )
            pipeline = result.scalar_one_or_none()
            if pipeline:
                pipeline.status = PipelineStatus.FAILED
                await self.db.commit()

        finally:
            if pipeline_id in self._running_pipelines:
                del self._running_pipelines[pipeline_id]

    async def _execute_stage(self, pipeline_id: str, stage: Stage) -> None:
        """Execute a single stage of the pipeline."""
        logger.info("Starting stage '%s' for pipeline %s", stage.name, pipeline_id)

        for step_def in stage.steps:
            try:
                await self._execute_step(pipeline_id, stage, step_def)
            except Exception as e:
                logger.error(
                    "Step '%s' failed in pipeline %s: %s",
                    step_def.name,
                    pipeline_id,
                    e,
                )

                if stage.on_failure == OnFailure.ABORT:
                    raise
                elif stage.on_failure == OnFailure.ROLLBACK:
                    # TODO: Implement rollback logic
                    logger.warning(
                        "Rollback requested but not yet implemented for stage %s",
                        stage.name,
                    )
                    raise
                # NOTIFY: continue to next step

    async def _execute_step(
        self, pipeline_id: str, stage: Stage, step_def: Step
    ) -> None:
        """Execute a single step in the pipeline."""
        # Get the step from database
        step_result = await self.db.execute(
            select(PipelineStep).where(
                PipelineStep.pipeline_id == pipeline_id,
                PipelineStep.name == step_def.name,
                PipelineStep.stage == stage.name,
            )
        )
        step = step_result.scalar_one_or_none()

        if not step:
            logger.warning(
                "Step '%s' not found for pipeline %s, skipping",
                step_def.name,
                pipeline_id,
            )
            return

        # Skip if already completed
        if step.status == StepStatus.COMPLETED:
            logger.info(
                "Step '%s' already completed, skipping",
                step_def.name,
            )
            return

        # Check if approval is required
        if step_def.requires_approval:
            await self._wait_for_approval(pipeline_id, step)

        # Mark step as running
        step.status = StepStatus.RUNNING
        step.started_at = datetime.now(UTC)
        await self.db.commit()

        try:
            # Execute based on step type
            if step_def.step_type == StepType.WORKFLOW:
                await self._execute_workflow_step(pipeline_id, step, step_def)
            else:
                await self._execute_action_step(pipeline_id, step, step_def)

            # Mark step as completed
            step.status = StepStatus.COMPLETED
            step.completed_at = datetime.now(UTC)
            await self.db.commit()

            logger.info(
                "Step '%s' completed for pipeline %s",
                step_def.name,
                pipeline_id,
            )

        except Exception as e:
            step.status = StepStatus.FAILED
            step.completed_at = datetime.now(UTC)
            step.error = str(e)
            await self.db.commit()
            raise

    async def _wait_for_approval(self, pipeline_id: str, step: PipelineStep) -> None:
        """Wait for approval before executing a step."""
        logger.info(
            "Waiting for approval for step '%s' in pipeline %s",
            step.name,
            pipeline_id,
        )

        approval = await self.approval_service.request_approval(pipeline_id, step.id)
        await self.db.commit()

        # Poll for approval status
        while True:
            # Refresh approval from database
            result = await self.db.execute(
                select(Pipeline).where(Pipeline.id == pipeline_id)
            )
            pipeline = result.scalar_one_or_none()

            if not pipeline or pipeline.status == PipelineStatus.ABORTED:
                raise PipelineExecutorError("Pipeline was aborted")

            # Check if approval was granted/rejected
            approval_result = await self.db.execute(
                select(approval.__class__).where(approval.__class__.id == approval.id)
            )
            approval = approval_result.scalar_one_or_none()

            if approval.status == ApprovalStatus.APPROVED:
                logger.info(
                    "Approval granted for step '%s' by %s",
                    step.name,
                    approval.responded_by,
                )
                return

            if approval.status == ApprovalStatus.REJECTED:
                raise PipelineExecutorError(
                    f"Approval rejected by {approval.responded_by}: {approval.comment}"
                )

            # Check for timeout
            if await self.approval_service.check_timeout(approval.id):
                await self.db.commit()
                raise PipelineExecutorError(
                    f"Approval timed out after {settings.approval_timeout_hours} hours"
                )

            # Wait before checking again
            await asyncio.sleep(10)

    async def _execute_workflow_step(
        self, pipeline_id: str, step: PipelineStep, step_def: Step
    ) -> None:
        """Execute a GitHub Actions workflow step."""
        result = await self.db.execute(
            select(Pipeline).where(Pipeline.id == pipeline_id)
        )
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            raise PipelineExecutorError(f"Pipeline {pipeline_id} not found")

        # Trigger the workflow
        logger.info(
            "Triggering workflow %s for pipeline %s",
            step_def.workflow,
            pipeline_id,
        )

        await self.github.trigger_workflow(
            repo=pipeline.repo,
            workflow=step_def.workflow,
            ref=pipeline.ref,
        )

        # Poll for workflow completion
        # Note: We need to find the workflow run that was just triggered
        # This is a simplified implementation - in production you'd need
        # more sophisticated run matching
        await asyncio.sleep(5)  # Wait for workflow to start

        timeout = step_def.timeout_minutes * 60
        start_time = datetime.now(UTC)

        while True:
            # Check timeout
            elapsed = (datetime.now(UTC) - start_time).total_seconds()
            if elapsed > timeout:
                raise PipelineExecutorError(
                    f"Workflow {step_def.workflow} timed out after {step_def.timeout_minutes} minutes"
                )

            # Get latest workflow runs
            runs = await self.github.list_workflow_runs(
                repo=pipeline.repo,
                workflow=step_def.workflow,
                branch=pipeline.ref.replace("refs/heads/", ""),
                per_page=5,
            )

            if runs:
                latest_run = runs[0]

                if latest_run.status == WorkflowStatus.COMPLETED:
                    if latest_run.conclusion == WorkflowConclusion.SUCCESS:
                        step.logs = f"Workflow completed: {latest_run.html_url}"
                        return
                    else:
                        raise PipelineExecutorError(
                            f"Workflow {step_def.workflow} failed with conclusion: {latest_run.conclusion}"
                        )

            await asyncio.sleep(30)  # Poll every 30 seconds

    async def _execute_action_step(
        self, pipeline_id: str, step: PipelineStep, step_def: Step
    ) -> None:
        """Execute a custom action step."""
        result = await self.db.execute(
            select(Pipeline).where(Pipeline.id == pipeline_id)
        )
        pipeline = result.scalar_one_or_none()

        if not pipeline:
            raise PipelineExecutorError(f"Pipeline {pipeline_id} not found")

        # Map step names to actions
        action_map = {
            "create-pr": self._action_create_pr,
            "wait-ci": self._action_wait_ci,
            "pr-merge": self._action_merge_pr,
            "create-release": self._action_create_release,
            "close-issue": self._action_close_issue,
        }

        action = action_map.get(step_def.name)
        if action:
            await action(pipeline, step)
        else:
            logger.warning("No action defined for step '%s', skipping", step_def.name)

    async def _action_create_pr(self, pipeline: Pipeline, step: PipelineStep) -> None:
        """Create a pull request for the pipeline."""
        trigger_data = pipeline.trigger_data or {}
        issue_number = trigger_data.get("issue_number")
        issue_title = trigger_data.get("issue_title", "")

        title = f"feat: {issue_title}" if issue_title else f"Pipeline {pipeline.id[:8]}"
        body = (
            f"Automated PR from CI/CD pipeline.\n\nCloses #{issue_number}"
            if issue_number
            else "Automated PR from CI/CD pipeline."
        )

        branch = pipeline.ref.replace("refs/heads/", "")
        pr = await self.github.create_pull_request(
            repo=pipeline.repo,
            title=title,
            body=body,
            head=branch,
        )

        step.logs = f"Created PR #{pr.number}: {pr.html_url}"

    async def _action_wait_ci(self, pipeline: Pipeline, step: PipelineStep) -> None:
        """Wait for CI checks to pass on the PR."""
        # For now, just wait a bit - in production this would poll PR status
        await asyncio.sleep(5)
        step.logs = "CI checks passed (simulated)"

    async def _action_merge_pr(self, pipeline: Pipeline, step: PipelineStep) -> None:
        """Merge the pull request."""
        trigger_data = pipeline.trigger_data or {}
        pr_number = trigger_data.get("pr_number")

        if pr_number:
            await self.github.merge_pull_request(
                repo=pipeline.repo,
                pr_number=pr_number,
            )
            step.logs = f"Merged PR #{pr_number}"
        else:
            step.logs = "No PR to merge"

    async def _action_create_release(
        self, pipeline: Pipeline, step: PipelineStep
    ) -> None:
        """Create a GitHub release."""
        version = pipeline.version or "0.0.0"
        tag = f"v{version}"

        release = await self.github.create_release(
            repo=pipeline.repo,
            tag=tag,
            name=f"Release {version}",
            body=f"Release created by CI/CD pipeline {pipeline.id[:8]}",
        )

        step.logs = f"Created release {release.tag_name}: {release.html_url}"

    async def _action_close_issue(self, pipeline: Pipeline, step: PipelineStep) -> None:
        """Close the triggering issue."""
        trigger_data = pipeline.trigger_data or {}
        issue_number = trigger_data.get("issue_number")

        if issue_number:
            await self.github.close_issue(
                repo=pipeline.repo,
                issue_number=issue_number,
            )
            step.logs = f"Closed issue #{issue_number}"
        else:
            step.logs = "No issue to close"

    def get_running_pipelines(self) -> list[str]:
        """Get list of currently running pipeline IDs."""
        return list(self._running_pipelines.keys())

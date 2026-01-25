"""GitHub webhook event handler service."""

import hashlib
import hmac
import logging
from datetime import UTC, datetime

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import Pipeline, PipelineStatus, WebhookEvent

logger = logging.getLogger(__name__)


def verify_github_signature(payload: bytes, signature: str, secret: str) -> bool:
    """Verify GitHub webhook signature (HMAC-SHA256).

    Args:
        payload: Raw request body
        signature: X-Hub-Signature-256 header value
        secret: Webhook secret from configuration

    Returns:
        True if signature is valid, False otherwise
    """
    if not signature or not signature.startswith("sha256="):
        return False

    expected = (
        "sha256="
        + hmac.new(
            secret.encode(),
            payload,
            hashlib.sha256,
        ).hexdigest()
    )

    return hmac.compare_digest(expected, signature)


class WebhookHandler:
    """Handles GitHub webhook events and creates pipelines."""

    def __init__(self, db: AsyncSession):
        self.db = db

    async def is_duplicate(self, delivery_id: str) -> bool:
        """Check if event with this delivery ID already exists."""
        result = await self.db.execute(
            select(WebhookEvent).where(WebhookEvent.github_delivery_id == delivery_id)
        )
        return result.scalar_one_or_none() is not None

    async def store_event(
        self,
        delivery_id: str,
        event_type: str,
        action: str | None,
        repo: str,
        payload: dict,
    ) -> WebhookEvent:
        """Store webhook event in database."""
        event = WebhookEvent(
            github_delivery_id=delivery_id,
            event_type=event_type,
            action=action,
            repo=repo,
            payload=payload,
        )
        self.db.add(event)
        await self.db.flush()
        await self.db.refresh(event)
        return event

    async def process_event(self, event: WebhookEvent) -> Pipeline | None:
        """Process webhook event and optionally create a pipeline.

        Args:
            event: The webhook event to process

        Returns:
            Created Pipeline if event triggers one, None otherwise
        """
        pipeline = None

        try:
            # Handle different event types
            if event.event_type == "issues" and event.action == "labeled":
                pipeline = await self._handle_issue_labeled(event)
            elif event.event_type == "pull_request" and event.action == "closed":
                pipeline = await self._handle_pr_closed(event)
            elif event.event_type == "workflow_run" and event.action == "completed":
                await self._handle_workflow_completed(event)
            elif event.event_type == "release" and event.action == "published":
                pipeline = await self._handle_release_published(event)

            # Mark event as processed
            event.processed = True
            event.processed_at = datetime.now(UTC)
            if pipeline:
                event.pipeline_id = pipeline.id

        except Exception as e:
            logger.exception("Error processing webhook event %s", event.id)
            event.error = str(e)

        return pipeline

    async def _handle_issue_labeled(self, event: WebhookEvent) -> Pipeline | None:
        """Handle issue labeled event.

        Creates a new pipeline if the label is 'status:ready'.
        """
        payload = event.payload
        label = payload.get("label", {})
        label_name = label.get("name", "")

        if label_name != "status:ready":
            logger.debug("Ignoring label %s (not status:ready)", label_name)
            return None

        issue = payload.get("issue", {})
        issue_number = issue.get("number")
        issue_title = issue.get("title", "")

        logger.info(
            "Creating pipeline for issue #%s: %s",
            issue_number,
            issue_title,
        )

        pipeline = Pipeline(
            repo=event.repo,
            ref="main",  # Default branch, could be configured
            trigger="issue_labeled",
            trigger_data={
                "issue_number": issue_number,
                "issue_title": issue_title,
                "label": label_name,
            },
        )
        self.db.add(pipeline)
        await self.db.flush()
        await self.db.refresh(pipeline)

        return pipeline

    async def _handle_pr_closed(self, event: WebhookEvent) -> Pipeline | None:
        """Handle pull request closed event.

        Only processes merged PRs.
        """
        payload = event.payload
        pr = payload.get("pull_request", {})

        if not pr.get("merged"):
            logger.debug("Ignoring unmerged PR close")
            return None

        pr_number = pr.get("number")
        pr_title = pr.get("title", "")
        merge_commit = pr.get("merge_commit_sha", "")[:7]

        logger.info(
            "PR #%s merged: %s (commit: %s)",
            pr_number,
            pr_title,
            merge_commit,
        )

        pipeline = Pipeline(
            repo=event.repo,
            ref=f"refs/pull/{pr_number}/merge",
            trigger="pr_merged",
            trigger_data={
                "pr_number": pr_number,
                "pr_title": pr_title,
                "merge_commit": merge_commit,
            },
        )
        self.db.add(pipeline)
        await self.db.flush()
        await self.db.refresh(pipeline)

        return pipeline

    async def _handle_workflow_completed(self, event: WebhookEvent) -> None:
        """Handle workflow run completed event.

        Updates existing pipeline step status.
        """
        payload = event.payload
        workflow_run = payload.get("workflow_run", {})
        conclusion = workflow_run.get("conclusion")
        workflow_name = workflow_run.get("name", "")

        logger.info(
            "Workflow '%s' completed with conclusion: %s",
            workflow_name,
            conclusion,
        )
        # Pipeline step update will be implemented in #75

    async def _handle_release_published(self, event: WebhookEvent) -> Pipeline | None:
        """Handle release published event."""
        payload = event.payload
        release = payload.get("release", {})
        tag_name = release.get("tag_name", "")
        release_name = release.get("name", "")

        logger.info(
            "Release published: %s (%s)",
            release_name,
            tag_name,
        )

        # Extract version from tag (remove 'v' prefix if present)
        version = tag_name.lstrip("v") if tag_name.startswith("v") else tag_name

        pipeline = Pipeline(
            repo=event.repo,
            ref=f"refs/tags/{tag_name}",
            version=version,
            status=PipelineStatus.COMPLETED,
            trigger="release_published",
            trigger_data={
                "tag_name": tag_name,
                "release_name": release_name,
                "release_id": release.get("id"),
            },
        )
        self.db.add(pipeline)
        await self.db.flush()
        await self.db.refresh(pipeline)

        return pipeline

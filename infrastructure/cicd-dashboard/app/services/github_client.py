"""GitHub API client for CI/CD Dashboard."""

import logging
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

import httpx

from app.config import settings

logger = logging.getLogger(__name__)


class WorkflowStatus(str, Enum):
    """Status of a GitHub workflow run."""

    QUEUED = "queued"
    IN_PROGRESS = "in_progress"
    COMPLETED = "completed"


class WorkflowConclusion(str, Enum):
    """Conclusion of a completed workflow run."""

    SUCCESS = "success"
    FAILURE = "failure"
    CANCELLED = "cancelled"
    SKIPPED = "skipped"
    TIMED_OUT = "timed_out"
    ACTION_REQUIRED = "action_required"


@dataclass
class WorkflowRun:
    """Represents a GitHub workflow run."""

    id: int
    name: str
    status: WorkflowStatus
    conclusion: WorkflowConclusion | None
    html_url: str
    created_at: datetime
    updated_at: datetime


@dataclass
class PullRequest:
    """Represents a GitHub pull request."""

    number: int
    title: str
    html_url: str
    state: str
    merged: bool


@dataclass
class Release:
    """Represents a GitHub release."""

    id: int
    tag_name: str
    name: str
    html_url: str


class GitHubClientError(Exception):
    """Base exception for GitHub client errors."""

    pass


class GitHubClient:
    """Async client for GitHub API operations."""

    BASE_URL = "https://api.github.com"

    def __init__(self, token: str | None = None):
        self.token = token or settings.github_token
        if not self.token:
            logger.warning("No GitHub token configured - API calls will be limited")

    def _get_headers(self) -> dict[str, str]:
        """Get headers for API requests."""
        headers = {
            "Accept": "application/vnd.github+json",
            "X-GitHub-Api-Version": "2022-11-28",
        }
        if self.token:
            headers["Authorization"] = f"Bearer {self.token}"
        return headers

    async def _request(
        self,
        method: str,
        endpoint: str,
        json: dict | None = None,
        params: dict | None = None,
    ) -> dict:
        """Make an API request to GitHub."""
        url = f"{self.BASE_URL}{endpoint}"

        async with httpx.AsyncClient() as client:
            response = await client.request(
                method,
                url,
                headers=self._get_headers(),
                json=json,
                params=params,
                timeout=30.0,
            )

            if response.status_code >= 400:
                logger.error(
                    "GitHub API error: %s %s -> %s %s",
                    method,
                    endpoint,
                    response.status_code,
                    response.text[:200],
                )
                raise GitHubClientError(
                    f"GitHub API error: {response.status_code} - {response.text[:200]}"
                )

            return response.json() if response.text else {}

    async def create_branch(
        self, repo: str, branch: str, from_ref: str = "main"
    ) -> str:
        """Create a new branch from a reference.

        Args:
            repo: Repository in owner/name format
            branch: Name of the new branch
            from_ref: Reference to branch from (default: main)

        Returns:
            SHA of the created branch
        """
        # Get SHA of the source reference
        ref_data = await self._request("GET", f"/repos/{repo}/git/ref/heads/{from_ref}")
        sha = ref_data["object"]["sha"]

        # Create the new branch
        await self._request(
            "POST",
            f"/repos/{repo}/git/refs",
            json={"ref": f"refs/heads/{branch}", "sha": sha},
        )

        logger.info("Created branch %s from %s in %s", branch, from_ref, repo)
        return sha

    async def create_pull_request(
        self,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> PullRequest:
        """Create a pull request.

        Args:
            repo: Repository in owner/name format
            title: PR title
            body: PR description
            head: Branch containing changes
            base: Target branch (default: main)

        Returns:
            Created PullRequest object
        """
        data = await self._request(
            "POST",
            f"/repos/{repo}/pulls",
            json={
                "title": title,
                "body": body,
                "head": head,
                "base": base,
            },
        )

        pr = PullRequest(
            number=data["number"],
            title=data["title"],
            html_url=data["html_url"],
            state=data["state"],
            merged=data.get("merged", False),
        )

        logger.info("Created PR #%s: %s", pr.number, pr.title)
        return pr

    async def merge_pull_request(
        self,
        repo: str,
        pr_number: int,
        merge_method: str = "merge",
        commit_title: str | None = None,
    ) -> bool:
        """Merge a pull request.

        Args:
            repo: Repository in owner/name format
            pr_number: PR number to merge
            merge_method: Merge method (merge, squash, rebase)
            commit_title: Optional commit title for squash merges

        Returns:
            True if merge was successful
        """
        json_data: dict = {"merge_method": merge_method}
        if commit_title:
            json_data["commit_title"] = commit_title

        await self._request(
            "PUT",
            f"/repos/{repo}/pulls/{pr_number}/merge",
            json=json_data,
        )

        logger.info("Merged PR #%s in %s using %s", pr_number, repo, merge_method)
        return True

    async def create_release(
        self,
        repo: str,
        tag: str,
        name: str,
        body: str,
        prerelease: bool = False,
        generate_release_notes: bool = True,
    ) -> Release:
        """Create a GitHub release.

        Args:
            repo: Repository in owner/name format
            tag: Tag name for the release
            name: Release title
            body: Release description
            prerelease: Whether this is a prerelease
            generate_release_notes: Auto-generate release notes

        Returns:
            Created Release object
        """
        data = await self._request(
            "POST",
            f"/repos/{repo}/releases",
            json={
                "tag_name": tag,
                "name": name,
                "body": body,
                "prerelease": prerelease,
                "generate_release_notes": generate_release_notes,
            },
        )

        release = Release(
            id=data["id"],
            tag_name=data["tag_name"],
            name=data["name"],
            html_url=data["html_url"],
        )

        logger.info("Created release %s: %s", release.tag_name, release.name)
        return release

    async def trigger_workflow(
        self,
        repo: str,
        workflow: str,
        ref: str = "main",
        inputs: dict | None = None,
    ) -> int | None:
        """Trigger a workflow dispatch event.

        Args:
            repo: Repository in owner/name format
            workflow: Workflow file name (e.g., ci.yml)
            ref: Git reference to run the workflow on
            inputs: Optional workflow inputs

        Returns:
            Workflow run ID if available, None otherwise
        """
        await self._request(
            "POST",
            f"/repos/{repo}/actions/workflows/{workflow}/dispatches",
            json={"ref": ref, "inputs": inputs or {}},
        )

        logger.info("Triggered workflow %s on %s@%s", workflow, repo, ref)

        # Workflow dispatch doesn't return run ID directly
        # We'd need to poll for the newly created run
        return None

    async def get_workflow_run(self, repo: str, run_id: int) -> WorkflowRun:
        """Get workflow run status.

        Args:
            repo: Repository in owner/name format
            run_id: Workflow run ID

        Returns:
            WorkflowRun object with current status
        """
        data = await self._request("GET", f"/repos/{repo}/actions/runs/{run_id}")

        return WorkflowRun(
            id=data["id"],
            name=data["name"],
            status=WorkflowStatus(data["status"]),
            conclusion=WorkflowConclusion(data["conclusion"])
            if data.get("conclusion")
            else None,
            html_url=data["html_url"],
            created_at=datetime.fromisoformat(
                data["created_at"].replace("Z", "+00:00")
            ),
            updated_at=datetime.fromisoformat(
                data["updated_at"].replace("Z", "+00:00")
            ),
        )

    async def list_workflow_runs(
        self,
        repo: str,
        workflow: str | None = None,
        branch: str | None = None,
        status: str | None = None,
        per_page: int = 10,
    ) -> list[WorkflowRun]:
        """List workflow runs.

        Args:
            repo: Repository in owner/name format
            workflow: Filter by workflow file name
            branch: Filter by branch
            status: Filter by status
            per_page: Results per page

        Returns:
            List of WorkflowRun objects
        """
        params: dict = {"per_page": per_page}
        if branch:
            params["branch"] = branch
        if status:
            params["status"] = status

        endpoint = f"/repos/{repo}/actions/runs"
        if workflow:
            endpoint = f"/repos/{repo}/actions/workflows/{workflow}/runs"

        data = await self._request("GET", endpoint, params=params)

        runs = []
        for run_data in data.get("workflow_runs", []):
            runs.append(
                WorkflowRun(
                    id=run_data["id"],
                    name=run_data["name"],
                    status=WorkflowStatus(run_data["status"]),
                    conclusion=WorkflowConclusion(run_data["conclusion"])
                    if run_data.get("conclusion")
                    else None,
                    html_url=run_data["html_url"],
                    created_at=datetime.fromisoformat(
                        run_data["created_at"].replace("Z", "+00:00")
                    ),
                    updated_at=datetime.fromisoformat(
                        run_data["updated_at"].replace("Z", "+00:00")
                    ),
                )
            )

        return runs

    async def close_issue(self, repo: str, issue_number: int) -> bool:
        """Close an issue.

        Args:
            repo: Repository in owner/name format
            issue_number: Issue number to close

        Returns:
            True if close was successful
        """
        await self._request(
            "PATCH",
            f"/repos/{repo}/issues/{issue_number}",
            json={"state": "closed"},
        )

        logger.info("Closed issue #%s in %s", issue_number, repo)
        return True

    async def add_issue_comment(self, repo: str, issue_number: int, body: str) -> int:
        """Add a comment to an issue or PR.

        Args:
            repo: Repository in owner/name format
            issue_number: Issue/PR number
            body: Comment body

        Returns:
            Comment ID
        """
        data = await self._request(
            "POST",
            f"/repos/{repo}/issues/{issue_number}/comments",
            json={"body": body},
        )

        logger.info("Added comment to #%s in %s", issue_number, repo)
        return data["id"]

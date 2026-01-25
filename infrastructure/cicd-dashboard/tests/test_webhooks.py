"""Tests for webhook API endpoints."""

import hashlib
import hmac
import json
from unittest.mock import patch

import pytest


def generate_signature(payload: dict, secret: str) -> str:
    """Generate a valid GitHub webhook signature."""
    body = json.dumps(payload).encode()
    signature = hmac.new(secret.encode(), body, hashlib.sha256).hexdigest()
    return f"sha256={signature}"


@pytest.mark.asyncio
async def test_webhook_missing_signature(client):
    """Test that missing signature is rejected when secret is configured."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = "test-secret"

        response = await client.post(
            "/api/v1/webhooks/github",
            json={"action": "test"},
            headers={
                "X-GitHub-Event": "ping",
                "X-GitHub-Delivery": "test-delivery-id",
            },
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Missing signature"


@pytest.mark.asyncio
async def test_webhook_invalid_signature(client):
    """Test that invalid signature is rejected."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = "test-secret"

        response = await client.post(
            "/api/v1/webhooks/github",
            json={"action": "test"},
            headers={
                "X-GitHub-Event": "ping",
                "X-GitHub-Delivery": "test-delivery-id",
                "X-Hub-Signature-256": "sha256=invalid",
            },
        )
        assert response.status_code == 401
        assert response.json()["detail"] == "Invalid signature"


@pytest.mark.asyncio
async def test_webhook_no_secret_configured(client):
    """Test that webhooks are accepted when no secret is configured."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = ""

        payload = {
            "action": "ping",
            "repository": {"full_name": "test/repo"},
        }
        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "ping",
                "X-GitHub-Delivery": "test-delivery-001",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert "event_id" in data


@pytest.mark.asyncio
async def test_webhook_duplicate_ignored(client):
    """Test that duplicate deliveries are ignored."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = ""

        payload = {
            "action": "test",
            "repository": {"full_name": "test/repo"},
        }

        # First request
        response1 = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "ping",
                "X-GitHub-Delivery": "duplicate-test-id",
            },
        )
        assert response1.status_code == 200
        assert response1.json()["status"] == "processed"

        # Second request with same delivery ID
        response2 = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "ping",
                "X-GitHub-Delivery": "duplicate-test-id",
            },
        )
        assert response2.status_code == 200
        assert response2.json()["status"] == "ignored"
        assert response2.json()["reason"] == "duplicate"


@pytest.mark.asyncio
async def test_webhook_issue_labeled_status_ready(client):
    """Test that issue labeled with status:ready creates a pipeline."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = ""

        payload = {
            "action": "labeled",
            "label": {"name": "status:ready"},
            "issue": {
                "number": 42,
                "title": "Test Issue",
            },
            "repository": {"full_name": "obtFusi/network-agent"},
        }

        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": "issue-labeled-test",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["pipeline_id"] is not None

        # Verify pipeline was created
        pipeline_response = await client.get(f"/api/v1/pipelines/{data['pipeline_id']}")
        assert pipeline_response.status_code == 200
        pipeline = pipeline_response.json()
        assert pipeline["repo"] == "obtFusi/network-agent"
        assert pipeline["trigger"] == "issue_labeled"


@pytest.mark.asyncio
async def test_webhook_issue_labeled_other_label(client):
    """Test that issue labeled with other labels does not create a pipeline."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = ""

        payload = {
            "action": "labeled",
            "label": {"name": "type:bug"},
            "issue": {
                "number": 43,
                "title": "Bug Issue",
            },
            "repository": {"full_name": "test/repo"},
        }

        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "issues",
                "X-GitHub-Delivery": "issue-other-label-test",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["pipeline_id"] is None


@pytest.mark.asyncio
async def test_webhook_pr_merged(client):
    """Test that merged PR creates a pipeline."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = ""

        payload = {
            "action": "closed",
            "pull_request": {
                "number": 123,
                "title": "feat: Add new feature",
                "merged": True,
                "merge_commit_sha": "abc1234567890",
            },
            "repository": {"full_name": "obtFusi/network-agent"},
        }

        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "pr-merged-test",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["pipeline_id"] is not None


@pytest.mark.asyncio
async def test_webhook_pr_closed_not_merged(client):
    """Test that closed but not merged PR does not create a pipeline."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = ""

        payload = {
            "action": "closed",
            "pull_request": {
                "number": 124,
                "title": "Rejected PR",
                "merged": False,
            },
            "repository": {"full_name": "test/repo"},
        }

        response = await client.post(
            "/api/v1/webhooks/github",
            json=payload,
            headers={
                "X-GitHub-Event": "pull_request",
                "X-GitHub-Delivery": "pr-closed-not-merged-test",
            },
        )
        assert response.status_code == 200
        data = response.json()
        assert data["status"] == "processed"
        assert data["pipeline_id"] is None


@pytest.mark.asyncio
async def test_list_webhook_events(client):
    """Test listing webhook events."""
    with patch("app.api.webhooks.settings") as mock_settings:
        mock_settings.github_webhook_secret = ""

        # Create some events
        for i in range(3):
            await client.post(
                "/api/v1/webhooks/github",
                json={"action": "test", "repository": {"full_name": "test/repo"}},
                headers={
                    "X-GitHub-Event": "ping",
                    "X-GitHub-Delivery": f"list-test-{i}",
                },
            )

        # List events
        response = await client.get("/api/v1/webhooks/events")
        assert response.status_code == 200
        events = response.json()
        assert len(events) >= 3


@pytest.mark.asyncio
async def test_get_webhook_event_not_found(client):
    """Test getting non-existent webhook event returns 404."""
    response = await client.get("/api/v1/webhooks/events/non-existent-id")
    assert response.status_code == 404

"""Tests for tools/web/web_search.py"""

import os
from unittest.mock import patch, MagicMock
import pytest
from tools.web.web_search import WebSearchTool


@pytest.fixture
def mock_searxng_url():
    """Set SEARXNG_URL for tests."""
    with patch.dict(os.environ, {"SEARXNG_URL": "http://localhost:8080"}):
        yield


@pytest.fixture
def mock_requests_get():
    """Mock requests.get for SearXNG API."""
    with patch("tools.web.web_search.requests.get") as mock:
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "results": [
                {
                    "title": "Test Result 1",
                    "url": "https://example.com/1",
                    "content": "This is test content 1",
                },
                {
                    "title": "Test Result 2",
                    "url": "https://example.com/2",
                    "content": "This is test content 2",
                },
            ]
        }
        mock.return_value = mock_response
        yield mock


class TestWebSearchTool:
    """Tests for WebSearchTool."""

    def setup_method(self):
        """Clear env var for clean state."""
        if "SEARXNG_URL" in os.environ:
            del os.environ["SEARXNG_URL"]

    def test_name(self):
        """Test tool name."""
        tool = WebSearchTool()
        assert tool.name == "web_search"

    def test_description_mentions_search(self):
        """Test tool description mentions search."""
        tool = WebSearchTool()
        assert "search" in tool.description.lower()

    def test_parameters_has_query(self):
        """Test parameters include query as required."""
        tool = WebSearchTool()
        assert "query" in tool.parameters["properties"]
        assert "query" in tool.parameters["required"]

    def test_parameters_has_max_results(self):
        """Test parameters include max_results."""
        tool = WebSearchTool()
        assert "max_results" in tool.parameters["properties"]

    def test_parameters_has_categories(self):
        """Test parameters include categories."""
        tool = WebSearchTool()
        assert "categories" in tool.parameters["properties"]

    def test_missing_searxng_url_returns_error(self):
        """Test that missing SEARXNG_URL returns helpful error."""
        tool = WebSearchTool()
        result = tool.execute(query="test")
        assert "Error" in result
        assert "SEARXNG_URL" in result

    def test_successful_search(self, mock_searxng_url, mock_requests_get):
        """Test successful search returns formatted results."""
        tool = WebSearchTool()
        result = tool.execute(query="test query")
        assert "Web Search" in result
        assert "Test Result 1" in result
        assert "example.com" in result

    def test_empty_results(self, mock_searxng_url, mock_requests_get):
        """Test empty results returns appropriate message."""
        mock_requests_get.return_value.json.return_value = {"results": []}
        tool = WebSearchTool()
        result = tool.execute(query="obscure query")
        assert "No results found" in result

    def test_max_results_limits_output(self, mock_searxng_url, mock_requests_get):
        """Test max_results parameter limits output."""
        tool = WebSearchTool()
        result = tool.execute(query="test", max_results=1)
        assert "Test Result 1" in result
        assert "Test Result 2" not in result

    def test_connection_error(self, mock_searxng_url, mock_requests_get):
        """Test connection error handling."""
        import requests

        mock_requests_get.side_effect = requests.exceptions.ConnectionError()
        tool = WebSearchTool()
        result = tool.execute(query="test")
        assert "Error" in result
        assert "Cannot connect" in result

    def test_timeout_error(self, mock_searxng_url, mock_requests_get):
        """Test timeout error handling."""
        import requests

        mock_requests_get.side_effect = requests.exceptions.Timeout()
        tool = WebSearchTool()
        result = tool.execute(query="test")
        assert "Error" in result
        assert "timeout" in result.lower()


class TestWebSearchTypeGuards:
    """Type guards for LLM input validation."""

    def setup_method(self):
        """Set up test environment."""
        if "SEARXNG_URL" in os.environ:
            del os.environ["SEARXNG_URL"]
        os.environ["SEARXNG_URL"] = "http://localhost:8080"
        self.tool = WebSearchTool()

    def teardown_method(self):
        """Clean up test environment."""
        if "SEARXNG_URL" in os.environ:
            del os.environ["SEARXNG_URL"]

    def test_query_not_string_rejected(self):
        """Test non-string query is rejected."""
        result = self.tool.execute(query=123)
        assert "Validation error" in result
        assert "query must be string" in result

    def test_max_results_not_int_rejected(self):
        """Test non-int max_results is rejected."""
        result = self.tool.execute(query="test", max_results="5")
        assert "Validation error" in result
        assert "max_results must be integer" in result

    def test_max_results_bool_rejected(self):
        """Test bool max_results is rejected (type guard)."""
        result = self.tool.execute(query="test", max_results=True)
        assert "Validation error" in result

    def test_max_results_zero_rejected(self):
        """Test zero max_results is rejected."""
        result = self.tool.execute(query="test", max_results=0)
        assert "Validation error" in result
        assert ">= 1" in result

    def test_max_results_negative_rejected(self):
        """Test negative max_results is rejected."""
        result = self.tool.execute(query="test", max_results=-5)
        assert "Validation error" in result

    def test_empty_query_rejected(self, mock_requests_get):
        """Test empty query is rejected."""
        result = self.tool.execute(query="   ")
        assert "Validation error" in result
        assert "empty" in result.lower()

    def test_categories_not_string_rejected(self):
        """Test non-string categories is rejected."""
        result = self.tool.execute(query="test", categories=123)
        assert "Validation error" in result
        assert "categories must be string" in result

    def test_invalid_category_rejected(self):
        """Test invalid category is rejected with helpful message."""
        result = self.tool.execute(query="test", categories="invalid_cat")
        assert "Validation error" in result
        assert "invalid category" in result
        assert "general" in result  # Shows valid categories

    def test_valid_categories_accepted(self, mock_requests_get):
        """Test all valid categories are accepted."""
        for cat in ["general", "images", "news", "science", "it", "files"]:
            result = self.tool.execute(query="test", categories=cat)
            assert "Validation error" not in result


class TestWebSearchToOpenAIFormat:
    """Test OpenAI function format generation."""

    def test_to_openai_format(self):
        """Test tool converts to OpenAI format correctly."""
        tool = WebSearchTool()
        fmt = tool.to_openai_format()
        assert fmt["type"] == "function"
        assert fmt["function"]["name"] == "web_search"
        assert "description" in fmt["function"]
        assert "parameters" in fmt["function"]

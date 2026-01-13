"""Web Search Tool - Search the web using SearXNG."""

import os
import requests
from tools.base import BaseTool


class WebSearchTool(BaseTool):
    """Web search using self-hosted SearXNG instance."""

    DEFAULT_TIMEOUT = 30
    DEFAULT_MAX_RESULTS = 5
    VALID_CATEGORIES = ["general", "images", "news", "science", "it", "files"]

    def __init__(self):
        super().__init__()
        self._searxng_url = os.getenv("SEARXNG_URL")

    @property
    def name(self) -> str:
        return "web_search"

    @property
    def description(self) -> str:
        return (
            "Search the web for current information. "
            "Returns titles, URLs, and snippets from search results. "
            "Use for questions about recent events, documentation, or facts."
        )

    @property
    def parameters(self) -> dict:
        return {
            "type": "object",
            "properties": {
                "query": {
                    "type": "string",
                    "description": "Search query (e.g., 'python requests library')",
                },
                "max_results": {
                    "type": "integer",
                    "description": (
                        f"Maximum results to return. Default: {self.DEFAULT_MAX_RESULTS}"
                    ),
                },
                "categories": {
                    "type": "string",
                    "description": (
                        f"Search category: {', '.join(self.VALID_CATEGORIES)}. "
                        "Default: general"
                    ),
                },
            },
            "required": ["query"],
        }

    def execute(
        self,
        query: str,
        max_results: int = None,
        categories: str = "general",
        timeout: int = None,
    ) -> str:
        """Execute web search via SearXNG."""

        # === TYPE GUARDS ===
        if not isinstance(query, str):
            return f"Validation error: query must be string, got {type(query).__name__}"
        if max_results is not None:
            if type(max_results) is not int:
                return (
                    f"Validation error: max_results must be integer, "
                    f"got {type(max_results).__name__}"
                )
            if max_results < 1:
                return f"Validation error: max_results must be >= 1, got {max_results}"
        if not isinstance(categories, str):
            return (
                f"Validation error: categories must be string, "
                f"got {type(categories).__name__}"
            )

        # === CATEGORIES VALIDATION ===
        if categories not in self.VALID_CATEGORIES:
            return (
                f"Validation error: invalid category '{categories}'. "
                f"Valid categories: {', '.join(self.VALID_CATEGORIES)}"
            )

        # === SEARXNG CHECK ===
        if not self._searxng_url:
            return (
                "Error: SEARXNG_URL not configured. "
                "Web search requires a SearXNG instance. "
                "Use 'docker compose up' to start with SearXNG, "
                "or set SEARXNG_URL to your SearXNG instance."
            )

        # === DEFAULTS ===
        max_results = max_results or self.DEFAULT_MAX_RESULTS
        timeout = timeout or self.DEFAULT_TIMEOUT

        # === QUERY VALIDATION ===
        query = query.strip()
        if not query:
            return "Validation error: query cannot be empty"

        # === EXECUTE SEARCH ===
        try:
            response = requests.get(
                f"{self._searxng_url}/search",
                params={
                    "q": query,
                    "format": "json",
                    "categories": categories,
                },
                timeout=timeout,
            )
            response.raise_for_status()
            data = response.json()

        except requests.exceptions.ConnectionError:
            return (
                f"Error: Cannot connect to SearXNG at {self._searxng_url}. "
                "Is it running?"
            )
        except requests.exceptions.Timeout:
            return f"Error: Search timeout (>{timeout}s). Try a simpler query."
        except requests.exceptions.RequestException as e:
            return f"Error: Search failed: {e}"

        # === FORMAT RESULTS ===
        results = data.get("results", [])[:max_results]

        if not results:
            return f"[Web Search: {query}]\n\nNo results found."

        output_parts = [f"[Web Search: {query}]", f"[{len(results)} results]", ""]

        for i, result in enumerate(results, 1):
            title = result.get("title", "No title")
            url = result.get("url", "")
            snippet = result.get("content", "No description")

            output_parts.append(f"{i}. {title}")
            output_parts.append(f"   {url}")
            output_parts.append(f"   {snippet}")
            output_parts.append("")

        return "\n".join(output_parts)


if __name__ == "__main__":
    import sys

    tool = WebSearchTool()
    if len(sys.argv) < 2:
        print("Usage: python -m tools.web.web_search <query>")
        sys.exit(1)
    print(tool.execute(query=" ".join(sys.argv[1:])))

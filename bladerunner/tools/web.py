"""Web search and fetching tools."""

import os
from typing import Any, Dict
from .base import Tool

try:
    import requests
    from bs4 import BeautifulSoup

    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False


class WebSearchTool(Tool):
    """Search the web using Brave Search API."""

    @property
    def name(self) -> str:
        return "WebSearch"

    @property
    def description(self) -> str:
        return "Search the web for current information"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["query"],
            "properties": {
                "query": {"type": "string", "description": "The search query"},
                "num_results": {
                    "type": "integer",
                    "description": "Number of results to return (default: 5)",
                    "default": 5,
                },
            },
        }

    def execute(self, query: str, num_results: int = 5) -> str:
        """Search web using Brave Search API."""
        if not WEB_AVAILABLE:
            return "Error: Web search requires 'requests' and 'beautifulsoup4' packages"

        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            return "Error: BRAVE_API_KEY environment variable not set"

        try:
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": api_key},
                params={"q": query, "count": num_results},
                timeout=10,
            )
            response.raise_for_status()
            results = response.json()

            # Format results
            formatted = []
            for i, result in enumerate(results.get("web", {}).get("results", []), 1):
                formatted.append(
                    f"{i}. {result['title']}\n"
                    f"   URL: {result['url']}\n"
                    f"   {result['description']}\n"
                )

            return "\n".join(formatted) if formatted else "No results found"
        except Exception as e:
            return f"Error performing web search: {str(e)}"


class FetchWebpageTool(Tool):
    """Fetch and extract content from a webpage."""

    @property
    def name(self) -> str:
        return "FetchWebpage"

    @property
    def description(self) -> str:
        return "Fetch and extract text content from a webpage"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["url"],
            "properties": {
                "url": {"type": "string", "description": "The URL to fetch"}
            },
        }

    def execute(self, url: str) -> str:
        """Fetch and extract text content from URL."""
        if not WEB_AVAILABLE:
            return (
                "Error: Web fetching requires 'requests' and 'beautifulsoup4' packages"
            )

        try:
            response = requests.get(url, timeout=10)
            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            # Remove script and style elements
            for script in soup(["script", "style"]):
                script.decompose()

            # Get text
            text = soup.get_text()

            # Clean up whitespace
            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            # Truncate if too long
            max_chars = 10000
            if len(text) > max_chars:
                text = text[:max_chars] + "\n... (truncated)"

            return text
        except Exception as e:
            return f"Error fetching webpage: {str(e)}"

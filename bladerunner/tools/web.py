"""Web search and fetching tools."""

import os
import re
from typing import Any, Dict
from .base import Tool

try:
    import requests
    from bs4 import BeautifulSoup

    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False


class WebSearchTool(Tool):
    """Search the web using multiple providers (DuckDuckGo, Brave)."""

    def __init__(self, provider: str = "duckduckgo", max_results: int = 5):
        """Initialize web search tool with provider.
        
        Args:
            provider: Search provider ("duckduckgo" or "brave")
            max_results: Maximum number of results to return
        """
        self.provider = provider.lower()
        self.max_results = max_results

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

    def _search_duckduckgo(self, query: str, num_results: int) -> str:
        """Search using DuckDuckGo (no API key required)."""
        try:
            # Use DuckDuckGo HTML search
            response = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={
                    "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36"
                },
                timeout=10,
            )
            response.raise_for_status()
            
            soup = BeautifulSoup(response.text, "html.parser")
            results = []
            
            # Parse search results
            for result_div in soup.select(".result")[:num_results]:
                title_elem = result_div.select_one(".result__a")
                snippet_elem = result_div.select_one(".result__snippet")
                
                if title_elem:
                    title = title_elem.get_text(strip=True)
                    url = title_elem.get("href", "")
                    
                    # DuckDuckGo wraps URLs in redirect - extract actual URL
                    if url.startswith("/"):
                        url_match = re.search(r"uddg=([^&]+)", url)
                        if url_match:
                            from urllib.parse import unquote
                            url = unquote(url_match.group(1))
                    
                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    
                    results.append({
                        "title": title,
                        "url": url,
                        "description": snippet
                    })
            
            if not results:
                return "No results found"
            
            # Format results
            formatted = []
            for i, result in enumerate(results, 1):
                formatted.append(
                    f"{i}. {result['title']}\n"
                    f"   URL: {result['url']}\n"
                    f"   {result['description']}\n"
                )
            
            return "\n".join(formatted)
        
        except Exception as e:
            return f"Error performing DuckDuckGo search: {str(e)}"

    def _search_brave(self, query: str, num_results: int) -> str:
        """Search using Brave Search API (requires API key)."""
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
            return f"Error performing Brave search: {str(e)}"

    def execute(self, query: str, num_results: int = 5) -> str:
        """Search web using configured provider (with fallback)."""
        if not WEB_AVAILABLE:
            return "Error: Web search requires 'requests' and 'beautifulsoup4' packages"

        # Use specified num_results or default from config
        num_results = num_results or self.max_results

        # Try primary provider
        if self.provider == "brave":
            result = self._search_brave(query, num_results)
            # Fallback to DuckDuckGo if Brave fails
            if result.startswith("Error") and "BRAVE_API_KEY" in result:
                return self._search_duckduckgo(query, num_results)
            return result
        else:  # Default to DuckDuckGo
            result = self._search_duckduckgo(query, num_results)
            # Fallback to Brave if DuckDuckGo fails and Brave key is available
            if result.startswith("Error") and os.getenv("BRAVE_API_KEY"):
                return self._search_brave(query, num_results)
            return result


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

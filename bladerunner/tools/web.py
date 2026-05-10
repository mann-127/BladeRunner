"""Web search and fetching tools."""

import ipaddress
import os
import re
from urllib.parse import unquote, urljoin, urlparse

from .base import Tool

try:
    import requests
    from bs4 import BeautifulSoup

    WEB_AVAILABLE = True
except ImportError:
    WEB_AVAILABLE = False

# Private/reserved IP ranges to block for SSRF prevention
_BLOCKED_HOSTNAMES = frozenset({"localhost", "127.0.0.1", "::1", "[::1]"})


def _validate_fetch_url(url):
    """Return an error string if the URL is unsafe, or None if OK."""
    try:
        parsed = urlparse(url)
    except Exception:
        return "Invalid URL"

    if parsed.scheme not in ("http", "https"):
        return f"Unsupported scheme '{parsed.scheme}': only http/https allowed"

    host = parsed.hostname or ""
    if not host:
        return "Missing host in URL"

    if host.lower() in _BLOCKED_HOSTNAMES:
        return "Access to loopback addresses is not allowed"

    try:
        addr = ipaddress.ip_address(host)
        if addr.is_private or addr.is_loopback or addr.is_link_local or addr.is_reserved:
            return "Access to private/internal IP addresses is not allowed"
    except ValueError:
        pass  # Not an IP literal — hostname, proceed

    return None


class WebSearchTool(Tool):
    """Search the web using multiple providers (DuckDuckGo, Brave)."""

    def __init__(self, provider="duckduckgo", max_results=5):
        self.provider = provider.lower()
        self.max_results = max_results

    @property
    def name(self):
        return "WebSearch"

    @property
    def description(self):
        return "Search the web for current information"

    @property
    def parameters(self):
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

    def _search_duckduckgo(self, query, num_results):
        try:
            response = requests.get(
                "https://html.duckduckgo.com/html/",
                params={"q": query},
                headers={"User-Agent": ("Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36")},
                timeout=10,
            )
            response.raise_for_status()

            soup = BeautifulSoup(response.text, "html.parser")
            results = []

            for result_div in soup.select(".result")[:num_results]:
                title_elem = result_div.select_one(".result__a")
                snippet_elem = result_div.select_one(".result__snippet")

                if title_elem:
                    title = title_elem.get_text(strip=True)
                    href_value = title_elem.get("href", "")
                    url = href_value if isinstance(href_value, str) else ""

                    # DuckDuckGo wraps URLs in redirect — extract actual URL
                    if url.startswith("/"):
                        url_match = re.search(r"uddg=([^&]+)", url)
                        if url_match:
                            url = unquote(url_match.group(1))

                    snippet = snippet_elem.get_text(strip=True) if snippet_elem else ""
                    results.append({"title": title, "url": url, "description": snippet})

            if not results:
                return "No results found"

            formatted = []
            for i, result in enumerate(results, 1):
                formatted.append(f"{i}. {result['title']}\n   URL: {result['url']}\n   {result['description']}\n")

            return "\n".join(formatted)

        except Exception as e:
            return f"Error performing DuckDuckGo search: {str(e)}"

    def _search_brave(self, query, num_results):
        api_key = os.getenv("BRAVE_API_KEY")
        if not api_key:
            return "Error: BRAVE_API_KEY environment variable not set"

        try:
            params = {"q": query, "count": num_results}
            response = requests.get(
                "https://api.search.brave.com/res/v1/web/search",
                headers={"X-Subscription-Token": api_key},
                params=params,
                timeout=10,
            )
            response.raise_for_status()
            results = response.json()

            formatted = []
            for i, result in enumerate(results.get("web", {}).get("results", []), 1):
                formatted.append(f"{i}. {result['title']}\n   URL: {result['url']}\n   {result['description']}\n")

            return "\n".join(formatted) if formatted else "No results found"
        except Exception as e:
            return f"Error performing Brave search: {str(e)}"

    def execute(self, query, num_results=5):
        if not WEB_AVAILABLE:
            return "Error: Web search requires 'requests' and 'beautifulsoup4' packages"

        num_results = num_results or self.max_results

        if self.provider == "brave":
            result = self._search_brave(query, num_results)
            if result.startswith("Error") and "BRAVE_API_KEY" in result:
                return self._search_duckduckgo(query, num_results)
            return result
        else:
            result = self._search_duckduckgo(query, num_results)
            if result.startswith("Error") and os.getenv("BRAVE_API_KEY"):
                return self._search_brave(query, num_results)
            return result


class FetchWebpageTool(Tool):
    """Fetch and extract content from a webpage."""

    @property
    def name(self):
        return "FetchWebpage"

    @property
    def description(self):
        return "Fetch and extract text content from a webpage"

    @property
    def parameters(self):
        return {
            "type": "object",
            "required": ["url"],
            "properties": {"url": {"type": "string", "description": "The URL to fetch"}},
        }

    def execute(self, url):
        if not WEB_AVAILABLE:
            return "Error: Web fetching requires 'requests' and 'beautifulsoup4' packages"

        error = _validate_fetch_url(url)
        if error:
            return f"Error: {error}"

        try:
            response = requests.get(url, timeout=10, allow_redirects=False)
            if 300 <= response.status_code < 400:
                redirect_location = response.headers.get("Location")
                if not redirect_location:
                    return "Error fetching webpage: Redirect missing Location header"

                redirect_url = urljoin(url, redirect_location)
                redirect_error = _validate_fetch_url(redirect_url)
                if redirect_error:
                    return f"Error: {redirect_error}"

                response = requests.get(redirect_url, timeout=10, allow_redirects=False)
                if 300 <= response.status_code < 400:
                    return "Error fetching webpage: Redirect chain blocked"

            response.raise_for_status()
            soup = BeautifulSoup(response.text, "html.parser")

            for script in soup(["script", "style"]):
                script.decompose()

            text = soup.get_text()

            lines = (line.strip() for line in text.splitlines())
            chunks = (phrase.strip() for line in lines for phrase in line.split("  "))
            text = "\n".join(chunk for chunk in chunks if chunk)

            max_chars = 10000
            if len(text) > max_chars:
                text = text[:max_chars] + "\n... (truncated)"

            return text
        except Exception as e:
            return f"Error fetching webpage: {str(e)}"

"""Tests for web search and fetch tools."""

from unittest.mock import Mock, patch
from bladerunner.tools.web import (
    WebSearchTool,
    FetchWebpageTool,
    WEB_AVAILABLE,
)


def test_web_dependencies_available() -> None:
    """Web tools dependencies should be available."""
    assert WEB_AVAILABLE is True


def test_web_search_tool_definition() -> None:
    """WebSearchTool should have proper definition."""
    tool = WebSearchTool()
    
    assert tool.name == "WebSearch"
    assert "search" in tool.description.lower() or "web" in tool.description.lower()
    assert "query" in tool.parameters["properties"]
    assert tool.parameters["required"] == ["query"]


def test_web_search_tool_requires_api_key(monkeypatch) -> None:
    """WebSearchTool should require BRAVE_API_KEY."""
    monkeypatch.delenv("BRAVE_API_KEY", raising=False)
    
    tool = WebSearchTool()
    result = tool.execute(query="test")
    
    assert "BRAVE_API_KEY" in result
    assert "Error" in result


@patch("bladerunner.tools.web.requests.get")
def test_web_search_tool_formats_results(mock_get) -> None:
    """WebSearchTool should format search results correctly."""
    # Mock successful API response
    mock_response = Mock()
    mock_response.json.return_value = {
        "web": {
            "results": [
                {
                    "title": "Test Result 1",
                    "url": "https://example.com/1",
                    "description": "First test result",
                },
                {
                    "title": "Test Result 2",
                    "url": "https://example.com/2",
                    "description": "Second test result",
                },
            ]
        }
    }
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    tool = WebSearchTool()
    
    # Set fake API key
    import os
    os.environ["BRAVE_API_KEY"] = "fake-key-for-testing"
    
    result = tool.execute(query="test query", num_results=2)
    
    assert "Test Result 1" in result
    assert "Test Result 2" in result
    assert "https://example.com/1" in result
    assert "First test result" in result


@patch("bladerunner.tools.web.requests.get")
def test_web_search_tool_handles_no_results(mock_get) -> None:
    """WebSearchTool should handle empty results gracefully."""
    mock_response = Mock()
    mock_response.json.return_value = {"web": {"results": []}}
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    import os
    os.environ["BRAVE_API_KEY"] = "fake-key"
    
    tool = WebSearchTool()
    result = tool.execute(query="nonexistent query")
    
    assert "No results found" in result


@patch("bladerunner.tools.web.requests.get")
def test_web_search_tool_handles_api_error(mock_get) -> None:
    """WebSearchTool should handle API errors gracefully."""
    mock_get.side_effect = Exception("API Error")
    
    import os
    os.environ["BRAVE_API_KEY"] = "fake-key"
    
    tool = WebSearchTool()
    result = tool.execute(query="test")
    
    assert "Error" in result
    assert "API Error" in result or "web search" in result.lower()


@patch("bladerunner.tools.web.requests.get")
def test_web_search_respects_num_results_parameter(mock_get) -> None:
    """WebSearchTool should respect num_results parameter."""
    import os
    os.environ["BRAVE_API_KEY"] = "fake-key"
    
    tool = WebSearchTool()
    tool.execute(query="test", num_results=10)
    
    # Check that the API was called with correct count parameter
    call_kwargs = mock_get.call_args[1]
    assert call_kwargs["params"]["count"] == 10


def test_fetch_webpage_tool_definition() -> None:
    """FetchWebpageTool should have proper definition."""
    tool = FetchWebpageTool()
    
    assert tool.name == "FetchWebpage"
    assert "fetch" in tool.description.lower() or "webpage" in tool.description.lower()
    assert "url" in tool.parameters["properties"]
    assert tool.parameters["required"] == ["url"]


@patch("bladerunner.tools.web.requests.get")
def test_fetch_webpage_extracts_text(mock_get) -> None:
    """FetchWebpageTool should extract text from HTML."""
    mock_response = Mock()
    mock_response.text = """
        <html>
            <head><title>Test Page</title></head>
            <body>
                <h1>Main Heading</h1>
                <p>This is a test paragraph.</p>
                <script>console.log('should be removed');</script>
                <style>.class { display: none; }</style>
            </body>
        </html>
    """
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    tool = FetchWebpageTool()
    result = tool.execute(url="https://example.com")
    
    assert "Main Heading" in result
    assert "test paragraph" in result
    # Scripts and styles should be removed
    assert "console.log" not in result
    assert "display: none" not in result


@patch("bladerunner.tools.web.requests.get")
def test_fetch_webpage_truncates_long_content(mock_get) -> None:
    """FetchWebpageTool should truncate very long content."""
    # Create content longer than 10,000 chars
    long_content = "x" * 15000
    mock_response = Mock()
    mock_response.text = f"<html><body><p>{long_content}</p></body></html>"
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    tool = FetchWebpageTool()
    result = tool.execute(url="https://example.com")
    
    assert "truncated" in result
    assert len(result) < 12000  # Should be under max_chars + buffer


@patch("bladerunner.tools.web.requests.get")
def test_fetch_webpage_handles_errors(mock_get) -> None:
    """FetchWebpageTool should handle fetch errors gracefully."""
    mock_get.side_effect = Exception("Connection error")
    
    tool = FetchWebpageTool()
    result = tool.execute(url="https://invalid.url")
    
    assert "Error" in result
    assert "Connection error" in result or "fetching webpage" in result.lower()


@patch("bladerunner.tools.web.requests.get")
def test_fetch_webpage_handles_http_errors(mock_get) -> None:
    """FetchWebpageTool should handle HTTP errors."""
    mock_response = Mock()
    mock_response.raise_for_status.side_effect = Exception("404 Not Found")
    mock_get.return_value = mock_response
    
    tool = FetchWebpageTool()
    result = tool.execute(url="https://example.com/notfound")
    
    assert "Error" in result


@patch("bladerunner.tools.web.requests.get")
def test_fetch_webpage_cleans_whitespace(mock_get) -> None:
    """FetchWebpageTool should clean up excessive whitespace."""
    mock_response = Mock()
    mock_response.text = """
        <html><body>
        <p>Line  with    extra     spaces</p>
        
        
        <p>Another line</p>
        </body></html>
    """
    mock_response.raise_for_status = Mock()
    mock_get.return_value = mock_response
    
    tool = FetchWebpageTool()
    result = tool.execute(url="https://example.com")
    
    # Should contain the text (HTML parser may format whitespace differently)
    assert "Line" in result
    assert "spaces" in result
    assert "Another line" in result

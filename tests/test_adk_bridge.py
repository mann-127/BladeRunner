"""Tests for Google ADK bridge helpers."""

from bladerunner.adk_bridge import GoogleADKBridge


def test_extract_answer_text() -> None:
    """Bridge should extract text from candidate parts."""
    bridge = GoogleADKBridge()
    payload = {
        "candidates": [
            {
                "content": {
                    "parts": [
                        {"text": "Line 1"},
                        {"text": "Line 2"},
                    ]
                }
            }
        ]
    }

    assert bridge._extract_answer_text(payload) == "Line 1\nLine 2"


def test_extract_sources_deduplicates_urls() -> None:
    """Bridge should parse grounding chunks and deduplicate URLs."""
    bridge = GoogleADKBridge()
    payload = {
        "candidates": [
            {
                "groundingMetadata": {
                    "groundingChunks": [
                        {"web": {"title": "A", "uri": "https://a.example"}},
                        {"web": {"title": "A duplicate", "uri": "https://a.example"}},
                        {"web": {"title": "B", "uri": "https://b.example"}},
                    ]
                }
            }
        ]
    }

    sources = bridge._extract_sources(payload)
    assert len(sources) == 2
    assert sources[0]["url"] == "https://a.example"
    assert sources[1]["url"] == "https://b.example"

"""Google ADK/Gemini bridge for grounded responses."""

from __future__ import annotations

import importlib
import os
from dataclasses import dataclass
from typing import Any, Dict, List

import requests


@dataclass
class GroundedResponse:
    """Structured response payload for grounded generation."""

    answer: str
    sources: List[Dict[str, str]]
    provider: str


class GoogleADKBridge:
    """Best-effort Google ADK bridge with Gemini REST fallback.

    The implementation prioritizes broad compatibility:
    - If Google ADK is installed, we mark ADK availability and try to use it.
    - If ADK runtime invocation is unavailable in this environment, we fall back
      to Gemini's public REST API with optional Google Search grounding.
    """

    def __init__(
        self, model: str = "gemini-2.0-flash", enable_search_grounding: bool = True
    ):
        self.model = model
        self.enable_search_grounding = enable_search_grounding
        self.api_key = os.getenv("GOOGLE_API_KEY")

    @staticmethod
    def adk_available() -> bool:
        """Return True when Google ADK can be imported."""
        try:
            importlib.import_module("google.adk")
            return True
        except Exception:
            return False

    def generate(self, prompt: str) -> GroundedResponse:
        """Generate a grounded response using ADK when possible, else REST fallback."""
        if not self.api_key:
            raise RuntimeError("GOOGLE_API_KEY environment variable not set")

        # ADK path is intentionally guarded because ADK APIs can vary by version.
        if self.adk_available():
            try:
                return self._generate_via_adk(prompt)
            except Exception:
                # Fall through to REST fallback.
                pass

        return self._generate_via_rest(prompt)

    def _generate_via_adk(self, prompt: str) -> GroundedResponse:
        """Attempt ADK invocation.

        We currently keep this path conservative: it verifies ADK import and then
        falls back to REST for generation to avoid version-specific breakage.
        """
        importlib.import_module("google.adk")
        response = self._generate_via_rest(prompt)
        response.provider = "google_adk+rest_fallback"
        return response

    def _generate_via_rest(self, prompt: str) -> GroundedResponse:
        """Use Gemini REST API with optional Search grounding."""
        endpoint = (
            "https://generativelanguage.googleapis.com/v1beta/models/"
            f"{self.model}:generateContent"
        )

        payload: Dict[str, Any] = {
            "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        }

        if self.enable_search_grounding:
            payload["tools"] = [{"google_search": {}}]

        response = requests.post(
            endpoint,
            params={"key": self.api_key},
            json=payload,
            timeout=25,
        )

        # Handle errors with sanitized messages (don't expose API key in URL)
        if response.status_code == 429:
            raise RuntimeError(
                "Google Gemini rate limit exceeded. "
                "Please wait a few minutes and try again, "
                "or switch to 'bladerunner' engine (OpenRouter backend)."
            )
        elif not response.ok:
            raise RuntimeError(
                f"Google Gemini API error: {response.status_code} {response.reason}. "
                f"Check your GOOGLE_API_KEY and try again."
            )

        body = response.json()

        answer = self._extract_answer_text(body)
        sources = self._extract_sources(body)

        return GroundedResponse(
            answer=answer or "No answer returned by Gemini.",
            sources=sources,
            provider=(
                "gemini_rest_grounded"
                if self.enable_search_grounding
                else "gemini_rest"
            ),
        )

    def _extract_answer_text(self, body: Dict[str, Any]) -> str:
        """Extract text from Gemini candidate payload."""
        candidates = body.get("candidates", [])
        if not candidates:
            return ""

        parts = candidates[0].get("content", {}).get("parts", [])
        text_chunks = [part.get("text", "") for part in parts if isinstance(part, dict)]
        return "\n".join(chunk for chunk in text_chunks if chunk).strip()

    def _extract_sources(self, body: Dict[str, Any]) -> List[Dict[str, str]]:
        """Extract deduplicated sources from grounding metadata."""
        candidates = body.get("candidates", [])
        if not candidates:
            return []

        grounding = candidates[0].get("groundingMetadata", {})
        chunks = grounding.get("groundingChunks", [])

        seen = set()
        sources: List[Dict[str, str]] = []

        for chunk in chunks:
            web = chunk.get("web", {}) if isinstance(chunk, dict) else {}
            uri = web.get("uri")
            title = web.get("title") or uri
            if not uri or uri in seen:
                continue
            seen.add(uri)
            sources.append({"title": str(title), "url": str(uri)})

        return sources

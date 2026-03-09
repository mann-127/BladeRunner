"""Execution trace recorder for reasoning transparency."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime, timezone
from typing import Any, Dict, List, Optional


@dataclass
class TraceEvent:
    """Single structured trace event."""

    timestamp: str
    event_type: str
    data: Dict[str, Any] = field(default_factory=dict)


class ExecutionTraceRecorder:
    """Record structured events for each agent execution."""

    def __init__(self):
        self.active_trace: Dict[str, Any] = {}

    def start(self, prompt: str, model: str) -> None:
        """Start a fresh trace."""
        self.active_trace = {
            "started_at": datetime.now(timezone.utc).isoformat(),
            "model": model,
            "prompt": prompt,
            "events": [],
            "status": "running",
        }

    def log(self, event_type: str, **data: Any) -> None:
        """Append an event to the active trace."""
        if not self.active_trace:
            return
        event = TraceEvent(
            timestamp=datetime.now(timezone.utc).isoformat(),
            event_type=event_type,
            data=data,
        )
        self.active_trace["events"].append(
            {
                "timestamp": event.timestamp,
                "event_type": event.event_type,
                "data": event.data,
            }
        )

    def finish(self, status: str, final_answer: str = "", error: str = "") -> Dict[str, Any]:
        """Finalize and return the current trace."""
        if not self.active_trace:
            return {}

        self.active_trace["status"] = status
        self.active_trace["finished_at"] = datetime.now(timezone.utc).isoformat()
        self.active_trace["final_answer_preview"] = final_answer[:200]
        self.active_trace["error"] = error
        return self.active_trace.copy()

    def get_active_trace(self) -> Dict[str, Any]:
        """Get a copy of current active trace."""
        return self.active_trace.copy()

    def render_compact(self, trace: Optional[Dict[str, Any]] = None) -> str:
        """Render a compact human-readable trace summary."""
        target = trace or self.active_trace
        if not target:
            return "No trace available."

        lines = [
            f"status={target.get('status', 'unknown')}",
            f"model={target.get('model', 'unknown')}",
            f"events={len(target.get('events', []))}",
        ]

        for event in target.get("events", [])[-8:]:
            lines.append(f"- {event['event_type']}")

        return "\n".join(lines)

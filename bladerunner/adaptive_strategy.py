"""Adaptive strategy manager for iterative agent behavior tuning."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, Optional


@dataclass
class ToolStats:
    """Track per-tool failure and success history."""

    consecutive_failures: int = 0
    total_failures: int = 0
    total_successes: int = 0


class AdaptiveStrategyManager:
    """Record tool outcomes and emit bounded adaptation guidance."""

    def __init__(self, failure_threshold: int = 2):
        self.failure_threshold = failure_threshold
        self.tool_stats: Dict[str, ToolStats] = {}

    def record_tool_outcome(
        self,
        tool_name: str,
        success: bool,
        error_message: Optional[str] = None,
    ) -> Optional[str]:
        """Update tool stats and return adaptation guidance when needed."""
        stats = self.tool_stats.setdefault(tool_name, ToolStats())

        if success:
            stats.total_successes += 1
            stats.consecutive_failures = 0
            return None

        stats.total_failures += 1
        stats.consecutive_failures += 1

        if stats.consecutive_failures >= self.failure_threshold:
            guidance = (
                f"Tool '{tool_name}' failed {stats.consecutive_failures} times in a row. "
                f"Switch to an alternate approach or simplify the tool arguments before retrying."
            )
            if error_message:
                guidance += f" Latest error: {error_message[:200]}"
            return guidance

        return None

    def get_active_guidance(self) -> str:
        """Return compact guidance summary based on current failure patterns."""
        unstable_tools = [
            name
            for name, stats in self.tool_stats.items()
            if stats.consecutive_failures >= self.failure_threshold
        ]
        if not unstable_tools:
            return ""

        names = ", ".join(sorted(unstable_tools))
        return (
            "Adaptive guidance: avoid repeating the same failed strategy. "
            f"Tools currently unstable: {names}."
        )

    def reset(self) -> None:
        """Reset adaptation history."""
        self.tool_stats.clear()

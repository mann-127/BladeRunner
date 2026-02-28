"""Tool effectiveness tracking for learning agent behavior."""

import json
from pathlib import Path
from typing import Dict, Any, Optional
from datetime import datetime


class ToolTracker:
    """Tracks success/failure rates of tools for learning."""

    def __init__(self, data_dir: Optional[Path] = None):
        """Initialize tool tracker."""
        self.data_dir = data_dir or (Path.home() / ".bladerunner" / "metrics")
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.stats_file = self.data_dir / "tool_stats.json"

        self.stats = self._load_stats()
        self.session_stats: Dict[str, Dict[str, Any]] = {}

    def _load_stats(self) -> Dict[str, Any]:
        """Load statistics from disk."""
        if self.stats_file.exists():
            try:
                with open(self.stats_file, "r") as f:
                    return json.load(f)
            except Exception:
                return {}
        return {}

    def record_execution(
        self, tool_name: str, success: bool, error: Optional[str] = None
    ) -> None:
        """Record tool execution result."""
        if tool_name not in self.stats:
            self.stats[tool_name] = {
                "total": 0,
                "successful": 0,
                "failed": 0,
                "success_rate": 0.0,
                "last_used": None,
                "errors": {},
            }

        stats = self.stats[tool_name]
        stats["total"] += 1
        stats["last_used"] = datetime.now().isoformat()

        if success:
            stats["successful"] += 1
        else:
            stats["failed"] += 1
            if error:
                error_type = error.split(":")[0]
                stats["errors"][error_type] = stats["errors"].get(error_type, 0) + 1

        # Update success rate
        stats["success_rate"] = stats["successful"] / stats["total"]

        # Track in session
        if tool_name not in self.session_stats:
            self.session_stats[tool_name] = {
                "calls": 0,
                "successes": 0,
                "failures": 0,
            }

        self.session_stats[tool_name]["calls"] += 1
        if success:
            self.session_stats[tool_name]["successes"] += 1
        else:
            self.session_stats[tool_name]["failures"] += 1

        # Persist to disk
        self._save_stats()

    def get_success_rate(self, tool_name: str) -> float:
        """Get success rate for a tool."""
        if tool_name not in self.stats:
            return 0.5  # Default neutral rate

        return self.stats[tool_name].get("success_rate", 0.0)

    def get_reliability_ranking(self) -> list:
        """Get tools ranked by reliability (success rate)."""
        tools = []
        for tool_name, stats in self.stats.items():
            if stats["total"] >= 3:  # Only rank tools tested 3+ times
                tools.append(
                    {
                        "tool": tool_name,
                        "success_rate": stats["success_rate"],
                        "total": stats["total"],
                        "successful": stats["successful"],
                    }
                )

        # Sort by success rate descending
        return sorted(tools, key=lambda x: x["success_rate"], reverse=True)

    def get_tool_health(self) -> Dict[str, str]:
        """Get health status of tools."""
        health = {}
        for tool_name, stats in self.stats.items():
            rate = stats.get("success_rate", 0)
            if stats["total"] < 3:
                status = "⚠️  Untested"
            elif rate >= 0.9:
                status = "✅ Excellent"
            elif rate >= 0.7:
                status = "⚠️  Fair"
            elif rate >= 0.5:
                status = "❌ Poor"
            else:
                status = "❌ Failing"

            health[tool_name] = f"{status} ({rate*100:.0f}%)"

        return health

    def get_recommendation(self) -> Optional[str]:
        """Get recommendation for next tool to use."""
        ranking = self.get_reliability_ranking()
        if not ranking:
            return None

        best_tool = ranking[0]
        if best_tool["success_rate"] >= 0.8:
            return (
                f"Recommend: {best_tool['tool']} "
                f"({best_tool['success_rate']*100:.0f}% success rate)"
            )

        return None

    def print_session_summary(self) -> None:
        """Print session execution summary."""
        if not self.session_stats:
            return

        print("\n📊 Tool Execution Summary (This Session):")
        print("-" * 50)

        total_calls = sum(s["calls"] for s in self.session_stats.values())
        total_successes = sum(s["successes"] for s in self.session_stats.values())

        for tool, stats in sorted(self.session_stats.items()):
            success_rate = (
                (stats["successes"] / stats["calls"] * 100) if stats["calls"] > 0 else 0
            )
            print(
                f"  {tool}: {stats['calls']} calls, "
                f"{stats['successes']} success, "
                f"{stats['failures']} failed ({success_rate:.0f}%)"
            )

        overall_rate = (total_successes / total_calls * 100) if total_calls > 0 else 0
        print("-" * 50)
        print(f"  Total: {total_calls} calls, {overall_rate:.0f}% success rate")

    def print_tool_rankings(self) -> None:
        """Print tool reliability rankings."""
        ranking = self.get_reliability_ranking()
        if not ranking:
            return

        print("\n🏆 Tool Reliability Ranking (All Time):")
        print("-" * 50)

        for i, tool in enumerate(ranking[:5], 1):
            print(
                f"  {i}. {tool['tool']}: "
                f"{tool['success_rate']*100:.0f}% "
                f"({tool['successful']}/{tool['total']} calls)"
            )

    def _save_stats(self) -> None:
        """Save statistics to disk."""
        try:
            with open(self.stats_file, "w") as f:
                json.dump(self.stats, f, indent=2)
        except Exception:
            pass  # Silently fail - don't break agent for metrics

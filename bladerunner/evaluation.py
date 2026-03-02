"""Evaluation and metrics tracking for agent performance monitoring."""

import json
import time
from pathlib import Path
from typing import Any, Dict, List, Optional
from datetime import datetime
from dataclasses import dataclass, asdict


@dataclass
class TaskExecution:
    """Represents a single task execution."""

    task_id: str
    prompt: str
    start_time: float
    end_time: Optional[float] = None
    success: bool = False
    iterations: int = 0
    total_tokens: int = 0
    prompt_tokens: int = 0
    completion_tokens: int = 0
    tools_used: List[str] = None
    error_message: Optional[str] = None
    model: Optional[str] = None

    def __post_init__(self):
        if self.tools_used is None:
            self.tools_used = []

    @property
    def duration(self) -> Optional[float]:
        """Calculate task duration in seconds."""
        if self.end_time:
            return self.end_time - self.start_time
        return None

    @property
    def tokens_per_second(self) -> Optional[float]:
        """Calculate token throughput."""
        duration = self.duration
        if duration and duration > 0:
            return self.total_tokens / duration
        return None

    def to_dict(self) -> Dict[str, Any]:
        """Convert to dictionary for serialization."""
        data = asdict(self)
        if self.duration:
            data["duration"] = self.duration
        if self.tokens_per_second:
            data["tokens_per_second"] = self.tokens_per_second
        return data


class AgentEvaluator:
    """Tracks and evaluates agent performance metrics."""

    def __init__(self, metrics_dir: Optional[Path] = None):
        """Initialize evaluator with metrics storage."""
        self.metrics_dir = metrics_dir or (Path.home() / ".bladerunner" / "metrics")
        self.metrics_dir.mkdir(parents=True, exist_ok=True)

        self.executions_file = self.metrics_dir / "executions.jsonl"
        self.summary_file = self.metrics_dir / "evaluation_summary.json"

        self.current_execution: Optional[TaskExecution] = None
        self.executions_history: List[TaskExecution] = []

        self._load_history()

    def _load_history(self) -> None:
        """Load execution history from disk."""
        if self.executions_file.exists():
            try:
                with open(self.executions_file, "r") as f:
                    for line in f:
                        data = json.loads(line)
                        # Reconstruct TaskExecution from dict
                        exec_obj = TaskExecution(
                            task_id=data["task_id"],
                            prompt=data["prompt"],
                            start_time=data["start_time"],
                            end_time=data.get("end_time"),
                            success=data.get("success", False),
                            iterations=data.get("iterations", 0),
                            total_tokens=data.get("total_tokens", 0),
                            prompt_tokens=data.get("prompt_tokens", 0),
                            completion_tokens=data.get("completion_tokens", 0),
                            tools_used=data.get("tools_used", []),
                            error_message=data.get("error_message"),
                            model=data.get("model"),
                        )
                        self.executions_history.append(exec_obj)
            except Exception as e:
                print(f"Warning: Could not load execution history: {e}")

    def start_task(self, prompt: str, model: Optional[str] = None) -> str:
        """Start tracking a new task execution."""
        task_id = f"task_{int(time.time() * 1000)}"
        self.current_execution = TaskExecution(
            task_id=task_id,
            prompt=prompt,
            start_time=time.time(),
            model=model,
        )
        return task_id

    def record_iteration(self) -> None:
        """Record an agent iteration."""
        if self.current_execution:
            self.current_execution.iterations += 1

    def record_tool_use(self, tool_name: str) -> None:
        """Record a tool being used."""
        if self.current_execution:
            self.current_execution.tools_used.append(tool_name)

    def record_tokens(
        self, total: int = 0, prompt: int = 0, completion: int = 0
    ) -> None:
        """Record token usage."""
        if self.current_execution:
            self.current_execution.total_tokens += total
            self.current_execution.prompt_tokens += prompt
            self.current_execution.completion_tokens += completion

    def end_task(self, success: bool, error_message: Optional[str] = None) -> None:
        """End the current task execution."""
        if not self.current_execution:
            return

        self.current_execution.end_time = time.time()
        self.current_execution.success = success
        self.current_execution.error_message = error_message

        # Save to history
        self.executions_history.append(self.current_execution)

        # Append to JSONL file
        try:
            with open(self.executions_file, "a") as f:
                f.write(json.dumps(self.current_execution.to_dict()) + "\n")
        except Exception as e:
            print(f"Warning: Could not save execution: {e}")

        # Update summary
        self._update_summary()

        self.current_execution = None

    def _update_summary(self) -> None:
        """Update evaluation summary statistics."""
        if not self.executions_history:
            return

        total_tasks = len(self.executions_history)
        successful_tasks = sum(1 for e in self.executions_history if e.success)
        failed_tasks = total_tasks - successful_tasks

        total_iterations = sum(e.iterations for e in self.executions_history)
        total_tokens = sum(e.total_tokens for e in self.executions_history)

        durations = [e.duration for e in self.executions_history if e.duration]
        avg_duration = sum(durations) / len(durations) if durations else 0

        # Tool usage statistics
        all_tools = []
        for e in self.executions_history:
            all_tools.extend(e.tools_used)

        tool_counts = {}
        for tool in all_tools:
            tool_counts[tool] = tool_counts.get(tool, 0) + 1

        # Model usage statistics
        model_stats = {}
        for e in self.executions_history:
            if e.model:
                if e.model not in model_stats:
                    model_stats[e.model] = {"total": 0, "successful": 0}
                model_stats[e.model]["total"] += 1
                if e.success:
                    model_stats[e.model]["successful"] += 1

        summary = {
            "last_updated": datetime.now().isoformat(),
            "total_tasks": total_tasks,
            "successful_tasks": successful_tasks,
            "failed_tasks": failed_tasks,
            "success_rate": successful_tasks / total_tasks if total_tasks > 0 else 0,
            "avg_iterations_per_task": (
                total_iterations / total_tasks if total_tasks > 0 else 0
            ),
            "avg_duration_seconds": avg_duration,
            "total_tokens_used": total_tokens,
            "avg_tokens_per_task": total_tokens / total_tasks if total_tasks > 0 else 0,
            "tool_usage": tool_counts,
            "most_used_tools": sorted(
                tool_counts.items(), key=lambda x: x[1], reverse=True
            )[:10],
            "model_performance": model_stats,
        }

        try:
            with open(self.summary_file, "w") as f:
                json.dump(summary, f, indent=2)
        except Exception as e:
            print(f"Warning: Could not save summary: {e}")

    def get_summary(self) -> Dict[str, Any]:
        """Get evaluation summary statistics."""
        if self.summary_file.exists():
            try:
                with open(self.summary_file, "r") as f:
                    return json.load(f)
            except Exception:
                pass
        return {}

    def get_recent_executions(self, n: int = 10) -> List[Dict[str, Any]]:
        """Get the N most recent task executions."""
        recent = self.executions_history[-n:] if self.executions_history else []
        return [e.to_dict() for e in reversed(recent)]

    def export_metrics(self, output_file: Optional[Path] = None) -> str:
        """Export all metrics to a JSON file."""
        output_file = output_file or (
            self.metrics_dir / f"export_{int(time.time())}.json"
        )

        export_data = {
            "summary": self.get_summary(),
            "executions": [e.to_dict() for e in self.executions_history],
        }

        try:
            with open(output_file, "w") as f:
                json.dump(export_data, f, indent=2)
            return f"Metrics exported to: {output_file}"
        except Exception as e:
            return f"Error exporting metrics: {e}"

    def clear_history(self) -> None:
        """Clear all execution history (use with caution)."""
        self.executions_history = []
        if self.executions_file.exists():
            self.executions_file.unlink()
        if self.summary_file.exists():
            self.summary_file.unlink()

    def print_summary(self) -> None:
        """Print a formatted summary to console."""
        summary = self.get_summary()
        if not summary:
            print("No evaluation data available yet.")
            return

        print("\n" + "=" * 60)
        print("AGENT PERFORMANCE EVALUATION SUMMARY")
        print("=" * 60)
        print(f"\nLast Updated: {summary.get('last_updated', 'N/A')}")
        print(f"\nTotal Tasks: {summary.get('total_tasks', 0)}")
        print(f"  ✓ Successful: {summary.get('successful_tasks', 0)}")
        print(f"  ✗ Failed: {summary.get('failed_tasks', 0)}")
        print(f"  Success Rate: {summary.get('success_rate', 0):.1%}")
        print(
            f"\nAverage Iterations per Task: {summary.get('avg_iterations_per_task', 0):.1f}"
        )
        print(f"Average Duration: {summary.get('avg_duration_seconds', 0):.2f}s")
        print(f"\nTotal Tokens Used: {summary.get('total_tokens_used', 0):,}")
        print(f"Average Tokens per Task: {summary.get('avg_tokens_per_task', 0):.0f}")

        most_used = summary.get("most_used_tools", [])
        if most_used:
            print("\nMost Used Tools:")
            for tool, count in most_used[:5]:
                print(f"  - {tool}: {count} times")

        model_perf = summary.get("model_performance", {})
        if model_perf:
            print("\nModel Performance:")
            for model, stats in model_perf.items():
                success_rate = (
                    stats["successful"] / stats["total"] if stats["total"] > 0 else 0
                )
                print(
                    f"  - {model}: {stats['total']} tasks ({success_rate:.1%} success)"
                )

        print("\n" + "=" * 60 + "\n")

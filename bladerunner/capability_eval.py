"""Capability benchmark runner for BladeRunner agent behavior.

This module provides a lightweight evaluation harness for measuring
agent capability across multiple task categories.
"""

from __future__ import annotations

import argparse
import json
import re
import statistics
import time
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional

from .agent import Agent
from .config import Config

TaskRecord = Dict[str, Any]


@dataclass
class TaskResult:
    """Result for a single benchmark task."""

    task_id: str
    category: str
    success: bool
    duration_sec: float
    answer: str
    failures: List[str]
    tools_used: List[str]
    iterations: int

    def to_dict(self) -> Dict[str, Any]:
        return {
            "task_id": self.task_id,
            "category": self.category,
            "success": self.success,
            "duration_sec": round(self.duration_sec, 4),
            "answer": self.answer,
            "failures": self.failures,
            "tools_used": self.tools_used,
            "iterations": self.iterations,
        }


class CapabilityBenchmarkRunner:
    """Execute benchmark tasks and compute capability metrics."""

    def __init__(
        self,
        config: Config,
        model: Optional[str] = None,
        agent_factory: Optional[Callable[[], Any]] = None,
    ) -> None:
        self.config = config
        self.model = model or config.get("model", "haiku")
        self._agent_factory = agent_factory

    def _create_agent(self) -> Any:
        """Create an agent instance for benchmark execution."""
        if self._agent_factory:
            return self._agent_factory()

        return Agent(
            config=self.config,
            model=self.model,
            use_permissions=False,
            permission_profile="permissive",
            session_id=None,
        )

    def run(self, tasks: List[TaskRecord]) -> Dict[str, Any]:
        """Run benchmark tasks and return a structured report."""
        started_at = datetime.now(timezone.utc).isoformat()
        results: List[TaskResult] = []

        for task in tasks:
            results.append(self._run_task(task))

        summary = _summarize_results(results)
        return {
            "started_at": started_at,
            "finished_at": datetime.now(timezone.utc).isoformat(),
            "task_count": len(results),
            "summary": summary,
            "results": [item.to_dict() for item in results],
        }

    def _run_task(self, task: TaskRecord) -> TaskResult:
        """Execute a single task and evaluate checks."""
        agent = self._create_agent()

        task_id = task["id"]
        category = task.get("category", "uncategorized")
        prompt = task["prompt"]

        started = time.perf_counter()
        answer = agent.execute(prompt)
        duration_sec = time.perf_counter() - started

        failures = evaluate_checks(answer, task.get("checks", []))

        max_duration = task.get("max_duration_sec")
        if isinstance(max_duration, (int, float)) and duration_sec > max_duration:
            failures.append(
                "Exceeded max_duration_sec "
                f"({duration_sec:.2f}s > {float(max_duration):.2f}s)"
            )

        tools_used: List[str] = []
        iterations = 0
        if getattr(agent, "enable_evaluation", False) and getattr(
            agent, "evaluator", None
        ):
            history = getattr(agent.evaluator, "executions_history", [])
            if history:
                latest = history[-1]
                tools_used = list(getattr(latest, "tools_used", []) or [])
                iterations = int(getattr(latest, "iterations", 0) or 0)

        required_tools = task.get("required_tools", [])
        for required in required_tools:
            if required not in tools_used:
                failures.append(f"Required tool not used: {required}")

        success = len(failures) == 0

        return TaskResult(
            task_id=task_id,
            category=category,
            success=success,
            duration_sec=duration_sec,
            answer=answer,
            failures=failures,
            tools_used=tools_used,
            iterations=iterations,
        )


def evaluate_checks(answer: str, checks: List[Dict[str, str]]) -> List[str]:
    """Evaluate answer content against declarative checks."""
    failures: List[str] = []
    text = answer or ""

    for check in checks:
        check_type = check.get("type", "non_empty")

        if check_type == "non_empty":
            if not text.strip():
                failures.append("Expected non-empty answer")

        elif check_type == "contains":
            needle = check.get("value", "")
            if needle and needle not in text:
                failures.append(f"Expected answer to contain '{needle}'")

        elif check_type == "not_contains":
            needle = check.get("value", "")
            if needle and needle in text:
                failures.append(f"Expected answer to not contain '{needle}'")

        elif check_type == "regex":
            pattern = check.get("value", "")
            if pattern and not re.search(pattern, text):
                failures.append(f"Expected regex match '{pattern}'")

        else:
            failures.append(f"Unknown check type: {check_type}")

    return failures


def load_tasks(
    tasks_dir: Path,
    suite: str = "all",
    tasks_file: Optional[Path] = None,
    max_tasks: Optional[int] = None,
) -> List[TaskRecord]:
    """Load benchmark tasks from JSON files."""
    raw_tasks: List[TaskRecord] = []

    if tasks_file:
        with tasks_file.open("r", encoding="utf-8") as handle:
            raw = json.load(handle)
        if not isinstance(raw, list):
            raise ValueError("Tasks file must contain a JSON array")
        raw_tasks = raw
    else:
        for file_path in sorted(tasks_dir.glob("*.json")):
            with file_path.open("r", encoding="utf-8") as handle:
                payload = json.load(handle)
            if not isinstance(payload, list):
                raise ValueError(
                    f"Task file {file_path.name} must contain a JSON array"
                )
            raw_tasks.extend(payload)

    # Normalize and filter by suite/category.
    tasks = [
        task
        for task in raw_tasks
        if isinstance(task, dict) and "id" in task and "prompt" in task
    ]
    if suite != "all":
        tasks = [task for task in tasks if task.get("category") == suite]

    if max_tasks is not None and max_tasks >= 0:
        tasks = tasks[:max_tasks]

    return tasks


def save_report(report: Dict[str, Any], output_dir: Path) -> Path:
    """Save benchmark report to timestamped JSON file."""
    output_dir.mkdir(parents=True, exist_ok=True)
    timestamp = datetime.now(timezone.utc).strftime("%Y%m%dT%H%M%SZ")
    output_path = output_dir / f"capability_eval_{timestamp}.json"
    with output_path.open("w", encoding="utf-8") as handle:
        json.dump(report, handle, indent=2)
    return output_path


def print_report(report: Dict[str, Any]) -> None:
    """Print a concise terminal summary of benchmark results."""
    summary = report["summary"]
    print("\nCapability Benchmark Summary")
    print("=" * 32)
    print(f"Tasks: {report['task_count']}")
    print(f"Pass rate: {summary['pass_rate']:.1%}")
    print(f"Median duration: {summary['median_duration_sec']:.3f}s")

    print("\nBy category:")
    for category, stats in summary["categories"].items():
        print(
            f"- {category}: {stats['passed']}/{stats['total']} "
            f"({stats['pass_rate']:.1%})"
        )

    if summary["top_failures"]:
        print("\nTop failure reasons:")
        for failure, count in summary["top_failures"]:
            print(f"- {failure} ({count})")


def _summarize_results(results: List[TaskResult]) -> Dict[str, Any]:
    """Aggregate per-task results into summary metrics."""
    total = len(results)
    passed = sum(1 for result in results if result.success)
    durations = [result.duration_sec for result in results]

    categories: Dict[str, Dict[str, Any]] = {}
    failure_counts: Dict[str, int] = {}

    for result in results:
        bucket = categories.setdefault(result.category, {"total": 0, "passed": 0})
        bucket["total"] += 1
        if result.success:
            bucket["passed"] += 1

        for failure in result.failures:
            failure_counts[failure] = failure_counts.get(failure, 0) + 1

    for stats in categories.values():
        total_for_category = stats["total"]
        stats["pass_rate"] = (
            stats["passed"] / total_for_category if total_for_category else 0.0
        )

    return {
        "total": total,
        "passed": passed,
        "failed": total - passed,
        "pass_rate": (passed / total) if total else 0.0,
        "median_duration_sec": statistics.median(durations) if durations else 0.0,
        "categories": categories,
        "top_failures": sorted(
            failure_counts.items(), key=lambda item: item[1], reverse=True
        )[:5],
    }


def build_parser() -> argparse.ArgumentParser:
    """Create CLI parser for capability benchmark command."""
    parser = argparse.ArgumentParser(
        description="Run BladeRunner capability benchmarks"
    )
    parser.add_argument(
        "--suite",
        choices=["all", "software", "data", "research"],
        default="all",
        help="Run only one benchmark category",
    )
    parser.add_argument(
        "--tasks-dir",
        default="benchmarks/tasks",
        help="Directory containing task JSON files",
    )
    parser.add_argument(
        "--tasks-file",
        help="Specific task JSON file (overrides --tasks-dir glob)",
    )
    parser.add_argument("--model", help="Model alias/name to run benchmarks with")
    parser.add_argument(
        "--max-tasks",
        type=int,
        help="Cap number of tasks executed",
    )
    parser.add_argument(
        "--output-dir",
        default="benchmarks/results",
        help="Directory where JSON reports are written",
    )
    return parser


def main() -> None:
    """CLI entrypoint for capability benchmarks."""
    parser = build_parser()
    args = parser.parse_args()

    config = Config()
    tasks = load_tasks(
        tasks_dir=Path(args.tasks_dir),
        suite=args.suite,
        tasks_file=Path(args.tasks_file) if args.tasks_file else None,
        max_tasks=args.max_tasks,
    )

    if not tasks:
        raise SystemExit("No benchmark tasks found")

    runner = CapabilityBenchmarkRunner(config=config, model=args.model)
    report = runner.run(tasks)
    output_path = save_report(report, Path(args.output_dir))
    print_report(report)
    print(f"\nReport written to: {output_path}")


if __name__ == "__main__":
    main()

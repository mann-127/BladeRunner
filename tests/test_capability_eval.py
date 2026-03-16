"""Tests for capability benchmark runner."""

from pathlib import Path

from bladerunner.capability_eval import (
    CapabilityBenchmarkRunner,
    evaluate_checks,
    load_tasks,
)


class _FakeExecution:
    def __init__(self, tools_used=None, iterations=0):
        self.tools_used = tools_used or []
        self.iterations = iterations


class _FakeEvaluator:
    def __init__(self):
        self.executions_history = []


class _FakeAgent:
    def __init__(self, answer: str, tools_used=None, iterations: int = 1):
        self.enable_evaluation = True
        self.evaluator = _FakeEvaluator()
        self._answer = answer
        self._tools_used = tools_used or []
        self._iterations = iterations

    def execute(self, prompt: str) -> str:
        _ = prompt
        self.evaluator.executions_history.append(
            _FakeExecution(tools_used=self._tools_used, iterations=self._iterations)
        )
        return self._answer


class _FakeConfig:
    def get(self, key: str, default=None):
        _ = key
        return default


def test_evaluate_checks_variants() -> None:
    checks = [
        {"type": "non_empty"},
        {"type": "contains", "value": "BladeRunner"},
        {"type": "regex", "value": r"\d+"},
        {"type": "not_contains", "value": "forbidden"},
    ]

    failures = evaluate_checks("BladeRunner 2.0", checks)
    assert failures == []


def test_evaluate_checks_failure() -> None:
    checks = [{"type": "contains", "value": "missing"}]
    failures = evaluate_checks("hello", checks)
    assert len(failures) == 1
    assert "missing" in failures[0]


def test_load_tasks_from_suite_dir() -> None:
    tasks_dir = Path("benchmarks/tasks")
    tasks = load_tasks(tasks_dir=tasks_dir, suite="software")
    assert tasks
    assert all(task.get("category") == "software" for task in tasks)


def test_runner_success_case() -> None:
    tasks = [
        {
            "id": "t1",
            "category": "software",
            "prompt": "test",
            "checks": [{"type": "contains", "value": "ok"}],
            "required_tools": ["Read"],
            "max_duration_sec": 30,
        }
    ]

    def factory() -> _FakeAgent:
        return _FakeAgent("ok result", tools_used=["Read"], iterations=2)

    runner = CapabilityBenchmarkRunner(config=_FakeConfig(), agent_factory=factory)
    report = runner.run(tasks)

    assert report["summary"]["total"] == 1
    assert report["summary"]["passed"] == 1
    assert report["results"][0]["success"] is True
    assert report["results"][0]["iterations"] == 2


def test_runner_required_tool_failure() -> None:
    tasks = [
        {
            "id": "t2",
            "category": "software",
            "prompt": "test",
            "checks": [{"type": "non_empty"}],
            "required_tools": ["Bash"],
        }
    ]

    def factory() -> _FakeAgent:
        return _FakeAgent("response", tools_used=["Read"], iterations=1)

    runner = CapabilityBenchmarkRunner(config=_FakeConfig(), agent_factory=factory)
    report = runner.run(tasks)

    assert report["summary"]["failed"] == 1
    assert report["results"][0]["success"] is False
    assert "Required tool not used: Bash" in report["results"][0]["failures"]

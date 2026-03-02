"""Tests for evaluation and metrics tracking."""

import json
import time
from pathlib import Path
import tempfile
import pytest

from bladerunner.evaluation import AgentEvaluator, TaskExecution


def test_task_execution_creation():
    """Test TaskExecution dataclass."""
    task = TaskExecution(
        task_id="test_123",
        prompt="test prompt",
        start_time=time.time(),
    )
    assert task.task_id == "test_123"
    assert task.prompt == "test prompt"
    assert task.success is False
    assert task.iterations == 0
    assert task.tools_used == []


def test_task_execution_duration():
    """Test duration calculation."""
    start = time.time()
    task = TaskExecution(
        task_id="test_123",
        prompt="test",
        start_time=start,
        end_time=start + 5.0,
    )
    assert task.duration == pytest.approx(5.0, rel=0.1)


def test_evaluator_initialization():
    """Test AgentEvaluator initialization."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evaluator = AgentEvaluator(metrics_dir=Path(tmpdir))
        assert evaluator.current_execution is None
        assert len(evaluator.executions_history) == 0


def test_evaluator_task_lifecycle():
    """Test complete task lifecycle tracking."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evaluator = AgentEvaluator(metrics_dir=Path(tmpdir))

        # Start task
        task_id = evaluator.start_task("test prompt", "test-model")
        assert task_id.startswith("task_")
        assert evaluator.current_execution is not None
        assert evaluator.current_execution.prompt == "test prompt"

        # Record iterations
        evaluator.record_iteration()
        evaluator.record_iteration()
        assert evaluator.current_execution.iterations == 2

        # Record tool use
        evaluator.record_tool_use("Read")
        evaluator.record_tool_use("Bash")
        assert len(evaluator.current_execution.tools_used) == 2
        assert "Read" in evaluator.current_execution.tools_used

        # Record tokens
        evaluator.record_tokens(total=100, prompt=60, completion=40)
        assert evaluator.current_execution.total_tokens == 100

        # End task
        evaluator.end_task(success=True)
        assert evaluator.current_execution is None
        assert len(evaluator.executions_history) == 1

        # Check history
        completed = evaluator.executions_history[0]
        assert completed.success is True
        assert completed.iterations == 2
        assert completed.total_tokens == 100


def test_evaluator_summary_statistics():
    """Test summary statistics calculation."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evaluator = AgentEvaluator(metrics_dir=Path(tmpdir))

        # Add successful task
        evaluator.start_task("task 1", "model-a")
        evaluator.record_tool_use("Read")
        evaluator.record_tokens(total=100)
        evaluator.end_task(success=True)

        # Add failed task
        evaluator.start_task("task 2", "model-b")
        evaluator.record_tool_use("Write")
        evaluator.record_tokens(total=50)
        evaluator.end_task(success=False, error_message="test error")

        # Get summary
        summary = evaluator.get_summary()
        assert summary["total_tasks"] == 2
        assert summary["successful_tasks"] == 1
        assert summary["failed_tasks"] == 1
        assert summary["success_rate"] == 0.5
        assert summary["total_tokens_used"] == 150


def test_evaluator_recent_executions():
    """Test retrieval of recent executions."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evaluator = AgentEvaluator(metrics_dir=Path(tmpdir))

        # Add multiple tasks
        for i in range(5):
            evaluator.start_task(f"task {i}", "model")
            evaluator.end_task(success=True)

        recent = evaluator.get_recent_executions(n=3)
        assert len(recent) == 3
        # Most recent should be first
        assert recent[0]["prompt"] == "task 4"


def test_evaluator_persistence():
    """Test that evaluation data persists to disk."""
    with tempfile.TemporaryDirectory() as tmpdir:
        metrics_dir = Path(tmpdir)

        # Create and use evaluator
        evaluator1 = AgentEvaluator(metrics_dir=metrics_dir)
        evaluator1.start_task("persistent task", "model")
        evaluator1.end_task(success=True)

        # Check files were created
        assert (metrics_dir / "executions.jsonl").exists()
        assert (metrics_dir / "evaluation_summary.json").exists()

        # Load in new evaluator instance
        evaluator2 = AgentEvaluator(metrics_dir=metrics_dir)
        assert len(evaluator2.executions_history) == 1
        assert evaluator2.executions_history[0].prompt == "persistent task"


def test_evaluator_export():
    """Test metrics export functionality."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evaluator = AgentEvaluator(metrics_dir=Path(tmpdir))

        evaluator.start_task("export test", "model")
        evaluator.end_task(success=True)

        export_path = Path(tmpdir) / "test_export.json"
        result = evaluator.export_metrics(export_path)

        assert export_path.exists()
        assert "exported" in result.lower()

        # Verify export format
        with open(export_path) as f:
            data = json.load(f)
            assert "summary" in data
            assert "executions" in data
            assert len(data["executions"]) == 1


def test_evaluator_clear_history():
    """Test clearing evaluation history."""
    with tempfile.TemporaryDirectory() as tmpdir:
        evaluator = AgentEvaluator(metrics_dir=Path(tmpdir))

        evaluator.start_task("clear test", "model")
        evaluator.end_task(success=True)

        assert len(evaluator.executions_history) == 1

        evaluator.clear_history()
        assert len(evaluator.executions_history) == 0

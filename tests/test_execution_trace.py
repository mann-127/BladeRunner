"""Tests for structured execution trace recorder."""

from bladerunner.execution_trace import ExecutionTraceRecorder


def test_execution_trace_lifecycle() -> None:
    recorder = ExecutionTraceRecorder()

    recorder.start(prompt="hello", model="haiku")
    recorder.log("iteration_started", iteration=0)
    recorder.log("tool_executed", tool="Read")
    trace = recorder.finish(status="success", final_answer="done")

    assert trace["status"] == "success"
    assert trace["model"] == "haiku"
    assert len(trace["events"]) == 2
    assert trace["final_answer_preview"] == "done"


def test_execution_trace_compact_render() -> None:
    recorder = ExecutionTraceRecorder()
    recorder.start(prompt="p", model="m")
    recorder.log("execution_started")
    compact = recorder.render_compact()

    assert "status=running" in compact
    assert "events=1" in compact

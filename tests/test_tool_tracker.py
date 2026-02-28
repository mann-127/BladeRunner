from pathlib import Path

from bladerunner.tool_tracker import ToolTracker


def test_records_stats_and_persists_to_disk(tmp_path: Path) -> None:
    tracker = ToolTracker(tmp_path)

    tracker.record_execution("Read", success=True)
    tracker.record_execution("Read", success=True)
    tracker.record_execution("Read", success=False, error="Timeout: command stalled")

    assert tracker.get_success_rate("Read") == (2 / 3)
    assert (tmp_path / "tool_stats.json").exists()


def test_reliability_ranking_and_recommendation(tmp_path: Path) -> None:
    tracker = ToolTracker(tmp_path)

    tracker.record_execution("Write", success=True)
    tracker.record_execution("Write", success=True)
    tracker.record_execution("Write", success=True)

    tracker.record_execution("Bash", success=True)
    tracker.record_execution("Bash", success=False, error="RuntimeError: failed")
    tracker.record_execution("Bash", success=False, error="RuntimeError: failed")

    ranking = tracker.get_reliability_ranking()

    assert ranking[0]["tool"] == "Write"
    assert ranking[0]["success_rate"] == 1.0

    recommendation = tracker.get_recommendation()
    assert recommendation is not None
    assert "Write" in recommendation


def test_health_labels_cover_thresholds(tmp_path: Path) -> None:
    tracker = ToolTracker(tmp_path)

    tracker.record_execution("ToolA", success=True)
    tracker.record_execution("ToolA", success=True)
    tracker.record_execution("ToolA", success=False, error="ValueError: bad")

    tracker.record_execution("ToolB", success=True)
    tracker.record_execution("ToolB", success=True)
    tracker.record_execution("ToolB", success=True)

    health = tracker.get_tool_health()

    assert "ToolA" in health
    assert "ToolB" in health
    assert "67%" in health["ToolA"]
    assert "100%" in health["ToolB"]

"""Tests for adaptive strategy manager."""

from bladerunner.adaptive_strategy import AdaptiveStrategyManager


def test_adaptive_strategy_emits_guidance_after_threshold() -> None:
    manager = AdaptiveStrategyManager(failure_threshold=2)

    first = manager.record_tool_outcome("Bash", success=False, error_message="timeout")
    second = manager.record_tool_outcome("Bash", success=False, error_message="timeout")

    assert first is None
    assert second is not None
    assert "Bash" in second


def test_adaptive_strategy_resets_on_success() -> None:
    manager = AdaptiveStrategyManager(failure_threshold=2)

    manager.record_tool_outcome("Read", success=False)
    manager.record_tool_outcome("Read", success=True)

    guidance = manager.get_active_guidance()
    assert guidance == ""

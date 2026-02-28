"""Integration-style pytest coverage for core framework behavior."""

from pathlib import Path

from bladerunner.agent_orchestrator import AgentOrchestrator, AgentRole
from bladerunner.config import Config
from bladerunner.semantic_memory import SemanticMemory, SimpleTextSimilarity
from bladerunner.safety import CriticalOperation
from bladerunner.tool_tracker import ToolTracker


def test_core_imports() -> None:
    from bladerunner.agent import Agent
    from bladerunner.cli import main
    from bladerunner.sessions import SessionManager

    assert Agent is not None
    assert main is not None
    assert SessionManager is not None


def test_tier2_imports() -> None:
    assert CriticalOperation is not None
    assert ToolTracker is not None
    assert SemanticMemory is not None
    assert SimpleTextSimilarity is not None
    assert AgentOrchestrator is not None
    assert AgentRole is not None


def test_tier2_instantiation(tmp_path: Path) -> None:
    safety = CriticalOperation()
    tracker = ToolTracker(tmp_path / "metrics")
    memory = SemanticMemory(tmp_path / "memory")
    orchestrator = AgentOrchestrator()

    assert safety is not None
    assert tracker is not None
    assert memory is not None
    assert orchestrator is not None


def test_tier2_features(tmp_path: Path) -> None:
    safety = CriticalOperation()
    tracker = ToolTracker(tmp_path / "metrics")
    orchestrator = AgentOrchestrator()

    is_critical, reason = safety.is_critical_bash("rm -rf /data")
    assert is_critical is True
    assert reason is not None

    similarity = SimpleTextSimilarity.jaccard_similarity("test code", "code test")
    assert similarity == 1.0

    tracker.record_execution("TestTool", success=True, error=None)
    assert tracker.get_success_rate("TestTool") == 1.0

    selected = orchestrator.select_agent("write a python function for sorting")
    assert selected is AgentRole.CODE


def test_configuration_defaults_from_missing_file(tmp_path: Path) -> None:
    config = Config(tmp_path / "missing-config.yml")

    assert config.get("model") == "haiku"
    assert config.get("backend") == "openrouter"
    assert config.get("agent") is not None

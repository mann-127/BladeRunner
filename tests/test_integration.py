"""Integration tests - Tests that verify components work together.

These tests check that multiple modules integrate correctly.
Unit tests for individual modules are in their respective test_*.py files.
"""

from pathlib import Path

from bladerunner.agent_orchestrator import AgentOrchestrator, AgentRole
from bladerunner.semantic_memory import SemanticMemory, SimpleTextSimilarity
from bladerunner.safety import CriticalOperation
from bladerunner.tool_tracker import ToolTracker
from bladerunner.tools.base import ToolRegistry
from bladerunner.tools.bash import BashTool
from bladerunner.tools.filesystem import ReadTool, WriteTool


def test_advanced_features_integration(tmp_path: Path) -> None:
    """Test that advanced features work together."""
    safety = CriticalOperation()
    tracker = ToolTracker(tmp_path / "metrics")
    orchestrator = AgentOrchestrator()

    # Safety checks dangerous commands
    is_critical, reason = safety.is_critical_bash("rm -rf /data")
    assert is_critical is True
    assert reason is not None

    # Similarity calculation
    similarity = SimpleTextSimilarity.jaccard_similarity("test code", "code test")
    assert similarity == 1.0

    # Tool tracking
    tracker.record_execution("TestTool", success=True, error=None)
    assert tracker.get_success_rate("TestTool") == 1.0

    # Agent selection
    selected = orchestrator.select_agent("write a python function for sorting")
    assert selected is AgentRole.CODE


def test_tool_registry_integration(tmp_path: Path) -> None:
    """Test that tool registry works with actual tools."""
    registry = ToolRegistry()

    # Register multiple tools
    registry.register(BashTool())
    registry.register(ReadTool())
    registry.register(WriteTool())

    # Verify registration
    assert registry.get("Bash") is not None
    assert registry.get("Read") is not None
    assert registry.get("Write") is not None

    # Get definitions for all
    definitions = registry.get_definitions()
    assert len(definitions) == 3

    # Test file operations through registry
    test_file = tmp_path / "test.txt"
    write_result = registry.execute("Write", file_path=str(test_file), content="Hello")
    assert "Success" in write_result

    read_result = registry.execute("Read", file_path=str(test_file))
    assert read_result == "Hello"


def test_semantic_memory_with_tool_tracker(tmp_path: Path) -> None:
    """Test that semantic memory and tool tracker work together."""
    memory = SemanticMemory(tmp_path / "memory")
    tracker = ToolTracker(tmp_path / "metrics")

    # Store solution with tool usage
    tools_used = ["Read", "Write", "Bash"]
    memory.store_solution(
        task_description="Create config file",
        execution_path=["read template", "modify", "write"],
        success=True,
    )

    # Track tool usage
    for tool in tools_used:
        tracker.record_execution(tool, success=True, error=None)

    # Verify integration with similar query
    # Use lower threshold to account for word overlap
    similar = memory.find_similar_solutions("Create a config file", threshold=0.2)
    assert len(similar) > 0

    # All tools should have 100% success
    for tool in tools_used:
        assert tracker.get_success_rate(tool) == 1.0

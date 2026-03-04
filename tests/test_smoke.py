"""Smoke tests - Quick sanity checks that the project can start.

These tests verify basic import ability and framework instantiation.
Detailed functionality tests are in their respective test_*.py files.
"""


def test_core_imports() -> None:
    """Test that core modules can be imported."""
    from bladerunner.agent import Agent
    from bladerunner.cli import main
    from bladerunner.config import Config
    from bladerunner.sessions import SessionManager
    from bladerunner.skills import SkillManager

    assert Agent is not None
    assert main is not None
    assert Config is not None
    assert SessionManager is not None
    assert SkillManager is not None


def test_tool_imports() -> None:
    """Test that tools can be imported."""
    from bladerunner.tools.bash import BashTool
    from bladerunner.tools.filesystem import ReadTool, WriteTool
    from bladerunner.tools.base import Tool, ToolRegistry

    assert BashTool is not None
    assert ReadTool is not None
    assert WriteTool is not None
    assert Tool is not None
    assert ToolRegistry is not None


def test_tier2_imports() -> None:
    """Test that tier 2 agentic features can be imported."""
    from bladerunner.safety import CriticalOperation
    from bladerunner.tool_tracker import ToolTracker
    from bladerunner.semantic_memory import SemanticMemory
    from bladerunner.agent_orchestrator import AgentOrchestrator
    from bladerunner.evaluation import AgentEvaluator

    assert CriticalOperation is not None
    assert ToolTracker is not None
    assert SemanticMemory is not None
    assert AgentOrchestrator is not None
    assert AgentEvaluator is not None

"""Smoke tests — quick sanity checks that the project can start."""


def test_core_imports():
    from bladerunner.agent import Agent
    from bladerunner.cli import main
    from bladerunner.config import Config
    from bladerunner.sessions import SessionManager

    assert Agent is not None
    assert main is not None
    assert Config is not None
    assert SessionManager is not None


def test_tool_imports():
    from bladerunner.tools.base import Tool, ToolRegistry
    from bladerunner.tools.bash import BashTool
    from bladerunner.tools.filesystem import ReadTool, WriteTool

    assert BashTool is not None
    assert ReadTool is not None
    assert WriteTool is not None
    assert Tool is not None
    assert ToolRegistry is not None


def test_safety_imports():
    from bladerunner.permissions import PermissionChecker, PermissionLevel
    from bladerunner.safety import CriticalOperation, Safety

    assert Safety is not None
    assert CriticalOperation is not None
    assert PermissionChecker is not None
    assert PermissionLevel is not None


def test_memory_import():
    from bladerunner.memory import Memory

    assert Memory is not None


def test_api_import():
    from bladerunner.api import create_app

    assert create_app is not None

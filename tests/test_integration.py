"""Integration tests — verify components work together."""

from bladerunner.safety import CriticalOperation
from bladerunner.tools.base import ToolRegistry
from bladerunner.tools.bash import BashTool
from bladerunner.tools.filesystem import ReadTool, WriteTool


def test_safety_detects_critical_bash():
    safety = CriticalOperation()

    is_critical, reason = safety.is_critical_bash("rm -rf /data")

    assert is_critical is True
    assert reason is not None


def test_tool_registry_integration(tmp_path):
    registry = ToolRegistry()
    registry.register(BashTool())
    registry.register(ReadTool())
    registry.register(WriteTool())

    assert registry.get("Bash") is not None
    assert registry.get("Read") is not None
    assert registry.get("Write") is not None

    definitions = registry.get_definitions()
    assert len(definitions) == 3

    test_file = tmp_path / "test.txt"
    write_result = registry.execute("Write", file_path=str(test_file), content="Hello")
    assert "Success" in write_result

    read_result = registry.execute("Read", file_path=str(test_file))
    assert read_result == "Hello"


def test_safety_and_registry_work_together(tmp_path):
    safety = CriticalOperation()
    registry = ToolRegistry()
    registry.register(ReadTool())
    registry.register(WriteTool())

    # Safety allows normal file operations
    is_critical, _ = safety.is_critical_file_write(str(tmp_path / "output.txt"))
    assert is_critical is False

    # And the registry can execute them
    test_file = tmp_path / "output.txt"
    result = registry.execute("Write", file_path=str(test_file), content="test")
    assert "Success" in result

"""Tests for base tool classes and registry."""

from bladerunner.tools.base import Tool, ToolRegistry
from typing import Any, Dict


class MockTool(Tool):
    """Mock tool for testing."""

    @property
    def name(self) -> str:
        return "MockTool"

    @property
    def description(self) -> str:
        return "A mock tool for testing"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["input"],
            "properties": {"input": {"type": "string", "description": "Test input"}},
        }

    def execute(self, input: str) -> str:
        return f"Mock result: {input}"


class FailingTool(Tool):
    """Tool that always fails for error testing."""

    @property
    def name(self) -> str:
        return "FailingTool"

    @property
    def description(self) -> str:
        return "A tool that fails"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "properties": {},
        }

    def execute(self) -> str:
        raise RuntimeError("Intentional failure")


def test_tool_to_definition_format() -> None:
    """Tool should convert to OpenAI function definition format."""
    tool = MockTool()
    definition = tool.to_definition()

    assert definition["type"] == "function"
    assert definition["function"]["name"] == "MockTool"
    assert definition["function"]["description"] == "A mock tool for testing"
    assert "parameters" in definition["function"]
    assert definition["function"]["parameters"]["required"] == ["input"]


def test_tool_registry_registration() -> None:
    """Tools should be registered and retrievable."""
    registry = ToolRegistry()
    tool = MockTool()

    registry.register(tool)

    retrieved = registry.get("MockTool")
    assert retrieved is not None
    assert retrieved.name == "MockTool"


def test_tool_registry_get_definitions() -> None:
    """Registry should provide all tool definitions."""
    registry = ToolRegistry()
    registry.register(MockTool())

    definitions = registry.get_definitions()

    assert len(definitions) == 1
    assert definitions[0]["function"]["name"] == "MockTool"


def test_tool_registry_execute_by_name() -> None:
    """Registry should execute tools by name."""
    registry = ToolRegistry()
    registry.register(MockTool())

    result = registry.execute("MockTool", input="test")

    assert result == "Mock result: test"


def test_tool_registry_handles_unknown_tool() -> None:
    """Registry should handle unknown tool gracefully."""
    registry = ToolRegistry()

    result = registry.execute("NonExistent", input="test")

    assert "Error: Unknown tool" in result
    assert "NonExistent" in result


def test_tool_registry_handles_invalid_arguments() -> None:
    """Registry should handle invalid arguments."""
    registry = ToolRegistry()
    registry.register(MockTool())

    # Missing required argument
    result = registry.execute("MockTool")

    assert "Error: Invalid arguments" in result


def test_tool_registry_handles_execution_errors() -> None:
    """Registry should catch and report execution errors."""
    registry = ToolRegistry()
    registry.register(FailingTool())

    result = registry.execute("FailingTool")

    assert "Error executing" in result
    assert "Intentional failure" in result


def test_tool_registry_multiple_tools() -> None:
    """Registry should handle multiple tools."""
    registry = ToolRegistry()

    tool1 = MockTool()
    tool2 = FailingTool()

    registry.register(tool1)
    registry.register(tool2)

    assert registry.get("MockTool") is not None
    assert registry.get("FailingTool") is not None
    assert len(registry.get_definitions()) == 2

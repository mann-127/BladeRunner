"""Base tool classes."""

from abc import ABC, abstractmethod
from typing import Any, Dict, List, Optional


class Tool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Tool name."""
        pass

    @property
    @abstractmethod
    def description(self) -> str:
        """Tool description."""
        pass

    @property
    @abstractmethod
    def parameters(self) -> Dict[str, Any]:
        """Tool parameters schema."""
        pass

    @abstractmethod
    def execute(self, **kwargs) -> str:
        """Execute the tool."""
        pass

    def to_definition(self) -> Dict[str, Any]:
        """Convert to OpenAI tool definition format."""
        return {
            "type": "function",
            "function": {
                "name": self.name,
                "description": self.description,
                "parameters": self.parameters,
            },
        }


class ToolRegistry:
    """Registry for managing tools."""

    def __init__(self):
        self.tools: Dict[str, Tool] = {}

    def register(self, tool: Tool):
        """Register a tool."""
        self.tools[tool.name] = tool

    def get(self, name: str) -> Optional[Tool]:
        """Get a tool by name."""
        return self.tools.get(name)

    def get_definitions(self) -> List[Dict[str, Any]]:
        """Get all tool definitions."""
        return [tool.to_definition() for tool in self.tools.values()]

    def execute(self, name: str, **kwargs) -> str:
        """Execute a tool by name."""
        tool = self.get(name)
        if tool is None:
            return f"Error: Unknown tool '{name}'"

        try:
            return tool.execute(**kwargs)
        except TypeError as e:
            return f"Error: Invalid arguments for {name}: {str(e)}"
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

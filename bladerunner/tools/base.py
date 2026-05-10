"""Base tool classes."""

from abc import ABC, abstractmethod


class Tool(ABC):
    """Base class for all tools."""

    @property
    @abstractmethod
    def name(self):
        pass

    @property
    @abstractmethod
    def description(self):
        pass

    @property
    @abstractmethod
    def parameters(self):
        pass

    @abstractmethod
    def execute(self, **kwargs):
        pass

    def to_definition(self):
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
        self.tools = {}

    def register(self, tool):
        self.tools[tool.name] = tool

    def get(self, name):
        return self.tools.get(name)

    def get_definitions(self):
        return [tool.to_definition() for tool in self.tools.values()]

    def execute(self, name, **kwargs):
        tool = self.get(name)
        if tool is None:
            return f"Error: Unknown tool '{name}'"
        # Validate required parameters from the tool's schema (if provided)
        params = tool.parameters or {}
        if isinstance(params, dict):
            required = params.get("required", [])
            if isinstance(required, list) and required:
                missing = [r for r in required if r not in kwargs]
                if missing:
                    missing_str = ", ".join(missing)
                    return f"Error: Invalid arguments for {name}: missing {missing_str}"

        try:
            return tool.execute(**kwargs)
        except TypeError as e:
            return f"Error: Invalid arguments for {name}: {str(e)}"
        except Exception as e:
            return f"Error executing {name}: {str(e)}"

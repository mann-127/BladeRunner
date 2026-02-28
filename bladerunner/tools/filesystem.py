"""Filesystem tools (Read, Write)."""

from pathlib import Path
from typing import Any, Dict
from .base import Tool

DEFAULT_ENCODING = "utf-8"


class ReadTool(Tool):
    """Read file content."""

    @property
    def name(self) -> str:
        return "Read"

    @property
    def description(self) -> str:
        return "Read and return content of a file"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["file_path"],
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to read from",
                }
            },
        }

    def execute(self, file_path: str) -> str:
        """Read file with proper error handling and encoding."""
        try:
            path = Path(file_path)
            return path.read_text(encoding=DEFAULT_ENCODING)
        except FileNotFoundError:
            return f"Error: File '{file_path}' not found"
        except PermissionError:
            return f"Error: Permission denied reading '{file_path}'"
        except Exception as e:
            return f"Error reading file: {str(e)}"


class WriteTool(Tool):
    """Write content to file."""

    @property
    def name(self) -> str:
        return "Write"

    @property
    def description(self) -> str:
        return "Write content to a file"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["file_path", "content"],
            "properties": {
                "file_path": {
                    "type": "string",
                    "description": "The path to the file to write to",
                },
                "content": {
                    "type": "string",
                    "description": "The content to write to the file",
                },
            },
        }

    def execute(self, file_path: str, content: str) -> str:
        """Write file with proper error handling and encoding."""
        try:
            path = Path(file_path)
            path.parent.mkdir(parents=True, exist_ok=True)
            path.write_text(content, encoding=DEFAULT_ENCODING)
            return f"Successfully wrote to {file_path}"
        except PermissionError:
            return f"Error: Permission denied writing to '{file_path}'"
        except Exception as e:
            return f"Error writing file: {str(e)}"

"""Bash command execution tool."""

import subprocess
from typing import Any, Dict
from .base import Tool

SUBPROCESS_TIMEOUT = 30
DEFAULT_ENCODING = "utf-8"


class BashTool(Tool):
    """Execute bash commands."""

    @property
    def name(self) -> str:
        return "Bash"

    @property
    def description(self) -> str:
        return "Execute a shell command"

    @property
    def parameters(self) -> Dict[str, Any]:
        return {
            "type": "object",
            "required": ["command"],
            "properties": {
                "command": {"type": "string", "description": "The command to execute"}
            },
        }

    def execute(self, command: str) -> str:
        """Execute bash command with security and timeout considerations."""
        try:
            result = subprocess.run(
                command,
                shell=True,
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
                encoding=DEFAULT_ENCODING,
            )

            # Combine stdout and stderr
            output = result.stdout
            if result.stderr:
                output += result.stderr

            # Include exit code information for debugging
            if result.returncode != 0:
                output += f"\n(Exit code: {result.returncode})"

            return output if output else "Command executed successfully"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {SUBPROCESS_TIMEOUT} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"

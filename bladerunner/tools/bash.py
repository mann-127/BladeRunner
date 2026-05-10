"""Bash command execution tool."""

import subprocess

from .base import Tool

SUBPROCESS_TIMEOUT = 30
DEFAULT_ENCODING = "utf-8"


class BashTool(Tool):
    """Execute bash commands."""

    @property
    def name(self):
        return "Bash"

    @property
    def description(self):
        return "Execute a shell command"

    @property
    def parameters(self):
        return {
            "type": "object",
            "required": ["command"],
            "properties": {"command": {"type": "string", "description": "The command to execute"}},
        }

    def execute(self, command):
        """Execute bash command with security and timeout considerations.

        Uses ["bash", "-c", command] instead of shell=True to make the shell
        invocation explicit. Security is enforced by the permission layer
        (PermissionChecker + CriticalOperation) before this method is called.
        """
        try:
            result = subprocess.run(
                ["bash", "-c", command],
                capture_output=True,
                text=True,
                timeout=SUBPROCESS_TIMEOUT,
                encoding=DEFAULT_ENCODING,
            )

            output = result.stdout
            if result.stderr:
                output += result.stderr

            if result.returncode != 0:
                output += f"\n(Exit code: {result.returncode})"

            return output if output else "Command executed successfully"
        except subprocess.TimeoutExpired:
            return f"Error: Command timed out after {SUBPROCESS_TIMEOUT} seconds"
        except Exception as e:
            return f"Error executing command: {str(e)}"

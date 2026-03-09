"""Tests for bash command execution tool."""

from bladerunner.tools.bash import BashTool, SUBPROCESS_TIMEOUT


def test_bash_tool_executes_simple_command() -> None:
    """BashTool should execute simple commands."""
    tool = BashTool()
    result = tool.execute(command="echo 'Hello, Bash!'")

    assert "Hello, Bash!" in result


def test_bash_tool_captures_stdout() -> None:
    """BashTool should capture standard output."""
    tool = BashTool()
    result = tool.execute(command="echo 'test output'")

    assert "test output" in result


def test_bash_tool_captures_stderr() -> None:
    """BashTool should capture standard error."""
    tool = BashTool()
    # Force error output
    result = tool.execute(command="echo 'error message' >&2")

    assert "error message" in result


def test_bash_tool_reports_exit_code_on_failure() -> None:
    """BashTool should report exit code for failed commands."""
    tool = BashTool()
    # False command returns exit code 1
    result = tool.execute(command="false")

    assert "Exit code:" in result
    assert "1" in result


def test_bash_tool_handles_nonexistent_command() -> None:
    """BashTool should handle nonexistent commands."""
    tool = BashTool()
    result = tool.execute(command="nonexistent_command_xyz123")

    assert "Exit code:" in result or "not found" in result


def test_bash_tool_handles_multiline_output() -> None:
    """BashTool should handle commands with multiline output."""
    tool = BashTool()
    result = tool.execute(command="echo 'line1'; echo 'line2'; echo 'line3'")

    assert "line1" in result
    assert "line2" in result
    assert "line3" in result


def test_bash_tool_handles_timeout() -> None:
    """BashTool should timeout long-running commands."""
    tool = BashTool()
    # Sleep longer than timeout
    result = tool.execute(command=f"sleep {SUBPROCESS_TIMEOUT + 5}")

    assert "Error: Command timed out" in result
    assert str(SUBPROCESS_TIMEOUT) in result


def test_bash_tool_handles_empty_output() -> None:
    """BashTool should handle commands with no output."""
    tool = BashTool()
    result = tool.execute(command="true")

    assert "successfully" in result.lower() or result == ""


def test_bash_tool_preserves_exit_status() -> None:
    """BashTool should preserve and report exit status."""
    tool = BashTool()

    # Success
    result = tool.execute(command="exit 0")
    assert "Exit code: 0" not in result  # Only shown on non-zero

    # Failure with specific code
    result = tool.execute(command="exit 42")
    assert "Exit code: 42" in result


def test_bash_tool_definition() -> None:
    """BashTool should have proper definition."""
    tool = BashTool()

    assert tool.name == "Bash"
    assert "command" in tool.description.lower() or "shell" in tool.description.lower()
    assert "command" in tool.parameters["properties"]
    assert tool.parameters["required"] == ["command"]


def test_bash_tool_handles_pipes_and_redirects() -> None:
    """BashTool should handle shell pipes and redirects."""
    tool = BashTool()
    result = tool.execute(command="echo 'hello world' | grep 'world'")

    assert "world" in result


def test_bash_tool_handles_command_substitution() -> None:
    """BashTool should handle command substitution."""
    tool = BashTool()
    result = tool.execute(command="echo $(echo 'nested')")

    assert "nested" in result

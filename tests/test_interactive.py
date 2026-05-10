"""Tests for interactive mode."""

from unittest.mock import Mock

from bladerunner.interactive import INTERACTIVE_AVAILABLE, InteractiveMode


def test_interactive_imports_available():
    """Interactive mode dependencies should be available."""
    assert INTERACTIVE_AVAILABLE is True


def test_interactive_mode_initialization():
    """InteractiveMode should initialize with agent."""
    mock_agent = Mock()

    mode = InteractiveMode(mock_agent)

    assert mode.agent is mock_agent
    assert mode.active is True


def test_interactive_mode_with_session_manager():
    """InteractiveMode should support session manager."""
    mock_agent = Mock()
    mock_session_manager = Mock()

    mode = InteractiveMode(mock_agent, mock_session_manager)

    assert mode.session_manager is mock_session_manager


def test_handle_help_command():
    """Interactive mode should handle /help command."""
    mock_agent = Mock()
    mode = InteractiveMode(mock_agent)

    # Should not raise
    mode.handle_command("/help")


def test_handle_exit_command():
    """Interactive mode should handle /exit command."""
    mock_agent = Mock()
    mode = InteractiveMode(mock_agent)

    mode.handle_command("/exit")

    assert mode.active is False


def test_handle_quit_command():
    """Interactive mode should handle /quit command."""
    mock_agent = Mock()
    mode = InteractiveMode(mock_agent)

    mode.handle_command("/quit")

    assert mode.active is False


def test_handle_clear_command():
    """Interactive mode should handle /clear command."""
    mock_agent = Mock()
    mock_agent.messages = [{"role": "user", "content": "test"}]
    mode = InteractiveMode(mock_agent)

    mode.handle_command("/clear")

    mock_agent.clear_history.assert_called_once()


def test_handle_history_command():
    """Interactive mode should handle /history command."""
    mock_agent = Mock()
    mock_agent.messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi"},
    ]
    mode = InteractiveMode(mock_agent)

    # Should not raise
    mode.handle_command("/history")


def test_handle_model_show_current():
    """Interactive mode should show current model with /model."""
    mock_agent = Mock()
    mock_agent.model = "haiku"
    mode = InteractiveMode(mock_agent)

    # Should not raise
    mode.handle_command("/model")


def test_handle_model_switch():
    """Interactive mode should switch model with /model <name>."""
    mock_agent = Mock()
    mode = InteractiveMode(mock_agent)

    mode.handle_command("/model sonnet")

    mock_agent.set_model.assert_called_once_with("sonnet")


def test_handle_unknown_command():
    """Interactive mode should handle unknown commands gracefully."""
    mock_agent = Mock()
    mode = InteractiveMode(mock_agent)

    # Should not raise
    mode.handle_command("/unknown")


def test_show_history_with_empty_messages():
    """show_history should handle empty message list."""
    mock_agent = Mock()
    mock_agent.messages = []
    mode = InteractiveMode(mock_agent)

    # Should not raise
    mode.show_history()


def test_interactive_mode_maintains_session_state():
    """InteractiveMode should track session state."""
    mock_agent = Mock()
    mode = InteractiveMode(mock_agent)

    assert mode.current_session_id is None

    # Simulate setting session
    mode.current_session_id = "test-session-123"
    assert mode.current_session_id == "test-session-123"

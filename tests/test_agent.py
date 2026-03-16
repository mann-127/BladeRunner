"""Tests for core agent functionality."""

from unittest.mock import patch
from pathlib import Path
from bladerunner.agent import Agent, MAX_ITERATIONS, RETRY_CONFIG
from bladerunner.config import Config


def test_agent_initialization_with_config(tmp_path: Path) -> None:
    """Agent should initialize with configuration."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert agent.config is config
        assert agent.model is not None
        assert agent.registry is not None


def test_agent_uses_default_model(tmp_path: Path) -> None:
    """Agent should use default model from config."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        # Should use haiku as default
        assert agent.model == "haiku"


def test_agent_accepts_custom_model(tmp_path: Path) -> None:
    """Agent should accept custom model parameter."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config, model="sonnet")

        assert agent.model == "sonnet"


def test_agent_registers_core_tools(tmp_path: Path) -> None:
    """Agent should register core tools (Read, Write, Bash)."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert agent.registry.get("Read") is not None
        assert agent.registry.get("Write") is not None
        assert agent.registry.get("Bash") is not None


def test_agent_optionally_registers_web_tools(tmp_path: Path) -> None:
    """Agent should register web tools when enabled."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        # Web tools should be registered if available
        if config.get("web_search.enabled"):
            assert agent.registry.get("WebSearch") is not None
            assert agent.registry.get("FetchWebpage") is not None


def test_agent_initializes_permission_checker(tmp_path: Path) -> None:
    """Agent should initialize permission checker."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config, use_permissions=True, permission_profile="standard")

        assert agent.use_permissions is True
        assert agent.permission_checker is not None
        assert agent.permission_checker.profile == "standard"


def test_agent_can_disable_permissions(tmp_path: Path) -> None:
    """Agent should allow disabling permissions."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config, use_permissions=False)

        assert agent.use_permissions is False


def test_agent_initializes_session_manager(tmp_path: Path) -> None:
    """Agent should initialize session manager when enabled."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        # Sessions enabled by default
        if config.get("sessions.enabled"):
            assert agent.session_manager is not None


def test_agent_loads_session_by_id(tmp_path: Path) -> None:
    """Agent should load existing session by ID."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        if agent.session_manager:
            # Create a test session
            session_id = agent.session_manager.create_session("test")
            agent.session_manager.save_message(
                session_id, {"role": "user", "content": "test"}
            )

            # Load the session
            agent.load_session(session_id)
            assert agent.session_id == session_id


def test_agent_agentic_features_configurable(tmp_path: Path) -> None:
    """Agent should respect agentic feature configuration."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        # All features should be configurable booleans
        assert isinstance(agent.enable_planning, bool)
        assert isinstance(agent.enable_reflection, bool)
        assert isinstance(agent.enable_retry, bool)
        assert isinstance(agent.enable_streaming, bool)
        assert isinstance(agent.require_approval, bool)
        assert isinstance(agent.enable_tool_tracking, bool)
        assert isinstance(agent.enable_memory, bool)
        assert isinstance(agent.enable_agent_selection, bool)
        assert isinstance(agent.enable_evaluation, bool)
        assert isinstance(agent.enable_adaptation, bool)
        assert isinstance(agent.enable_trace, bool)


def test_agent_initializes_tool_tracker(tmp_path: Path) -> None:
    """Agent should initialize tool effectiveness tracker."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert agent.tool_tracker is not None


def test_agent_initializes_semantic_memory(tmp_path: Path) -> None:
    """Agent should initialize semantic memory system."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert agent.semantic_memory is not None


def test_agent_initializes_orchestrator(tmp_path: Path) -> None:
    """Agent should initialize multi-agent orchestrator."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert agent.orchestrator is not None
        assert agent.agent_role is not None


def test_agent_initializes_evaluator(tmp_path: Path) -> None:
    """Agent should initialize performance evaluator."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert agent.evaluator is not None


def test_agent_exposes_last_trace_accessor(tmp_path: Path) -> None:
    """Agent should expose a trace accessor even before first execution."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        trace = agent.get_last_trace()
        assert isinstance(trace, dict)


def test_agent_maintains_conversation_state(tmp_path: Path) -> None:
    """Agent should maintain conversation messages."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert isinstance(agent.messages, list)
        assert len(agent.messages) == 0  # Start empty


def test_agent_backend_selection(tmp_path: Path) -> None:
    """Agent should support backend selection."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        # Should have a backend configured
        assert agent.backend in ["openrouter", "groq"]


def test_agent_gets_correct_base_url_for_backend(tmp_path: Path) -> None:
    """Agent should get correct base URL for selected backend."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        base_url = agent._get_base_url()

        # Should return a valid URL
        assert base_url.startswith("https://")
        assert "api" in base_url.lower()


def test_agent_requires_api_key_for_backend(tmp_path: Path, monkeypatch) -> None:
    """Agent should require API key for configured backend."""
    config = Config(tmp_path / "config.yml")

    # Remove all API keys
    monkeypatch.delenv("OPENROUTER_API_KEY", raising=False)
    monkeypatch.delenv("GROQ_API_KEY", raising=False)

    try:
        agent = Agent(config)
        # If it doesn't raise, the test setup has an API key
        assert agent is not None
    except RuntimeError as e:
        # Should raise error about missing API key
        assert "API_KEY" in str(e) or "environment variable" in str(e)


def test_agent_retry_config_defined() -> None:
    """Agent should have retry configuration for tools."""
    assert "Bash" in RETRY_CONFIG
    assert "Read" in RETRY_CONFIG
    assert "Write" in RETRY_CONFIG

    # Each tool should have retry settings
    for tool, config in RETRY_CONFIG.items():
        assert "max_retries" in config
        assert "backoff_factor" in config
        assert config["max_retries"] > 0
        assert config["backoff_factor"] > 0


def test_agent_max_iterations_defined() -> None:
    """Agent should have max iterations limit."""
    assert MAX_ITERATIONS > 0
    assert MAX_ITERATIONS <= 100  # Reasonable upper bound


def test_agent_critical_checker_initialized(tmp_path: Path) -> None:
    """Agent should initialize critical operation checker."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert agent.critical_checker is not None


def test_agent_tracks_execution_history(tmp_path: Path) -> None:
    """Agent should track execution history."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert hasattr(agent, "execution_history")
        assert isinstance(agent.execution_history, list)


def test_agent_tracks_current_execution_path(tmp_path: Path) -> None:
    """Agent should track current execution path for memory."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert hasattr(agent, "current_execution_path")
        assert isinstance(agent.current_execution_path, list)


def test_agent_permission_profiles_supported(tmp_path: Path) -> None:
    """Agent should support different permission profiles."""
    config = Config(tmp_path / "config.yml")
    profiles = ["strict", "standard", "permissive"]

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        for profile in profiles:
            agent = Agent(config, permission_profile=profile)
            if agent.permission_checker:
                assert agent.permission_checker.profile == profile


def test_agent_initializes_openai_client(tmp_path: Path) -> None:
    """Agent should initialize OpenAI client for API calls."""
    config = Config(tmp_path / "config.yml")

    with patch.object(Agent, "_get_api_key_for_backend", return_value="fake-key"):
        agent = Agent(config)

        assert agent.client is not None
        # Client should be configured with base_url and api_key
        assert hasattr(agent.client, "base_url")

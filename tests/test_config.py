"""Tests for config module."""

from pathlib import Path
from bladerunner.config import Config


def test_config_loads_defaults_when_file_missing() -> None:
    """Config should use defaults when file doesn't exist."""
    config = Config(Path("/nonexistent/config.yml"))
    
    assert config.get("model") == "haiku"
    assert config.get("debug") is False
    assert config.get("agent.enable_planning") is True


def test_config_get_nested_keys() -> None:
    """Config should support nested key access with dot notation."""
    config = Config()
    
    assert config.get("agent.enable_planning") is True
    assert config.get("agent.require_approval") is True
    assert config.get("permissions.enabled") is True


def test_config_get_with_default() -> None:
    """Config should return default value for missing keys."""
    config = Config()
    
    assert config.get("nonexistent.key", "default") == "default"
    assert config.get("also.missing", 42) == 42


def test_config_resolve_model_haiku() -> None:
    """Config should resolve haiku alias to full model name."""
    config = Config()
    
    full_name = config.resolve_model("haiku")
    assert "anthropic" in full_name.lower()
    assert "haiku" in full_name.lower()


def test_config_resolve_model_sonnet() -> None:
    """Config should resolve sonnet alias to full model name."""
    config = Config()
    
    full_name = config.resolve_model("sonnet")
    assert "anthropic" in full_name.lower()
    assert "sonnet" in full_name.lower()


def test_config_resolve_model_llama() -> None:
    """Config should resolve llama alias to full model name."""
    config = Config()
    
    full_name = config.resolve_model("llama")
    assert "llama" in full_name.lower()


def test_config_resolve_model_passes_through_full_names() -> None:
    """Config should pass through full model names unchanged."""
    config = Config()
    
    full_name = "anthropic/claude-3-opus-20240229"
    assert config.resolve_model(full_name) == full_name


def test_config_backend_selection() -> None:
    """Config should have backend configuration."""
    config = Config()
    
    backends = config.get("backends")
    assert "openrouter" in backends
    assert "groq" in backends
    assert "base_url" in backends["openrouter"]
    assert "api_key_env" in backends["openrouter"]


def test_config_model_settings() -> None:
    """Config should have model-specific settings."""
    config = Config()
    
    models = config.get("models")
    assert "haiku" in models
    assert "full_name" in models["haiku"]
    assert "temperature" in models["haiku"]
    assert "max_tokens" in models["haiku"]


def test_config_permission_profiles() -> None:
    """Config should define permission profiles."""
    config = Config()
    
    assert config.get("permissions.enabled") is True
    assert config.get("permissions.profile") in ["strict", "standard", "permissive"]


def test_config_agentic_features_enabled() -> None:
    """Config should have all agentic features configurable."""
    config = Config()
    
    # Tier 1
    assert isinstance(config.get("agent.enable_planning"), bool)
    assert isinstance(config.get("agent.enable_reflection"), bool)
    assert isinstance(config.get("agent.enable_retry"), bool)
    assert isinstance(config.get("agent.enable_streaming"), bool)
    
    # Tier 2
    assert isinstance(config.get("agent.require_approval"), bool)
    assert isinstance(config.get("agent.enable_tool_tracking"), bool)
    assert isinstance(config.get("agent.enable_memory"), bool)
    assert isinstance(config.get("agent.enable_agent_selection"), bool)
    assert isinstance(config.get("agent.enable_adaptation"), bool)
    assert isinstance(config.get("agent.adaptation_failure_threshold"), int)
    assert isinstance(config.get("agent.enable_trace"), bool)


def test_config_sessions_enabled_by_default() -> None:
    """Config should enable sessions by default."""
    config = Config()
    
    assert config.get("sessions.enabled") is True


def test_config_web_search_settings() -> None:
    """Config should have web search configuration."""
    config = Config()
    
    # Web search is disabled by default (enabled in example.yml)
    assert isinstance(config.get("web_search.enabled"), bool)
    assert config.get("web_search.provider") == "duckduckgo"
    assert isinstance(config.get("web_search.max_results"), int)


def test_config_rag_settings() -> None:
    """Config should have RAG configuration."""
    config = Config()
    
    # RAG is not in default config (only when config.yml is used)
    # Check that it's either a bool or None
    rag_enabled = config.get("rag.enabled")
    assert rag_enabled is None or isinstance(rag_enabled, bool)


def test_config_logging_settings() -> None:
    """Config should expose logging defaults."""
    config = Config()

    assert config.get("logging.level") == "INFO"
    assert isinstance(config.get("logging.format"), str)
    assert isinstance(config.get("logging.uvicorn_access_log"), bool)

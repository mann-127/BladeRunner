"""Tests for config module."""

from pathlib import Path

from bladerunner.config import Config


def test_config_loads_defaults_when_file_missing():
    config = Config(Path("/nonexistent/config.yml"))

    assert config.get("model") == "gemma"
    assert config.get("debug") is False


def test_config_get_nested_keys():
    config = Config()

    assert config.get("agent.require_approval") is True
    assert isinstance(config.get("agent.max_iterations"), int)
    assert isinstance(config.get("agent.max_history_messages"), int)


def test_config_get_with_default():
    config = Config()

    assert config.get("nonexistent.key", "default") == "default"
    assert config.get("also.missing", 42) == 42


def test_config_resolve_model_gemma():
    config = Config()

    full = config.resolve_model("gemma")
    assert "gemma" in full.lower()


def test_config_resolve_model_llama():
    config = Config()

    full = config.resolve_model("llama-70b")
    assert "meta-llama" in full.lower()
    assert full != "llama-70b"


def test_config_resolve_model_passes_through_full_names():
    config = Config()

    name = "anthropic/claude-3-opus-20240229"
    assert config.resolve_model(name) == name


def test_config_backend_selection():
    config = Config()

    backends = config.get("backends")
    assert "openrouter" in backends
    assert "groq" in backends
    assert "base_url" in backends["openrouter"]
    assert "api_key_env" in backends["openrouter"]


def test_config_model_settings():
    config = Config()

    models = config.get("models")
    assert "gemma" in models
    assert "full_name" in models["gemma"]


def test_config_get_model_settings_returns_defaults():
    config = Config()

    settings = config.get_model_settings("unknown-model")
    assert settings["temperature"] == 0.7
    assert settings["max_tokens"] == 2048


def test_config_sessions_enabled_by_default():
    config = Config()

    assert config.get("sessions.enabled") is True


def test_config_web_search_settings():
    config = Config()

    assert isinstance(config.get("web_search.enabled"), bool)
    assert config.get("web_search.provider") == "duckduckgo"
    assert isinstance(config.get("web_search.max_results"), int)


def test_config_rag_settings():
    config = Config()

    assert isinstance(config.get("rag.enabled"), bool)
    assert isinstance(config.get("rag.persist_directory"), str)
    assert config.get("rag.embedding_model") == "all-MiniLM-L6-v2"


def test_config_api_settings():
    config = Config()

    assert isinstance(config.get("api.cors_origins"), list)
    assert isinstance(config.get("api.chat_timeout_seconds"), float)
    users = config.get("api.auth.users", [])
    assert isinstance(users, list)


def test_config_logging_settings():
    config = Config()

    assert config.get("logging.level") == "INFO"
    assert isinstance(config.get("logging.format"), str)
    assert isinstance(config.get("logging.uvicorn_access_log"), bool)


def test_config_fork_is_independent():
    config = Config()
    forked = Config.fork(config)

    forked.config["model"] = "changed"
    assert config.get("model") != "changed"


def test_config_agent_memory_settings():
    config = Config()

    assert isinstance(config.get("agent.memory_enabled"), bool)
    assert isinstance(config.get("agent.memory_use_embeddings"), bool)
    assert config.get("agent.memory_embedding_model") == "all-MiniLM-L6-v2"

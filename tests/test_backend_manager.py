"""Tests for backend manager and automatic fallback."""

import os
import time
from unittest.mock import patch

import pytest

from bladerunner.backend_manager import BackendManager, BackendStatus


@pytest.fixture
def mock_env():
    """Mock environment with API keys for testing."""
    with patch.dict(
        os.environ,
        {
            "OPENROUTER_API_KEY": "test_openrouter_key",
            "GROQ_API_KEY": "test_groq_key",
        },
    ):
        yield


@pytest.fixture
def test_config():
    """Test configuration with multiple backends."""
    return {
        "backend": "openrouter",
        "backends": {
            "openrouter": {
                "base_url": "https://openrouter.ai/api/v1",
                "api_key_env": "OPENROUTER_API_KEY",
            },
            "groq": {
                "base_url": "https://api.groq.com/openai/v1",
                "api_key_env": "GROQ_API_KEY",
            },
        },
    }


def test_backend_manager_initialization(mock_env, test_config):
    """Test backend manager initializes with available backends."""
    manager = BackendManager(test_config, "openrouter")

    assert manager.primary_backend == "openrouter"
    assert "openrouter" in manager.backends
    assert "groq" in manager.backends
    assert manager.backends["openrouter"].available
    assert manager.backends["groq"].available


def test_backend_manager_no_api_key():
    """Test backend marked unavailable when API key missing."""
    config = {
        "backends": {
            "openrouter": {
                "api_key_env": "MISSING_KEY",
            },
        },
    }

    manager = BackendManager(config)
    assert "openrouter" in manager.backends
    assert not manager.backends["openrouter"].available


def test_get_backend_priority(mock_env, test_config):
    """Test backend priority returns primary first."""
    manager = BackendManager(test_config, "openrouter")

    priority = manager.get_backend_priority()
    assert priority[0] == "openrouter"
    assert "groq" in priority


def test_record_request_failure_sets_cooldown(mock_env, test_config):
    """Test recording failure sets cooldown period."""
    manager = BackendManager(test_config)

    manager.record_request_failure("openrouter", 429)

    status = manager.backends["openrouter"]
    assert status.available
    assert status.is_in_cooldown()
    assert status.failure_count == 1


def test_record_request_success_clears_failures(mock_env, test_config):
    """Test recording success clears failure state."""
    manager = BackendManager(test_config)

    # Record failures first
    manager.record_request_failure("openrouter", 429)
    assert manager.backends["openrouter"].available

    # Record success
    manager.record_request_success("openrouter")

    status = manager.backends["openrouter"]
    assert status.available
    assert status.failure_count == 0
    assert not status.is_in_cooldown()


def test_should_attempt_fallback_on_rate_limit(mock_env, test_config):
    """Test fallback triggered on rate limit errors."""
    manager = BackendManager(test_config)

    assert manager.should_attempt_fallback("openrouter", 429)
    assert manager.should_attempt_fallback("openrouter", 402)


def test_should_attempt_fallback_on_repeated_failures(mock_env, test_config):
    """Test fallback triggered after repeated failures."""
    manager = BackendManager(test_config)

    # First failure - no fallback
    manager.record_request_failure("openrouter")
    assert not manager.should_attempt_fallback("openrouter")

    # Second failure - trigger fallback
    manager.record_request_failure("openrouter")
    assert manager.should_attempt_fallback("openrouter")


def test_get_next_backend_excludes_attempted(mock_env, test_config):
    """Test next backend excludes already attempted ones."""
    manager = BackendManager(test_config, "openrouter")

    # First call returns groq (excluding openrouter)
    next_backend = manager.get_next_backend(exclude=["openrouter"])
    assert next_backend == "groq"

    # Second call returns None (all backends excluded)
    next_backend = manager.get_next_backend(exclude=["openrouter", "groq"])
    assert next_backend is None


def test_get_next_backend_skips_cooldown(mock_env, test_config):
    """Test next backend skips backends in cooldown."""
    manager = BackendManager(test_config, "openrouter")

    # Put groq in cooldown
    manager.record_request_failure("groq", 429)

    # Should return None since groq is in cooldown
    next_backend = manager.get_next_backend(exclude=["openrouter"])
    assert next_backend is None


def test_cooldown_duration_varies_by_error(mock_env, test_config):
    """Test cooldown duration varies based on error type."""
    manager = BackendManager(test_config)

    # Rate limit gets 2 minute cooldown
    manager.record_request_failure("openrouter", 429)
    status_429 = manager.backends["openrouter"]
    cooldown_429 = status_429.cooldown_until - time.time()
    assert 110 < cooldown_429 <= 120  # ~2 minutes

    # Reset
    manager.backends["openrouter"] = BackendStatus("openrouter", available=True)

    # Payment error gets 5 minute cooldown
    manager.record_request_failure("openrouter", 402)
    status_402 = manager.backends["openrouter"]
    cooldown_402 = status_402.cooldown_until - time.time()
    assert 290 < cooldown_402 <= 300  # ~5 minutes


def test_get_backend_info(mock_env, test_config):
    """Test getting backend status information."""
    manager = BackendManager(test_config, "openrouter")

    info = manager.get_backend_info()

    assert "openrouter" in info
    assert "groq" in info
    assert info["openrouter"]["is_primary"]
    assert not info["groq"]["is_primary"]
    assert info["openrouter"]["available"]


def test_backend_status_cooldown_expiry():
    """Test cooldown expires after time passes."""
    status = BackendStatus("test")
    status.record_failure(cooldown_seconds=0)  # Immediate expiry

    # Should not be in cooldown anymore
    time.sleep(0.1)
    assert not status.is_in_cooldown()
    # Backend remains configured and can be retried after cooldown.
    assert status.available

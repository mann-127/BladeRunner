"""Configuration management for BladeRunner."""

from pathlib import Path
from typing import Any, Dict, Optional
import yaml


class Config:
    """Central configuration manager."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_dir = Path.home() / ".bladerunner"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_path = config_path or self.config_dir / "config.yml"
        self.config = self._load_config()

    def _load_config(self) -> Dict[str, Any]:
        """Load configuration from file."""
        if not self.config_path.exists():
            return self._default_config()

        try:
            with open(self.config_path, "r") as f:
                return yaml.safe_load(f) or {}
        except Exception:
            return self._default_config()

    def _default_config(self) -> Dict[str, Any]:
        """Return default configuration."""
        return {
            "backend": "openrouter",  # openrouter or groq
            "model": "haiku",
            "debug": False,
            "models": {
                "haiku": {
                    "full_name": "anthropic/claude-haiku-4.5",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
                "sonnet": {
                    "full_name": "anthropic/claude-sonnet-4",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
                "opus": {
                    "full_name": "anthropic/claude-opus-4",
                    "temperature": 0.8,
                    "max_tokens": 2048,
                },
                # Free alternatives
                "llama": {
                    "full_name": "meta-llama/llama-3.1-8b-instruct:free",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
                "gemini": {
                    "full_name": "google/gemini-flash-1.5:free",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
                "mistral": {
                    "full_name": "mistralai/mistral-7b-instruct:free",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
                # Groq models (when using Groq backend)
                "groq-llama": {
                    "full_name": "llama-3.1-70b-versatile",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
                "groq-mixtral": {
                    "full_name": "mixtral-8x7b-32768",
                    "temperature": 0.7,
                    "max_tokens": 2048,
                },
            },
            "backends": {
                "openrouter": {
                    "base_url": "https://openrouter.ai/api/v1",
                    "api_key_env": "OPENROUTER_API_KEY",
                },
                "groq": {
                    "base_url": "https://api.groq.com/openai/v1",
                    "api_key_env": "GROQ_API_KEY",
                },
                "google_adk": {
                    "base_url": "",
                    "api_key_env": "GOOGLE_API_KEY",
                },
            },
            "permissions": {"enabled": True, "profile": "standard"},
            "sessions": {
                "enabled": True,
                "directory": str(self.config_dir / "sessions"),
            },
            "web_search": {"enabled": False, "provider": "duckduckgo", "max_results": 5},
            "google_adk": {
                "enabled": False,
                "model": "gemini-2.0-flash",
                "enable_search_grounding": True,
            },
            "api": {
                "host": "127.0.0.1",
                "port": 8000,
                "database": str(self.config_dir / "api.db"),
                "uploads_dir": str(self.config_dir / "uploads"),
                "auth": {
                    "enabled": False,
                    "keys": [],
                    "jwt": {
                        "enabled": False,
                        "secret_key": "",  # Set via BLADERUNNER_JWT_SECRET
                        "algorithm": "HS256",
                        "access_token_expire_minutes": 60,
                        "refresh_token_expire_days": 7,
                    },
                    "users": [],  # List of {username, password_hash, permissions}
                },
                "uploads": {
                    "max_size_mb": 10,
                    "allowed_types": ["image/jpeg", "image/png", "image/gif", "image/webp"],
                    "retention_days": 30,
                    "per_user_quota_mb": 100,
                },
            },
            "skills": {"enabled": False, "directory": str(self.config_dir / "skills")},
            "lsp": {"enabled": False},
            "mcp": {"enabled": False},
            "interactive": {"streaming": True},
            "agent": {
                # Tier 1: Agentic AI features
                "enable_planning": True,
                "enable_reflection": True,
                "enable_retry": True,
                "enable_streaming": False,
                # Tier 2: Safety and learning features
                "require_approval": True,  # Approve critical operations
                "enable_tool_tracking": True,  # Track tool effectiveness
                "enable_memory": True,  # Semantic memory learning
                "enable_agent_selection": True,  # Multi-agent orchestration
            },
        }

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

    def resolve_model(self, model_name: str) -> str:
        """Resolve model alias to full name."""
        # Check if it's an alias
        model_config = self.get(f"models.{model_name}")
        if model_config and "full_name" in model_config:
            return model_config["full_name"]
        # Return as-is (assume it's a full model name)
        return model_name

    def get_model_settings(self, model_name: str) -> dict:
        """Get model settings (temperature, max_tokens, etc.)."""
        model_config = self.get(f"models.{model_name}", {})
        return {
            "temperature": model_config.get("temperature", 0.7),
            "max_tokens": model_config.get("max_tokens", 2048),
        }

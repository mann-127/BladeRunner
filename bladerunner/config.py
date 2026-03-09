"""Configuration management for BladeRunner."""

import logging
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


# --- Pydantic Validation Models ---


class ModelSettings(BaseModel):
    full_name: str
    temperature: float = 0.7
    max_tokens: int = 2048


class BackendSettings(BaseModel):
    base_url: str
    api_key_env: str


class PermissionsSettings(BaseModel):
    enabled: bool = True
    profile: str = "standard"


class SessionSettings(BaseModel):
    enabled: bool = True
    directory: str


class WebSearchSettings(BaseModel):
    enabled: bool = False
    provider: str = "duckduckgo"
    max_results: int = 5


class GoogleADKSettings(BaseModel):
    enabled: bool = False
    model: str = "gemini-2.0-flash"
    enable_search_grounding: bool = True


class JWTAuthSettings(BaseModel):
    enabled: bool = False
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7


class User(BaseModel):
    username: str
    password_hash: str
    permissions: List[str] = Field(default_factory=list)


class AuthSettings(BaseModel):
    enabled: bool = False
    keys: List[str] = Field(default_factory=list)
    jwt: JWTAuthSettings = Field(default_factory=JWTAuthSettings)
    users: List[User] = Field(default_factory=list)


class UploadSettings(BaseModel):
    max_size_mb: float = 10
    allowed_types: List[str] = Field(
        default_factory=lambda: ["image/jpeg", "image/png", "image/gif", "image/webp"]
    )
    retention_days: int = 30
    per_user_quota_mb: float = 100


class APISettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    database: str
    uploads_dir: str
    auth: AuthSettings = Field(default_factory=AuthSettings)
    uploads: UploadSettings = Field(default_factory=UploadSettings)


class LoggingSettings(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    date_format: str = "%Y-%m-%dT%H:%M:%S%z"
    uvicorn_access_log: bool = True


class SkillsSettings(BaseModel):
    enabled: bool = False
    directory: str


class LSPSettings(BaseModel):
    enabled: bool = False


class MCPSettings(BaseModel):
    enabled: bool = False


class InteractiveSettings(BaseModel):
    streaming: bool = True


class AgentSettings(BaseModel):
    enable_planning: bool = True
    enable_reflection: bool = True
    enable_retry: bool = True
    enable_streaming: bool = False
    require_approval: bool = True
    enable_tool_tracking: bool = True
    enable_memory: bool = True
    enable_agent_selection: bool = True
    enable_adaptation: bool = True
    adaptation_failure_threshold: int = 2
    enable_trace: bool = True


class Settings(BaseModel):
    """Pydantic model for config.yml validation."""

    backend: str = "openrouter"
    model: str = "haiku"
    debug: bool = False
    models: Dict[str, ModelSettings]
    backends: Dict[str, BackendSettings]
    permissions: PermissionsSettings = Field(default_factory=PermissionsSettings)
    sessions: SessionSettings
    web_search: WebSearchSettings = Field(default_factory=WebSearchSettings)
    google_adk: GoogleADKSettings = Field(default_factory=GoogleADKSettings)
    api: APISettings
    logging: LoggingSettings = Field(default_factory=LoggingSettings)
    skills: SkillsSettings
    lsp: LSPSettings = Field(default_factory=LSPSettings)
    mcp: MCPSettings = Field(default_factory=MCPSettings)
    interactive: InteractiveSettings = Field(default_factory=InteractiveSettings)
    agent: AgentSettings = Field(default_factory=AgentSettings)


# --- Config Manager ---


class Config:
    """Central configuration manager."""

    def __init__(self, config_path: Optional[Path] = None):
        self.config_dir = Path.home() / ".bladerunner"
        self.config_dir.mkdir(parents=True, exist_ok=True)

        self.config_path = config_path or self.config_dir / "config.yml"
        self.settings = self._load_config()
        self.config = self.settings.model_dump()  # For legacy dict access

    def _load_config(self) -> Settings:
        """Load, validate, and return configuration."""
        default_cfg = self._default_config()
        if not self.config_path.exists():
            logger.warning("No config file found, using default settings.")
            user_cfg: Dict[str, Any] = {}
        else:
            try:
                with open(self.config_path, "r") as f:
                    loaded_cfg = yaml.safe_load(f) or {}
                    user_cfg = loaded_cfg if isinstance(loaded_cfg, dict) else {}
            except Exception as e:
                logger.error("Error reading config file: %s. Using defaults.", e)
                user_cfg = {}

        # Deep merge user config into default
        merged_cfg = self._deep_merge(default_cfg, user_cfg)

        try:
            settings = Settings(**merged_cfg)
            return settings
        except ValidationError as e:
            logger.error(
                "Configuration validation failed. Using default settings. Errors:\n%s",
                e,
            )
            # Fallback to default on validation error
            return Settings(**default_cfg)

    def _deep_merge(
        self, source: Dict[str, Any], destination: Dict[str, Any]
    ) -> Dict[str, Any]:
        """Deeply merge two dictionaries."""
        for key, value in source.items():
            if isinstance(value, dict):
                node = destination.setdefault(key, {})
                if isinstance(node, dict):
                    self._deep_merge(value, node)
                else:
                    destination[key] = value
            else:
                destination.setdefault(key, value)
        return destination

    def _default_config_dict(self) -> Dict[str, Any]:
        """Return default configuration as a dictionary."""
        return {
            "backend": "openrouter",
            "model": "haiku",
            "debug": False,
            "models": {
                "haiku": {
                    "full_name": "anthropic/claude-haiku-4.5",
                },
                "sonnet": {
                    "full_name": "anthropic/claude-sonnet-4",
                },
                "opus": {
                    "full_name": "anthropic/claude-opus-4",
                },
                "llama": {
                    "full_name": "meta-llama/llama-3.1-8b-instruct:free",
                },
                "gemini": {
                    "full_name": "google/gemini-flash-1.5:free",
                },
                "mistral": {
                    "full_name": "mistralai/mistral-7b-instruct:free",
                },
                "groq-llama": {
                    "full_name": "llama-3.1-70b-versatile",
                },
                "groq-mixtral": {
                    "full_name": "mixtral-8x7b-32768",
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
            "api": {
                "database": str(self.config_dir / "api.db"),
                "uploads_dir": str(self.config_dir / "uploads"),
                "auth": {
                    "enabled": False,
                    "keys": [],
                    "jwt": {
                        "enabled": False,
                        "secret_key": "",
                        "algorithm": "HS256",
                        "access_token_expire_minutes": 60,
                        "refresh_token_expire_days": 7,
                    },
                    "users": [],
                },
                "uploads": {
                    "max_size_mb": 10,
                    "allowed_types": [
                        "image/jpeg",
                        "image/png",
                        "image/gif",
                        "image/webp",
                    ],
                    "retention_days": 30,
                    "per_user_quota_mb": 100,
                },
            },
            "skills": {"enabled": False, "directory": str(self.config_dir / "skills")},
        }

    def _default_config(self) -> Dict[str, Any]:
        """Backward-compatible default config hook for tests/integrations."""
        return self._default_config_dict()

    def resolve_model(self, model: str) -> str:
        """Resolve model aliases; pass through full model names unchanged."""
        models = self.get("models", {})
        model_cfg = models.get(model)
        if isinstance(model_cfg, dict):
            full_name = model_cfg.get("full_name")
            if isinstance(full_name, str) and full_name:
                return full_name
        return model

    def get_model_settings(self, model: str) -> Dict[str, Any]:
        """Return effective model settings for a model alias or full model name."""
        models = self.get("models", {})
        if isinstance(models, dict):
            model_cfg = models.get(model)
            if isinstance(model_cfg, dict):
                return {
                    "temperature": model_cfg.get("temperature", 0.7),
                    "max_tokens": model_cfg.get("max_tokens", 2048),
                }
        return {"temperature": 0.7, "max_tokens": 2048}

    def get(self, key: str, default: Any = None) -> Any:
        """Get configuration value."""
        keys = key.split(".")
        value: Any = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

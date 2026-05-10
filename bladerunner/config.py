"""Configuration management for BladeRunner."""

import copy
import logging
from pathlib import Path

import yaml
from pydantic import BaseModel, Field, ValidationError

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Pydantic models
# ---------------------------------------------------------------------------


class ModelSettings(BaseModel):
    full_name: str
    temperature: float = Field(default=0.7, ge=0.0, le=2.0)
    max_tokens: int = Field(default=2048, ge=1, le=128000)


class BackendSettings(BaseModel):
    base_url: str
    api_key_env: str


class AgentSettings(BaseModel):
    max_iterations: int = 30
    max_history_messages: int = 20
    stream: bool = False
    require_approval: bool = True
    permissions_profile: str = "standard"
    memory_enabled: bool = True
    memory_use_embeddings: bool = False
    memory_embedding_model: str = "all-MiniLM-L6-v2"


class SessionSettings(BaseModel):
    enabled: bool = True
    directory: str


class WebSearchSettings(BaseModel):
    enabled: bool = False
    provider: str = "duckduckgo"
    max_results: int = 5
    timeout: int = 10


class RAGSettings(BaseModel):
    enabled: bool = False
    persist_directory: str
    embedding_model: str = "all-MiniLM-L6-v2"


class JWTSettings(BaseModel):
    enabled: bool = False
    secret_key: str = ""
    algorithm: str = "HS256"
    access_token_expire_minutes: int = 60
    refresh_token_expire_days: int = 7


class UserSettings(BaseModel):
    user_id: str = ""
    username: str
    password_hash: str
    permissions: list[str] = Field(default_factory=list)


class AuthSettings(BaseModel):
    enabled: bool = False
    keys: list[str] = Field(default_factory=list)
    jwt: JWTSettings = Field(default_factory=JWTSettings)
    users: list[UserSettings] = Field(default_factory=list)


class UploadSettings(BaseModel):
    max_size_mb: float = 10
    allowed_types: list[str] = Field(default_factory=lambda: ["image/jpeg", "image/png", "image/gif", "image/webp"])
    retention_days: int = 30
    per_user_quota_mb: float = 100


class APISettings(BaseModel):
    host: str = "127.0.0.1"
    port: int = 8000
    cors_origins: list[str] = Field(default_factory=lambda: ["*"])
    chat_timeout_seconds: float = 300
    database: str
    uploads_dir: str
    auth: AuthSettings = Field(default_factory=AuthSettings)
    uploads: UploadSettings = Field(default_factory=UploadSettings)


class LoggingSettings(BaseModel):
    level: str = "INFO"
    format: str = "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    date_format: str = "%Y-%m-%dT%H:%M:%S%z"
    uvicorn_access_log: bool = True


class Settings(BaseModel):
    backend: str = "openrouter"
    model: str = "gemma"
    debug: bool = False
    models: dict[str, ModelSettings]
    backends: dict[str, BackendSettings]
    agent: AgentSettings = Field(default_factory=AgentSettings)
    sessions: SessionSettings
    web_search: WebSearchSettings = Field(default_factory=WebSearchSettings)
    rag: RAGSettings
    api: APISettings
    logging: LoggingSettings = Field(default_factory=LoggingSettings)


# ---------------------------------------------------------------------------
# Config manager
# ---------------------------------------------------------------------------


class Config:
    """Central configuration manager."""

    def __init__(self, config_path=None):
        self.config_dir = Path.home() / ".bladerunner"
        self.config_dir.mkdir(parents=True, exist_ok=True)
        self.config_path = config_path or self.config_dir / "config.yml"
        self.settings = self._load()
        self.config = self.settings.model_dump()

    def _load(self):
        defaults = self._defaults()
        if not self.config_path.exists():
            user_cfg = {}
        else:
            try:
                with open(self.config_path) as f:
                    loaded = yaml.safe_load(f) or {}
                    user_cfg = loaded if isinstance(loaded, dict) else {}
            except Exception as e:
                logger.error("Error reading config file: %s", e)
                user_cfg = {}

        merged = self._deep_merge(defaults, user_cfg)
        try:
            return Settings(**merged)
        except ValidationError as e:
            logger.error("Config validation failed, using defaults:\n%s", e)
            return Settings(**defaults)

    def _defaults(self):
        return {
            "backend": "openrouter",
            "model": "gemma",
            "debug": False,
            "models": {
                "gemma": {"full_name": "google/gemma-3-27b-it:free"},
                "llama-70b": {"full_name": "meta-llama/llama-3.3-70b-instruct:free"},
                "qwen3-coder": {"full_name": "qwen/qwen3-coder:free"},
                "gpt-oss-20b": {"full_name": "openai/gpt-oss-20b:free"},
                "groq-llama": {"full_name": "llama-3.1-70b-versatile"},
                "groq-mixtral": {"full_name": "mixtral-8x7b-32768"},
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
            },
            "agent": {
                "max_iterations": 30,
                "max_history_messages": 20,
                "stream": False,
                "require_approval": True,
                "permissions_profile": "standard",
                "memory_enabled": True,
                "memory_use_embeddings": False,
                "memory_embedding_model": "all-MiniLM-L6-v2",
            },
            "sessions": {
                "enabled": True,
                "directory": str(self.config_dir / "sessions"),
            },
            "web_search": {
                "enabled": False,
                "provider": "duckduckgo",
                "max_results": 5,
                "timeout": 10,
            },
            "rag": {
                "enabled": False,
                "persist_directory": str(self.config_dir / "rag"),
                "embedding_model": "all-MiniLM-L6-v2",
            },
            "api": {
                "host": "127.0.0.1",
                "port": 8000,
                "cors_origins": ["*"],
                "chat_timeout_seconds": 300,
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
            "logging": {
                "level": "INFO",
                "format": "%(asctime)s %(levelname)s [%(name)s] %(message)s",
                "date_format": "%Y-%m-%dT%H:%M:%S%z",
                "uvicorn_access_log": True,
            },
        }

    @staticmethod
    def _deep_merge(source, destination):
        for key, value in source.items():
            if isinstance(value, dict):
                node = destination.setdefault(key, {})
                if isinstance(node, dict):
                    Config._deep_merge(value, node)
                else:
                    destination[key] = value
            else:
                destination.setdefault(key, value)
        return destination

    def resolve_model(self, model):
        typed = self.settings.models.get(model)
        if typed and typed.full_name:
            return typed.full_name
        cfg = (self.get("models") or {}).get(model)
        if isinstance(cfg, dict) and cfg.get("full_name"):
            return cfg["full_name"]
        return model

    def get_model_settings(self, model):
        typed = self.settings.models.get(model)
        if typed:
            return {"temperature": typed.temperature, "max_tokens": typed.max_tokens}
        cfg = (self.get("models") or {}).get(model)
        if isinstance(cfg, dict):
            return {
                "temperature": cfg.get("temperature", 0.7),
                "max_tokens": cfg.get("max_tokens", 2048),
            }
        return {"temperature": 0.7, "max_tokens": 2048}

    @classmethod
    def fork(cls, other):
        """Clone config with independent mutable dict, without disk read."""
        inst = object.__new__(cls)
        inst.config_dir = other.config_dir
        inst.config_path = other.config_path
        inst.settings = other.settings
        inst.config = copy.deepcopy(other.config)
        return inst

    def save(self):
        self.config_path.parent.mkdir(parents=True, exist_ok=True)
        with open(self.config_path, "w", encoding="utf-8") as f:
            yaml.safe_dump(self.config, f, sort_keys=False)

    def get(self, key, default=None):
        keys = key.split(".")
        value = self.config
        for k in keys:
            if isinstance(value, dict):
                value = value.get(k)
            else:
                return default
        return value if value is not None else default

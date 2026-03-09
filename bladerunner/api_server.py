"""FastAPI service for BladeRunner and Google ADK/Gemini chat."""

from __future__ import annotations

import asyncio
import bcrypt
import copy
from contextlib import asynccontextmanager, suppress
from datetime import datetime, timedelta, timezone
import logging
import os
import queue
import uuid
from pathlib import Path
from typing import Any, Dict, List, Literal, Optional

import jwt
import uvicorn
from dotenv import load_dotenv
from fastapi import FastAPI, File, Header, HTTPException, Query, UploadFile, WebSocket
from pydantic import BaseModel, Field

from .adk_bridge import GoogleADKBridge
from .agent import Agent
from .api_store import APISessionStore
from .config import Config
from .logging_config import configure_logging
from .sessions import SessionManager
from .skills import SkillManager

logger = logging.getLogger(__name__)


class SessionCreateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    title: str = Field(default="New Case File", min_length=1, max_length=200)


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=10000)
    session_id: Optional[str] = None
    model: Optional[str] = None
    engine: Literal["bladerunner", "google_adk"] = "bladerunner"
    enable_web_search: bool = False
    enable_rag: bool = False
    image_paths: List[str] = Field(default_factory=list)
    enable_planning: Optional[bool] = None
    enable_reflection: Optional[bool] = None
    enable_retry: Optional[bool] = None
    enable_streaming: bool = False
    permission_profile: Literal["strict", "standard", "permissive", "none"] = "none"
    skill: Optional[str] = None
    auto_match_skill: bool = False
    google_search_grounding: Optional[bool] = None
    include_trace: bool = False


class SourceItem(BaseModel):
    title: str
    url: str


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    engine: str
    model: str
    sources: List[SourceItem]
    web_search_requested: bool = False
    web_search_used: bool = False
    rag_requested: bool = False
    rag_available: bool = False
    applied_skill: Optional[str] = None
    warnings: List[str] = Field(default_factory=list)
    trace: Optional[Dict[str, Any]] = None


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: List[dict]


class UploadResponse(BaseModel):
    file_path: str
    original_name: str
    size_bytes: int


class LoginRequest(BaseModel):
    username: str = Field(min_length=1, max_length=64)
    password: str = Field(min_length=1, max_length=128)


class TokenResponse(BaseModel):
    access_token: str
    refresh_token: str
    token_type: str = "bearer"
    expires_in: int


class RefreshTokenRequest(BaseModel):
    refresh_token: str


class UserInfo(BaseModel):
    username: str
    user_id: str
    permissions: List[str] = Field(default_factory=list)


def _new_bladerunner_session_id() -> str:
    # Prefix makes API-created sessions easy to identify in JSONL history.
    return f"api_{uuid.uuid4().hex[:12]}"


def create_app() -> FastAPI:
    """Build and configure FastAPI app."""
    load_dotenv()
    config = Config()
    configure_logging(config, service_name="bladerunner.api")

    cleanup_task: Optional[asyncio.Task] = None

    @asynccontextmanager
    async def lifespan(_app: FastAPI):
        """Manage background tasks for app lifecycle."""
        nonlocal cleanup_task
        cleanup_task = asyncio.create_task(_cleanup_old_uploads())
        try:
            yield
        finally:
            if cleanup_task is not None:
                cleanup_task.cancel()
                with suppress(asyncio.CancelledError):
                    await cleanup_task

    app = FastAPI(
        title="BladeRunner API",
        version="0.1.0",
        description="FastAPI API server for BladeRunner with optional Google ADK/Gemini mode.",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    store = APISessionStore(Path(config.get("api.database", "~/.bladerunner/api.db")))

    auth_enabled = bool(config.get("api.auth.enabled", False))
    configured_keys = config.get("api.auth.keys", []) or []
    env_keys = [
        k.strip() for k in os.getenv("BLADERUNNER_API_KEYS", "").split(",") if k.strip()
    ]
    api_keys = set(configured_keys + env_keys)

    # JWT configuration
    jwt_enabled = bool(config.get("api.auth.jwt.enabled", False))
    jwt_secret = os.getenv("BLADERUNNER_JWT_SECRET") or config.get(
        "api.auth.jwt.secret_key", ""
    )
    jwt_algorithm = config.get("api.auth.jwt.algorithm", "HS256")
    access_token_expire_minutes = config.get(
        "api.auth.jwt.access_token_expire_minutes", 60
    )
    refresh_token_expire_days = config.get("api.auth.jwt.refresh_token_expire_days", 7)
    users = config.get("api.auth.users", []) or []

    def _ensure_jwt_runtime_ready() -> None:
        """Validate JWT runtime configuration before token operations."""
        if not jwt_enabled:
            raise HTTPException(
                status_code=501, detail="JWT authentication not enabled"
            )
        if not jwt_secret:
            raise HTTPException(status_code=500, detail="JWT secret not configured")
        if jwt_algorithm.upper().startswith("HS") and len(jwt_secret) < 32:
            raise HTTPException(
                status_code=500,
                detail="JWT secret too short (minimum 32 characters for HS algorithms)",
            )

    def _create_jwt_token(data: dict, expires_delta: timedelta) -> str:
        """Create a JWT token with expiration."""
        to_encode = data.copy()
        expire = datetime.now(timezone.utc) + expires_delta
        to_encode.update({"exp": expire})
        return jwt.encode(to_encode, jwt_secret, algorithm=jwt_algorithm)

    def _verify_jwt_token(token: str) -> Optional[dict]:
        """Verify and decode JWT token."""
        try:
            payload = jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
            return payload
        except jwt.ExpiredSignatureError:
            raise HTTPException(status_code=401, detail="Token expired")
        except jwt.InvalidTokenError:
            return None

    def _authenticate_user(username: str, password: str) -> Optional[dict]:
        """Authenticate user with username and password."""
        for user in users:
            if user.get("username") == username:
                password_hash = user.get("password_hash", "")
                # Use bcrypt directly to avoid passlib initialization issues
                try:
                    if bcrypt.checkpw(
                        password.encode("utf-8"), password_hash.encode("utf-8")
                    ):
                        return user
                except Exception as exc:
                    logger.exception(
                        "Password verification failed for user '%s': %s", username, exc
                    )
                    return None
        return None

    def _get_user_from_token(token: str) -> Optional[UserInfo]:
        """Extract user info from JWT token."""
        payload = _verify_jwt_token(token)
        if not payload:
            return None
        return UserInfo(
            username=payload.get("sub", ""),
            user_id=payload.get("user_id", ""),
            permissions=payload.get("permissions", []),
        )

    def _require_api_key(key: Optional[str]) -> Optional[UserInfo]:
        """Validate API key or JWT token when auth is enabled. Returns user info from JWT if available."""
        if not auth_enabled:
            return None

        # Try JWT token first (if enabled and secret is set)
        if jwt_enabled and jwt_secret and key:
            # Check if it looks like a JWT (contains dots)
            if key.count(".") == 2:
                user = _get_user_from_token(key)
                if user:
                    return user

        # Fall back to static API key validation
        if not key or key not in api_keys:
            raise HTTPException(status_code=401, detail="Unauthorized")

        return None

    def _config_with_toggles(
        base_config: Config, web_enabled: bool, rag_enabled: bool
    ) -> Config:
        """Clone config object with request-scoped feature toggles."""
        cfg = Config()
        cfg.config = copy.deepcopy(base_config.config)
        cfg.config.setdefault("web_search", {})
        cfg.config["web_search"]["enabled"] = web_enabled
        cfg.config.setdefault("rag", {})
        cfg.config["rag"]["enabled"] = rag_enabled
        return cfg

    def _build_prompt_with_images(prompt: str, image_paths: List[str]) -> str:
        """Inject image-analysis hint so model can invoke ReadImage tool."""
        if not image_paths:
            return prompt
        lines = [
            prompt,
            "",
            "Attached image paths:",
        ]
        lines.extend([f"- {p}" for p in image_paths])
        lines.append(
            "Use ReadImage on relevant paths before answering when visual context is needed."
        )
        return "\n".join(lines)

    def _apply_skill(
        agent: Agent, prompt: str, explicit_skill: Optional[str], auto_match: bool
    ) -> Optional[str]:
        """Apply skill context and tool restrictions when available."""
        manager = SkillManager()
        skill = None

        if explicit_skill:
            skill = manager.get_skill(explicit_skill)
        elif auto_match:
            skill = manager.match_skill(prompt)

        if not skill:
            return None

        if skill.system_prompt:
            agent.messages.append(
                {
                    "role": "assistant",
                    "content": f"[Skill Context: {skill.name}]\n{skill.system_prompt}",
                }
            )

        if skill.allowed_tools:
            allowed = set(skill.allowed_tools)
            agent.registry.tools = {
                name: tool
                for name, tool in agent.registry.tools.items()
                if name in allowed
            }

        if skill.model:
            agent.set_model(skill.model)

        return skill.name

    def _create_agent_for_request(
        payload: ChatRequest,
        session: Dict[str, Any],
        base_config: Config,
        is_streaming: bool,
    ) -> tuple[Agent, list[str]]:
        """Configure and return a BladeRunner agent based on API request parameters."""
        warnings: list[str] = []
        web_config = _config_with_toggles(
            base_config,
            web_enabled=payload.enable_web_search,
            rag_enabled=payload.enable_rag,
        )

        use_permissions = payload.permission_profile != "none"
        permission_profile = (
            payload.permission_profile if use_permissions else "permissive"
        )

        try:
            agent = Agent(
                config=web_config,
                model=payload.model or base_config.get("model", "haiku"),
                use_permissions=use_permissions,
                permission_profile=permission_profile,
                session_id=session["bladerunner_session_id"],
            )
        except RuntimeError as exc:
            raise HTTPException(
                status_code=500, detail=f"Configuration error: {exc}"
            ) from exc

        if agent.use_permissions and agent.permission_checker:
            # API mode is non-interactive: treat ASK prompts as denied.
            agent.permission_checker.prompt_user = lambda *_args, **_kwargs: False
            if payload.permission_profile in {"standard", "strict"}:
                warnings.append("Non-interactive mode auto-denies ASK permission prompts.")

        if is_streaming and payload.enable_streaming is False:
            warnings.append("Payload requested no streaming, but endpoint requires it.")
        elif not is_streaming and payload.enable_streaming:
            warnings.append("Streaming in HTTP response is not implemented yet.")

        # Configure agent based on payload
        if payload.enable_planning is not None:
            agent.enable_planning = payload.enable_planning
        if payload.enable_reflection is not None:
            agent.enable_reflection = payload.enable_reflection
        if payload.enable_retry is not None:
            agent.enable_retry = payload.enable_retry
        agent.enable_streaming = is_streaming

        agent.load_session(session["bladerunner_session_id"])
        return agent, warnings

    @app.get("/api/health")
    def health(
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")
    ) -> dict:
        _require_api_key(x_api_key)
        return {
            "ok": True,
            "service": "bladerunner-api",
            "google_adk_available": GoogleADKBridge.adk_available(),
            "auth_enabled": auth_enabled,
            "jwt_enabled": jwt_enabled and bool(jwt_secret),
        }

    @app.post("/api/auth/login")
    def login(request: LoginRequest) -> TokenResponse:
        """Authenticate user and return JWT tokens."""
        _ensure_jwt_runtime_ready()

        user = _authenticate_user(request.username, request.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")

        user_id = user.get("user_id") or user.get("username")
        permissions = user.get("permissions", [])

        access_token = _create_jwt_token(
            {"sub": request.username, "user_id": user_id, "permissions": permissions},
            timedelta(minutes=access_token_expire_minutes),
        )
        refresh_token = _create_jwt_token(
            {"sub": request.username, "user_id": user_id, "type": "refresh"},
            timedelta(days=refresh_token_expire_days),
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=refresh_token,
            expires_in=access_token_expire_minutes * 60,
        )

    @app.post("/api/auth/refresh")
    def refresh(request: RefreshTokenRequest) -> TokenResponse:
        """Refresh access token using refresh token."""
        _ensure_jwt_runtime_ready()

        payload = _verify_jwt_token(request.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")

        username = payload.get("sub")
        user_id = payload.get("user_id")

        # Find user to get current permissions
        user = next((u for u in users if u.get("username") == username), None)
        permissions = user.get("permissions", []) if user else []

        access_token = _create_jwt_token(
            {"sub": username, "user_id": user_id, "permissions": permissions},
            timedelta(minutes=access_token_expire_minutes),
        )

        return TokenResponse(
            access_token=access_token,
            refresh_token=request.refresh_token,
            expires_in=access_token_expire_minutes * 60,
        )

    @app.get("/api/auth/me")
    def get_current_user(
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")
    ) -> UserInfo:
        """Get current user info from JWT token."""
        user = _require_api_key(x_api_key)
        if not user:
            raise HTTPException(status_code=401, detail="JWT token required")
        return user

    @app.get("/api/meta")
    def meta(
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")
    ) -> Dict[str, object]:
        """Return API metadata including models, engines, skills, and auth status."""
        _require_api_key(x_api_key)
        skills = SkillManager().list_skills()
        return {
            "models": list((config.get("models") or {}).keys()),
            "default_model": config.get("model", "haiku"),
            "engines": ["bladerunner", "google_adk"],
            "permission_profiles": ["none", "permissive", "standard", "strict"],
            "skills": skills,
            "auth_enabled": auth_enabled,
        }

    @app.get("/api/skills")
    def list_skills(
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key")
    ) -> List[Dict[str, str]]:
        """List configured skills."""
        _require_api_key(x_api_key)
        return SkillManager().list_skills()

    def _get_user_upload_size(user_id: str) -> int:
        """Calculate total upload size for a user in bytes."""
        base_upload_dir = Path(
            config.get("api.uploads_dir", "~/.bladerunner/uploads")
        ).expanduser()
        user_dir = base_upload_dir / user_id
        if not user_dir.exists():
            return 0

        total_size = 0
        for file_path in user_dir.glob("*"):
            if file_path.is_file():
                total_size += file_path.stat().st_size
        return total_size

    def _check_upload_quota(user_id: str, new_file_size: int) -> None:
        """Check if user has enough quota for new upload."""
        max_quota_mb = config.get("api.uploads.per_user_quota_mb", 100)
        max_quota_bytes = max_quota_mb * 1024 * 1024

        current_size = _get_user_upload_size(user_id)
        if current_size + new_file_size > max_quota_bytes:
            used_mb = current_size / (1024 * 1024)
            raise HTTPException(
                status_code=413,
                detail=f"Upload quota exceeded. Used: {used_mb:.2f}MB / {max_quota_mb}MB",
            )

    def _validate_upload_file(file: UploadFile, content: bytes) -> None:
        """Validate file type and size."""
        max_size_mb = config.get("api.uploads.max_size_mb", 10)
        max_size_bytes = max_size_mb * 1024 * 1024

        if len(content) > max_size_bytes:
            raise HTTPException(
                status_code=413,
                detail=f"File too large. Maximum size: {max_size_mb}MB",
            )

        allowed_types = config.get(
            "api.uploads.allowed_types",
            ["image/jpeg", "image/png", "image/gif", "image/webp"],
        )
        if file.content_type not in allowed_types:
            raise HTTPException(
                status_code=400,
                detail=f"Unsupported file type: {file.content_type}. Allowed: {', '.join(allowed_types)}",
            )

    async def _cleanup_old_uploads() -> None:
        """Background task to periodically clean up old uploads based on retention policy."""
        retention_days = config.get("api.uploads.retention_days", 30)
        check_interval_hours = 6  # Check every 6 hours

        while True:
            try:
                base_upload_dir = Path(
                    config.get("api.uploads_dir", "~/.bladerunner/uploads")
                ).expanduser()
                if not base_upload_dir.exists():
                    await asyncio.sleep(check_interval_hours * 3600)
                    continue

                cutoff_time = datetime.now(timezone.utc) - timedelta(
                    days=retention_days
                )
                deleted_count = 0
                deleted_size = 0

                # Iterate through all user directories
                for user_dir in base_upload_dir.iterdir():
                    if not user_dir.is_dir():
                        continue

                    for file_path in user_dir.glob("*"):
                        if not file_path.is_file():
                            continue

                        # Check file modification time
                        file_mtime = datetime.fromtimestamp(
                            file_path.stat().st_mtime, tz=timezone.utc
                        )
                        if file_mtime < cutoff_time:
                            file_size = file_path.stat().st_size
                            file_path.unlink()
                            deleted_count += 1
                            deleted_size += file_size

                if deleted_count > 0:
                    logger.info(
                        f"Upload cleanup: deleted {deleted_count} files ({deleted_size / (1024*1024):.2f}MB) "
                        f"older than {retention_days} days"
                    )

            except Exception as e:
                logger.exception("Error during upload cleanup: %s", e)

            # Wait before next cleanup cycle
            await asyncio.sleep(check_interval_hours * 3600)

    @app.post("/api/uploads/image", response_model=UploadResponse)
    async def upload_image(
        user_id: str = Query(..., min_length=1, max_length=128),
        file: UploadFile = File(...),
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> UploadResponse:
        """Upload an image and return server-side path for ReadImage tool usage."""
        _require_api_key(x_api_key)

        # Read file content
        content = await file.read()

        # Validate file type and size
        _validate_upload_file(file, content)

        # Check user quota
        _check_upload_quota(user_id, len(content))

        # Save file
        base_upload_dir = Path(
            config.get("api.uploads_dir", "~/.bladerunner/uploads")
        ).expanduser()
        target_dir = base_upload_dir / user_id
        target_dir.mkdir(parents=True, exist_ok=True)

        target_name = f"{uuid.uuid4().hex[:12]}_{Path(file.filename or 'image').name}"
        target_path = target_dir / target_name

        target_path.write_bytes(content)

        return UploadResponse(
            file_path=str(target_path),
            original_name=file.filename or "image",
            size_bytes=len(content),
        )

    @app.get("/api/uploads/quota/{user_id}")
    def get_upload_quota(
        user_id: str,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> dict:
        """Get current upload quota usage for a user."""
        _require_api_key(x_api_key)

        max_quota_mb = config.get("api.uploads.per_user_quota_mb", 100)
        current_size = _get_user_upload_size(user_id)
        current_mb = current_size / (1024 * 1024)

        return {
            "user_id": user_id,
            "used_mb": round(current_mb, 2),
            "total_mb": max_quota_mb,
            "remaining_mb": round(max_quota_mb - current_mb, 2),
            "usage_percent": (
                round((current_mb / max_quota_mb) * 100, 1) if max_quota_mb > 0 else 0
            ),
        }

    @app.post("/api/sessions", response_model=SessionResponse)
    def create_session(
        payload: SessionCreateRequest,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> SessionResponse:
        _require_api_key(x_api_key)
        br_session_id = _new_bladerunner_session_id()
        SessionManager().create_session(br_session_id)

        session = store.create_session(
            user_id=payload.user_id,
            title=payload.title,
            bladerunner_session_id=br_session_id,
        )

        return SessionResponse(
            session_id=session["id"],
            user_id=session["user_id"],
            title=session["title"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
        )

    @app.get("/api/sessions", response_model=List[SessionResponse])
    def list_sessions(
        user_id: str = Query(..., min_length=1, max_length=128),
        limit: int = Query(50, ge=1, le=200),
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> List[SessionResponse]:
        _require_api_key(x_api_key)
        sessions = store.list_sessions(user_id=user_id, limit=limit)
        return [
            SessionResponse(
                session_id=s["id"],
                user_id=s["user_id"],
                title=s["title"],
                created_at=s["created_at"],
                updated_at=s["updated_at"],
            )
            for s in sessions
        ]

    @app.get(
        "/api/sessions/{session_id}/messages", response_model=SessionMessagesResponse
    )
    def list_messages(
        session_id: str,
        user_id: str = Query(..., min_length=1, max_length=128),
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> SessionMessagesResponse:
        _require_api_key(x_api_key)
        session = store.get_session(user_id=user_id, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")

        return SessionMessagesResponse(
            session_id=session_id,
            messages=store.list_messages(session_id=session_id),
        )

    @app.post("/api/chat", response_model=ChatResponse)
    def chat(
        payload: ChatRequest,
        x_api_key: Optional[str] = Header(default=None, alias="X-API-Key"),
    ) -> ChatResponse:
        _require_api_key(x_api_key)
        warnings: List[str] = []
        session = None
        if payload.session_id:
            session = store.get_session(
                user_id=payload.user_id, session_id=payload.session_id
            )
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")

        if not session:
            br_session_id = _new_bladerunner_session_id()
            SessionManager().create_session(br_session_id)
            session = store.create_session(
                user_id=payload.user_id,
                title="Live Session",
                bladerunner_session_id=br_session_id,
            )

        store.add_message(session["id"], "user", payload.message)

        if payload.engine == "google_adk":
            bridge = GoogleADKBridge(
                model=payload.model
                or config.get("google_adk.model", "gemini-2.0-flash"),
                enable_search_grounding=(
                    payload.google_search_grounding
                    if payload.google_search_grounding is not None
                    else config.get("google_adk.enable_search_grounding", True)
                ),
            )
            try:
                result = bridge.generate(payload.message)
            except RuntimeError as exc:
                detail = str(exc)
                if "rate limit" in detail.lower():
                    raise HTTPException(status_code=429, detail=detail) from exc
                raise HTTPException(status_code=400, detail=detail) from exc
            except Exception as exc:
                # Unexpected errors
                logger.exception("Unexpected Google ADK/Gemini error: %s", exc)
                raise HTTPException(
                    status_code=500,
                    detail=f"Unexpected Google ADK/Gemini error: {type(exc).__name__}",
                ) from exc

            answer = result.answer
            sources = result.sources
            engine = result.provider
            model = payload.model or config.get("google_adk.model", "gemini-2.0-flash")
            web_search_requested = False
            web_search_used = False
            rag_requested = False
            rag_available = False
            applied_skill = None
            trace = None
            if payload.image_paths:
                warnings.append(
                    "Image paths are currently processed only by 'bladerunner' engine."
                )
            if payload.include_trace:
                warnings.append(
                    "Trace output is only available for the 'bladerunner' engine."
                )
        else:
            agent, warnings = _create_agent_for_request(
                payload, session, config, is_streaming=False
            )

            applied_skill = _apply_skill(
                agent,
                prompt=payload.message,
                explicit_skill=payload.skill,
                auto_match=payload.auto_match_skill,
            )

            if payload.skill and not applied_skill:
                warnings.append(f"Skill '{payload.skill}' was not found.")

            prepared_prompt = _build_prompt_with_images(
                payload.message, payload.image_paths
            )
            answer = agent.execute(prepared_prompt)
            sources = []
            engine = "bladerunner"
            model = agent.model
            web_search_requested = payload.enable_web_search
            web_search_used = agent.was_web_search_used()
            rag_requested = payload.enable_rag
            rag_available = agent.registry.get("rag_search") is not None
            trace = agent.get_last_trace() if payload.include_trace else None

            if payload.enable_rag and not rag_available:
                warnings.append(
                    "RAG requested but dependencies/config are not available."
                )

        store.add_message(session["id"], "assistant", answer)
        store.touch_session(session["id"])

        return ChatResponse(
            session_id=session["id"],
            answer=answer,
            engine=engine,
            model=model,
            sources=[SourceItem(**src) for src in sources],
            web_search_requested=web_search_requested,
            web_search_used=web_search_used,
            rag_requested=rag_requested,
            rag_available=rag_available,
            applied_skill=applied_skill,
            warnings=warnings,
            trace=trace,
        )

    @app.websocket("/ws/chat")
    async def ws_chat(websocket: WebSocket):
        """WebSocket streaming endpoint for BladeRunner engine with bidirectional control."""
        await websocket.accept()

        try:
            payload_raw = await websocket.receive_json()
            payload = ChatRequest(**payload_raw)

            api_key = websocket.headers.get("x-api-key")
            if not api_key:
                api_key = websocket.query_params.get("api_key")
            _require_api_key(api_key)

            if payload.engine != "bladerunner":
                await websocket.send_json(
                    {
                        "type": "error",
                        "message": "WebSocket streaming currently supports only 'bladerunner' engine.",
                    }
                )
                await websocket.close(code=1003)
                return

            if not payload.session_id:
                br_session_id = _new_bladerunner_session_id()
                SessionManager().create_session(br_session_id)
                session = store.create_session(
                    user_id=payload.user_id,
                    title="Live Session",
                    bladerunner_session_id=br_session_id,
                )
                payload.session_id = session["id"]

            session = store.get_session(payload.user_id, payload.session_id)
            if not session:
                await websocket.send_json(
                    {"type": "error", "message": "Session not found"}
                )
                await websocket.close(code=1008)
                return

            store.add_message(session["id"], "user", payload.message)

            agent, _ = _create_agent_for_request(
                payload, session, config, is_streaming=True
            )
            applied_skill = _apply_skill(
                agent,
                prompt=payload.message,
                explicit_skill=payload.skill,
                auto_match=payload.auto_match_skill,
            )

            chunk_queue: queue.Queue[str] = queue.Queue()

            def on_chunk(text: str) -> None:
                chunk_queue.put(text)

            agent.stream_callback = on_chunk
            prepared_prompt = _build_prompt_with_images(
                payload.message, payload.image_paths
            )

            # Send status update
            await websocket.send_json({"type": "status", "status": "executing"})

            loop = asyncio.get_event_loop()
            task = loop.run_in_executor(
                None, lambda: agent.execute(prepared_prompt, use_streaming=True)
            )

            # Bidirectional communication loop
            while not task.done():
                # Send any pending chunks
                while not chunk_queue.empty():
                    await websocket.send_json(
                        {"type": "chunk", "delta": chunk_queue.get()}
                    )

                # Check for control messages from client (non-blocking)
                try:
                    # Use a short timeout to check for messages without blocking
                    msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.02)
                    msg_type = msg.get("type")

                    if msg_type == "interrupt":
                        # Set interruption flag
                        agent.interrupted = True
                        await websocket.send_json(
                            {"type": "status", "status": "interrupting"}
                        )
                    elif msg_type == "ping":
                        # Heartbeat response
                        await websocket.send_json({"type": "pong"})

                except asyncio.TimeoutError:
                    # No message received, continue
                    pass
                except Exception as exc:
                    # Client disconnected or error
                    logger.warning("WebSocket control channel error: %s", exc)
                    agent.interrupted = True
                    break

                await asyncio.sleep(0.02)

            answer = await task

            # Send any remaining chunks
            while not chunk_queue.empty():
                await websocket.send_json({"type": "chunk", "delta": chunk_queue.get()})

            store.add_message(session["id"], "assistant", answer)
            store.touch_session(session["id"])

            await websocket.send_json(
                {
                    "type": "final",
                    "session_id": session["id"],
                    "answer": answer,
                    "engine": "bladerunner",
                    "model": agent.model,
                    "web_search_requested": payload.enable_web_search,
                    "web_search_used": agent.was_web_search_used(),
                    "rag_requested": payload.enable_rag,
                    "rag_available": agent.registry.get("rag_search") is not None,
                    "applied_skill": applied_skill,
                    "warnings": [],
                    "interrupted": agent.interrupted,
                    "trace": agent.get_last_trace() if payload.include_trace else None,
                }
            )
            await websocket.close()

        except HTTPException as exc:
            await websocket.send_json({"type": "error", "message": exc.detail})
            await websocket.close(code=1008)
        except Exception as exc:
            logger.exception("Unhandled websocket error: %s", exc)
            await websocket.send_json({"type": "error", "message": str(exc)})
            await websocket.close(code=1011)

    return app


app = create_app()


def main() -> None:
    """Run API server via CLI entrypoint."""
    load_dotenv()
    config = Config()
    configure_logging(config, service_name="bladerunner.api")
    host = config.get("api.host", "127.0.0.1")
    port = int(config.get("api.port", 8000))
    uvicorn.run(
        "bladerunner.api_server:app",
        host=host,
        port=port,
        reload=False,
        log_level=str(config.get("logging.level", "info")).lower(),
        access_log=bool(config.get("logging.uvicorn_access_log", True)),
    )

"""FastAPI server for BladeRunner."""

import asyncio
import collections
import logging
import os
import re
import time
import uuid
from contextlib import asynccontextmanager, suppress
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Literal

import bcrypt
import jwt
import uvicorn
from dotenv import load_dotenv
from fastapi import (
    FastAPI,
    File,
    Header,
    HTTPException,
    Query,
    Request,
    UploadFile,
    WebSocket,
)
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agent import Agent
from .api_store import APISessionStore
from .config import Config
from .logging_config import configure_logging
from .sessions import SessionManager

logger = logging.getLogger(__name__)

# ---------------------------------------------------------------------------
# Rate limiter — per-IP sliding window
# ---------------------------------------------------------------------------
_RATE_LIMIT_REQUESTS = 60
_RATE_LIMIT_WINDOW = 60.0
_rate_store: dict[str, collections.deque] = collections.defaultdict(lambda: collections.deque())


def _check_rate_limit(client_ip):
    now = time.monotonic()
    dq = _rate_store[client_ip]
    while dq and dq[0] < now - _RATE_LIMIT_WINDOW:
        dq.popleft()
    if len(dq) >= _RATE_LIMIT_REQUESTS:
        return False
    dq.append(now)
    return True


def _client_ip(request):
    forwarded = request.headers.get("X-Forwarded-For")
    if forwarded:
        return forwarded.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


# ---------------------------------------------------------------------------
# Request / response models
# ---------------------------------------------------------------------------


class SessionCreateRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    title: str = Field(default="New Session", min_length=1, max_length=200)


class SessionResponse(BaseModel):
    session_id: str
    user_id: str
    title: str
    created_at: str
    updated_at: str


class ChatRequest(BaseModel):
    user_id: str = Field(min_length=1, max_length=128)
    message: str = Field(min_length=1, max_length=10000)
    session_id: str | None = None
    model: str | None = None
    enable_web_search: bool = False
    enable_rag: bool = False
    image_paths: list[str] = Field(default_factory=list)
    enable_streaming: bool = False
    permission_profile: Literal["strict", "standard", "permissive", "none"] = "none"


class ChatResponse(BaseModel):
    session_id: str
    answer: str
    model: str
    web_search_used: bool = False
    warnings: list[str] = Field(default_factory=list)


class SessionMessagesResponse(BaseModel):
    session_id: str
    messages: list[dict]


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
    permissions: list[str] = Field(default_factory=list)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

_SAFE_UID_RE = re.compile(r"[^a-zA-Z0-9_\-]")


def _sanitize_uid(user_id):
    return _SAFE_UID_RE.sub("_", user_id)


def _new_br_session_id():
    return f"api_{uuid.uuid4().hex[:12]}"


def _build_prompt_with_images(prompt, image_paths):
    if not image_paths:
        return prompt
    lines = [prompt, "", "Attached image paths:"]
    lines.extend(f"- {p}" for p in image_paths)
    lines.append("Use ReadImage on relevant paths before answering when visual context is needed.")
    return "\n".join(lines)


# ---------------------------------------------------------------------------
# App factory
# ---------------------------------------------------------------------------


def create_app():
    load_dotenv()
    config = Config()
    configure_logging(config, service_name="bladerunner.api")

    cleanup_task = None

    @asynccontextmanager
    async def lifespan(_app):
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
        version="2.0",
        docs_url="/docs",
        redoc_url="/redoc",
        openapi_url="/openapi.json",
        lifespan=lifespan,
    )

    cors_origins = config.settings.api.cors_origins
    wildcard = cors_origins == ["*"]
    app.add_middleware(
        CORSMiddleware,
        allow_origins=cors_origins,
        allow_credentials=not wildcard,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    store = APISessionStore(Path(config.get("api.database", "~/.bladerunner/api.db")))

    # Auth setup
    auth_enabled = bool(config.get("api.auth.enabled", False))
    configured_keys = config.get("api.auth.keys") or []
    env_keys = [k.strip() for k in os.getenv("BLADERUNNER_API_KEYS", "").split(",") if k.strip()]
    api_keys = set(configured_keys + env_keys)

    jwt_enabled = bool(config.get("api.auth.jwt.enabled", False))
    jwt_secret = os.getenv("BLADERUNNER_JWT_SECRET") or config.get("api.auth.jwt.secret_key", "")
    jwt_algorithm = config.get("api.auth.jwt.algorithm", "HS256")
    access_token_expire_minutes = config.get("api.auth.jwt.access_token_expire_minutes", 60)
    refresh_token_expire_days = config.get("api.auth.jwt.refresh_token_expire_days", 7)
    users = config.get("api.auth.users") or []

    # ------------------------------------------------------------------
    # Auth helpers
    # ------------------------------------------------------------------

    def _ensure_jwt_ready():
        if not jwt_enabled:
            raise HTTPException(status_code=501, detail="JWT auth not enabled")
        if not jwt_secret:
            raise HTTPException(status_code=500, detail="JWT secret not configured")

    def _create_jwt(data, expires):
        payload = {**data, "exp": datetime.now(UTC) + expires}
        return jwt.encode(payload, jwt_secret, algorithm=jwt_algorithm)

    def _verify_jwt(token):
        try:
            return jwt.decode(token, jwt_secret, algorithms=[jwt_algorithm])
        except (jwt.ExpiredSignatureError, jwt.InvalidTokenError):
            return None

    def _authenticate(username, password):
        for user in users:
            if user.get("username") == username:
                try:
                    if bcrypt.checkpw(password.encode(), user.get("password_hash", "").encode()):
                        return user
                except Exception:
                    pass
        return None

    def _require_auth(key):
        if not auth_enabled:
            return None
        if jwt_enabled and jwt_secret and key and key.count(".") == 2:
            payload = _verify_jwt(key)
            if payload:
                return UserInfo(
                    username=payload.get("sub", ""),
                    user_id=payload.get("user_id", ""),
                    permissions=payload.get("permissions", []),
                )
            raise HTTPException(status_code=401, detail="Invalid or expired token")
        if not key or key not in api_keys:
            raise HTTPException(status_code=401, detail="Unauthorized")
        return None

    # ------------------------------------------------------------------
    # Agent factory
    # ------------------------------------------------------------------

    def _make_agent(payload, session, is_streaming):
        warnings = []
        cfg = Config.fork(config)
        cfg.config.setdefault("web_search", {})["enabled"] = payload.enable_web_search
        cfg.config.setdefault("rag", {})["enabled"] = payload.enable_rag

        use_perms = payload.permission_profile != "none"
        profile = payload.permission_profile if use_perms else "permissive"

        try:
            agent = Agent(
                config=cfg,
                model=payload.model or config.get("model", "gemma"),
                use_permissions=use_perms,
                permission_profile=profile,
                session_id=session["bladerunner_session_id"],
            )
        except RuntimeError as exc:
            if "environment variable not set" in str(exc).lower():
                cfg2 = Config.fork(cfg)
                cfg2.config["api_key"] = "test-placeholder-key"
                warnings.append("Backend API key not configured; using placeholder.")
                try:
                    agent = Agent(
                        config=cfg2,
                        model=payload.model or config.get("model", "gemma"),
                        use_permissions=use_perms,
                        permission_profile=profile,
                        session_id=session["bladerunner_session_id"],
                    )
                except RuntimeError as exc2:
                    raise HTTPException(status_code=500, detail=f"Configuration error: {exc2}") from exc2
            else:
                raise HTTPException(status_code=500, detail=f"Configuration error: {exc}") from exc

        # In non-interactive (API) mode, auto-deny all safety prompts
        agent.safety.prompt_approval = lambda *_a, **_k: False
        agent.safety.prompt_permission = lambda *_a, **_k: False
        if profile in ("standard", "strict"):
            warnings.append("Non-interactive mode auto-denies ASK permission prompts.")

        agent.enable_streaming = is_streaming
        agent.load_session(session["bladerunner_session_id"])
        return agent, warnings

    # ------------------------------------------------------------------
    # Session helpers
    # ------------------------------------------------------------------

    def _resolve_session(user_id, session_id, title="Live Session"):
        if session_id:
            session = store.get_session(user_id=user_id, session_id=session_id)
            if not session:
                raise HTTPException(status_code=404, detail="Session not found")
            return session
        br_id = _new_br_session_id()
        SessionManager().create_session(br_id)
        return store.create_session(user_id=user_id, title=title, bladerunner_session_id=br_id)

    # ------------------------------------------------------------------
    # Upload helpers
    # ------------------------------------------------------------------

    def _user_upload_size(user_id):
        base = Path(config.get("api.uploads_dir", "~/.bladerunner/uploads")).expanduser()
        user_dir = base / _sanitize_uid(user_id)
        if not user_dir.exists():
            return 0
        return sum(f.stat().st_size for f in user_dir.glob("*") if f.is_file())

    def _check_quota(user_id, file_size):
        quota_mb = config.get("api.uploads.per_user_quota_mb", 100)
        quota_bytes = quota_mb * 1024 * 1024
        used = _user_upload_size(user_id)
        if used + file_size > quota_bytes:
            detail = f"Upload quota exceeded. Used: {used / (1024 * 1024):.2f}MB / {quota_mb}MB"
            raise HTTPException(status_code=413, detail=detail)

    def _validate_upload(file, content):
        max_mb = config.get("api.uploads.max_size_mb", 10)
        if len(content) > max_mb * 1024 * 1024:
            raise HTTPException(status_code=413, detail=f"File too large. Max: {max_mb}MB")
        allowed = config.get(
            "api.uploads.allowed_types",
            ["image/jpeg", "image/png", "image/gif", "image/webp"],
        )
        if file.content_type not in allowed:
            raise HTTPException(status_code=400, detail=f"Unsupported type: {file.content_type}")

    async def _cleanup_old_uploads():
        retention_days = config.get("api.uploads.retention_days", 30)
        while True:
            try:
                base = Path(config.get("api.uploads_dir", "~/.bladerunner/uploads")).expanduser()
                if base.exists():
                    cutoff = datetime.now(UTC) - timedelta(days=retention_days)
                    for user_dir in base.iterdir():
                        if not user_dir.is_dir():
                            continue
                        for fp in user_dir.glob("*"):
                            if not fp.is_file():
                                continue
                            mtime = datetime.fromtimestamp(fp.stat().st_mtime, tz=UTC)
                            if mtime < cutoff:
                                fp.unlink()
            except Exception as e:
                logger.exception("Upload cleanup error: %s", e)
            await asyncio.sleep(6 * 3600)

    # ------------------------------------------------------------------
    # Routes
    # ------------------------------------------------------------------

    @app.get("/api/health")
    def health(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        if not _check_rate_limit(_client_ip(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _require_auth(x_api_key)
        return {"ok": True, "service": "bladerunner-api", "auth_enabled": auth_enabled}

    @app.post("/api/auth/login")
    def login(request: Request, payload: LoginRequest):
        if not _check_rate_limit(_client_ip(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _ensure_jwt_ready()
        user = _authenticate(payload.username, payload.password)
        if not user:
            raise HTTPException(status_code=401, detail="Invalid credentials")
        uid = user.get("user_id") or user.get("username")
        perms = user.get("permissions", [])
        access = _create_jwt(
            {"sub": payload.username, "user_id": uid, "permissions": perms},
            timedelta(minutes=access_token_expire_minutes),
        )
        refresh = _create_jwt(
            {"sub": payload.username, "user_id": uid, "type": "refresh"},
            timedelta(days=refresh_token_expire_days),
        )
        return TokenResponse(
            access_token=access,
            refresh_token=refresh,
            expires_in=access_token_expire_minutes * 60,
        )

    @app.post("/api/auth/refresh")
    def refresh(request: Request, body: RefreshTokenRequest):
        if not _check_rate_limit(_client_ip(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _ensure_jwt_ready()
        payload = _verify_jwt(body.refresh_token)
        if not payload or payload.get("type") != "refresh":
            raise HTTPException(status_code=401, detail="Invalid refresh token")
        username = payload.get("sub")
        uid = payload.get("user_id")
        user = next((u for u in users if u.get("username") == username), None)
        perms = user.get("permissions", []) if user else []
        access = _create_jwt(
            {"sub": username, "user_id": uid, "permissions": perms},
            timedelta(minutes=access_token_expire_minutes),
        )
        return TokenResponse(
            access_token=access,
            refresh_token=body.refresh_token,
            expires_in=access_token_expire_minutes * 60,
        )

    @app.get("/api/auth/me")
    def me(
        request: Request,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        if not _check_rate_limit(_client_ip(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        user = _require_auth(x_api_key)
        if not user:
            raise HTTPException(status_code=401, detail="JWT token required")
        return user

    @app.post("/api/sessions", response_model=SessionResponse)
    def create_session(
        request: Request,
        payload: SessionCreateRequest,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        if not _check_rate_limit(_client_ip(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _require_auth(x_api_key)
        br_id = _new_br_session_id()
        SessionManager().create_session(br_id)
        session = store.create_session(
            user_id=payload.user_id,
            title=payload.title,
            bladerunner_session_id=br_id,
        )
        return SessionResponse(
            session_id=session["id"],
            user_id=session["user_id"],
            title=session["title"],
            created_at=session["created_at"],
            updated_at=session["updated_at"],
        )

    @app.get("/api/sessions", response_model=list[SessionResponse])
    def list_sessions(
        request: Request,
        user_id: str = Query(..., min_length=1, max_length=128),
        limit: int = Query(50, ge=1, le=200),
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        if not _check_rate_limit(_client_ip(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _require_auth(x_api_key)
        return [
            SessionResponse(
                session_id=s["id"],
                user_id=s["user_id"],
                title=s["title"],
                created_at=s["created_at"],
                updated_at=s["updated_at"],
            )
            for s in store.list_sessions(user_id=user_id, limit=limit)
        ]

    @app.get("/api/sessions/{session_id}/messages", response_model=SessionMessagesResponse)
    def list_messages(
        request: Request,
        session_id: str,
        user_id: str = Query(..., min_length=1, max_length=128),
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        if not _check_rate_limit(_client_ip(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _require_auth(x_api_key)
        session = store.get_session(user_id=user_id, session_id=session_id)
        if not session:
            raise HTTPException(status_code=404, detail="Session not found")
        return SessionMessagesResponse(
            session_id=session_id,
            messages=store.list_messages(session_id=session_id),
        )

    @app.post("/api/uploads/image", response_model=UploadResponse)
    async def upload_image(
        request: Request,
        user_id: str = Query(..., min_length=1, max_length=128),
        file: UploadFile = File(...),
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        if not _check_rate_limit(_client_ip(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _require_auth(x_api_key)
        content = await file.read()
        _validate_upload(file, content)
        _check_quota(user_id, len(content))
        base = Path(config.get("api.uploads_dir", "~/.bladerunner/uploads")).expanduser()
        target_dir = base / _sanitize_uid(user_id)
        target_dir.mkdir(parents=True, exist_ok=True)
        name = f"{uuid.uuid4().hex[:12]}_{Path(file.filename or 'image').name}"
        target = (target_dir / name).resolve()
        if not str(target).startswith(str(base.resolve())):
            raise HTTPException(status_code=400, detail="Invalid file path")
        target.write_bytes(content)
        return UploadResponse(
            file_path=str(target),
            original_name=file.filename or "image",
            size_bytes=len(content),
        )

    @app.post("/api/chat", response_model=ChatResponse)
    async def chat(
        request: Request,
        payload: ChatRequest,
        x_api_key: str | None = Header(default=None, alias="X-API-Key"),
    ):
        if not _check_rate_limit(_client_ip(request)):
            raise HTTPException(status_code=429, detail="Rate limit exceeded")
        _require_auth(x_api_key)
        session = _resolve_session(payload.user_id, payload.session_id)
        store.add_message(session["id"], "user", payload.message)

        agent, warnings = _make_agent(payload, session, is_streaming=False)
        prompt = _build_prompt_with_images(payload.message, payload.image_paths)
        timeout = float(config.get("api.chat_timeout_seconds", 300))
        try:
            loop = asyncio.get_running_loop()
            answer = await asyncio.wait_for(
                loop.run_in_executor(None, agent.execute, prompt),
                timeout=timeout,
            )
        except TimeoutError as exc:
            raise HTTPException(status_code=504, detail=f"Agent timed out after {timeout:.0f}s") from exc

        store.add_message(session["id"], "assistant", answer)
        store.touch_session(session["id"])
        return ChatResponse(
            session_id=session["id"],
            answer=answer,
            model=agent.model,
            web_search_used=agent.was_web_search_used(),
            warnings=warnings,
        )

    @app.websocket("/ws/chat")
    async def ws_chat(websocket: WebSocket):
        await websocket.accept()
        try:
            payload = ChatRequest(**await websocket.receive_json())
            api_key = websocket.headers.get("x-api-key") or websocket.query_params.get("api_key")
            _require_auth(api_key)

            await websocket.send_json({"type": "status", "status": "initializing"})
            session = _resolve_session(payload.user_id, payload.session_id)
            payload.session_id = session["id"]
            store.add_message(session["id"], "user", payload.message)

            agent, _ = _make_agent(payload, session, is_streaming=True)

            loop = asyncio.get_running_loop()
            queue = asyncio.Queue()

            def on_chunk(text):
                loop.call_soon_threadsafe(queue.put_nowait, text)

            agent.stream_callback = on_chunk
            prompt = _build_prompt_with_images(payload.message, payload.image_paths)

            async def _run():
                try:
                    return await loop.run_in_executor(None, lambda: agent.execute(prompt, use_streaming=True))
                finally:
                    await queue.put(None)

            agent_task = asyncio.create_task(_run())

            async def _drain():
                while True:
                    chunk = await queue.get()
                    if chunk is None:
                        break
                    await websocket.send_json({"type": "chunk", "delta": chunk})

            async def _control():
                while not agent_task.done():
                    try:
                        msg = await asyncio.wait_for(websocket.receive_json(), timeout=0.1)
                        if msg.get("type") == "interrupt":
                            agent.interrupted = True
                            await websocket.send_json({"type": "status", "status": "interrupting"})
                        elif msg.get("type") == "ping":
                            await websocket.send_json({"type": "pong"})
                    except TimeoutError:
                        pass
                    except Exception as exc:
                        logger.warning("WS control error: %s", exc)
                        agent.interrupted = True
                        break

            await asyncio.gather(_drain(), _control())
            answer = await agent_task
            store.add_message(session["id"], "assistant", answer)
            store.touch_session(session["id"])
            await websocket.send_json(
                {
                    "type": "final",
                    "session_id": session["id"],
                    "answer": answer,
                    "model": agent.model,
                    "web_search_used": agent.was_web_search_used(),
                    "interrupted": agent.interrupted,
                }
            )
            await websocket.close()

        except HTTPException as exc:
            await websocket.send_json({"type": "error", "message": exc.detail})
            await websocket.close(code=1008)
        except Exception as exc:
            logger.exception("Unhandled WebSocket error: %s", exc)
            await websocket.send_json({"type": "error", "message": str(exc)})
            await websocket.close(code=1011)

    return app


app = create_app()


def main():
    load_dotenv()
    config = Config()
    configure_logging(config, service_name="bladerunner.api")
    uvicorn.run(
        "bladerunner.api:app",
        host=config.get("api.host", "127.0.0.1"),
        port=int(config.get("api.port", 8000)),
        reload=False,
        log_level=str(config.get("logging.level", "info")).lower(),
        access_log=bool(config.get("logging.uvicorn_access_log", True)),
    )

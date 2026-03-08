"""Tests for FastAPI server endpoints and error handling."""

from pathlib import Path

from fastapi.testclient import TestClient

from bladerunner import api_server
from bladerunner.adk_bridge import GroundedResponse


def _build_client() -> TestClient:
    """Create a test client from app factory."""
    app = api_server.create_app()
    return TestClient(app)


def test_health_endpoint() -> None:
    """Health endpoint should report service liveness."""
    client = _build_client()
    res = client.get("/api/health")

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["service"] == "bladerunner-console"


def test_google_adk_runtime_error_maps_to_400(monkeypatch) -> None:
    """Non-rate-limit runtime errors should map to HTTP 400."""
    client = _build_client()

    def _raise_runtime_error(*args, **kwargs):
        raise RuntimeError("GOOGLE_API_KEY environment variable not set")

    monkeypatch.setattr(api_server.GoogleADKBridge, "generate", _raise_runtime_error)

    res = client.post(
        "/api/chat",
        json={
            "user_id": "user-1",
            "message": "hello",
            "engine": "google_adk",
        },
    )

    assert res.status_code == 400
    assert "GOOGLE_API_KEY" in res.json()["detail"]


def test_google_adk_rate_limit_maps_to_429(monkeypatch) -> None:
    """Rate-limit runtime errors should map to HTTP 429."""
    client = _build_client()

    def _raise_rate_limit(*args, **kwargs):
        raise RuntimeError("Google Gemini rate limit exceeded")

    monkeypatch.setattr(api_server.GoogleADKBridge, "generate", _raise_rate_limit)

    res = client.post(
        "/api/chat",
        json={
            "user_id": "user-1",
            "message": "hello",
            "engine": "google_adk",
        },
    )

    assert res.status_code == 429


def test_google_adk_success_returns_sources(monkeypatch) -> None:
    """Google ADK path should return answer and sources payload."""
    client = _build_client()

    def _ok(*args, **kwargs):
        return GroundedResponse(
            answer="Grounded response",
            sources=[{"title": "Source A", "url": "https://example.com"}],
            provider="gemini_rest_grounded",
        )

    monkeypatch.setattr(api_server.GoogleADKBridge, "generate", _ok)

    res = client.post(
        "/api/chat",
        json={
            "user_id": "user-1",
            "message": "hello",
            "engine": "google_adk",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["answer"] == "Grounded response"
    assert payload["engine"] == "gemini_rest_grounded"
    assert payload["sources"][0]["url"] == "https://example.com"


def test_auth_enforcement_when_enabled(monkeypatch) -> None:
    """API should enforce X-API-Key when auth is enabled."""
    original_default = api_server.Config._default_config

    def _auth_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})
        cfg["api"].setdefault("auth", {})
        cfg["api"]["auth"]["enabled"] = True
        cfg["api"]["auth"]["keys"] = ["secret-key"]
        return cfg

    monkeypatch.setattr(api_server.Config, "_default_config", _auth_config)
    client = _build_client()

    assert client.get("/api/health").status_code == 401
    assert client.get("/api/health", headers={"X-API-Key": "secret-key"}).status_code == 200


def test_image_upload_endpoint() -> None:
    """Upload endpoint should persist image and return its path."""
    client = _build_client()

    files = {"file": ("screen.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")}
    res = client.post("/api/uploads/image?user_id=uploader", files=files)

    assert res.status_code == 200
    payload = res.json()
    assert payload["file_path"].endswith(".png")
    assert Path(payload["file_path"]).exists()


def test_websocket_streaming_chat(monkeypatch) -> None:
    """WebSocket endpoint should send chunks and a final message."""
    client = _build_client()

    def _fake_execute(self, prompt, use_streaming=False):
        if use_streaming and self.stream_callback:
            self.stream_callback("hel")
            self.stream_callback("lo")
        return "hello"

    monkeypatch.setattr(api_server.Agent, "execute", _fake_execute)

    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json(
            {
                "user_id": "ws-user",
                "message": "hello",
                "engine": "bladerunner",
                "enable_streaming": True,
                "permission_profile": "none",
            }
        )

        # First message should be status
        status = ws.receive_json()
        assert status["type"] == "status"
        
        # Then chunks
        first = ws.receive_json()
        second = ws.receive_json()
        
        # Then final
        final = ws.receive_json()

    assert first["type"] == "chunk"
    assert second["type"] == "chunk"
    assert final["type"] == "final"
    assert final["answer"] == "hello"


def test_jwt_login_success(monkeypatch) -> None:
    """JWT login should return access and refresh tokens."""
    import bcrypt

    # Pre-hash password to avoid passlib initialization issues
    password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode('utf-8')

    original_default = api_server.Config._default_config

    def _jwt_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})
        cfg["api"].setdefault("auth", {})
        cfg["api"]["auth"]["enabled"] = True
        cfg["api"]["auth"]["jwt"] = {
            "enabled": True,
            "secret_key": "test-secret-key-for-jwt",
            "algorithm": "HS256",
            "access_token_expire_minutes": 60,
            "refresh_token_expire_days": 7,
        }
        cfg["api"]["auth"]["users"] = [
            {
                "username": "testuser",
                "password_hash": password_hash,
                "user_id": "test-001",
                "permissions": ["read", "write"],
            }
        ]
        return cfg

    monkeypatch.setattr(api_server.Config, "_default_config", _jwt_config)
    monkeypatch.setenv("BLADERUNNER_JWT_SECRET", "test-secret-key-for-jwt-32-chars!!")
    client = _build_client()

    res = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "testpass123"},
    )

    assert res.status_code == 200
    payload = res.json()
    assert "access_token" in payload
    assert "refresh_token" in payload
    assert payload["token_type"] == "bearer"


def test_jwt_login_invalid_credentials(monkeypatch) -> None:
    """JWT login should reject invalid credentials."""
    import bcrypt

    password_hash = bcrypt.hashpw(b"correctpass", bcrypt.gensalt()).decode('utf-8')

    original_default = api_server.Config._default_config

    def _jwt_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})
        cfg["api"]["auth"]["enabled"] = True
        cfg["api"]["auth"]["jwt"] = {
            "enabled": True,
            "secret_key": "test-secret-key-with-minimum-32chars",
            "algorithm": "HS256",
        }
        cfg["api"]["auth"]["users"] = [
            {
                "username": "testuser",
                "password_hash": password_hash,
                "user_id": "test-001",
            }
        ]
        return cfg

    monkeypatch.setattr(api_server.Config, "_default_config", _jwt_config)
    monkeypatch.setenv("BLADERUNNER_JWT_SECRET", "test-secret-key-with-minimum-32chars")
    client = _build_client()

    res = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "wrongpass"},
    )

    assert res.status_code == 401


def test_jwt_token_authentication(monkeypatch) -> None:
    """API endpoints should accept valid JWT tokens."""
    from datetime import datetime, timedelta, timezone
    import jwt as pyjwt
    import bcrypt

    password_hash = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode('utf-8')
    secret = "test-jwt-secret-with-minimum-32chars"

    original_default = api_server.Config._default_config

    def _jwt_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})
        cfg["api"]["auth"]["enabled"] = True
        cfg["api"]["auth"]["jwt"] = {
            "enabled": True,
            "secret_key": secret,
            "algorithm": "HS256",
        }
        cfg["api"]["auth"]["users"] = [
            {
                "username": "testuser",
                "password_hash": password_hash,
                "user_id": "test-001",
            }
        ]
        return cfg

    monkeypatch.setattr(api_server.Config, "_default_config", _jwt_config)
    monkeypatch.setenv("BLADERUNNER_JWT_SECRET", secret)
    client = _build_client()

    # Create a valid token
    token = pyjwt.encode(
        {
            "sub": "testuser",
            "user_id": "test-001",
            "exp": datetime.now(timezone.utc) + timedelta(hours=1),
        },
        secret,
        algorithm="HS256",
    )

    # Should work without static key when using JWT
    res = client.get("/api/health", headers={"X-API-Key": token})
    assert res.status_code == 200


def test_upload_size_limit_enforcement(monkeypatch) -> None:
    """Upload endpoint should reject files exceeding size limit."""
    original_default = api_server.Config._default_config

    def _limit_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})
        cfg["api"]["uploads"] = {
            "max_size_mb": 0.001,  # 1KB limit for testing
            "allowed_types": ["image/png"],
            "per_user_quota_mb": 100,
            "retention_days": 30,
        }
        return cfg

    monkeypatch.setattr(api_server.Config, "_default_config", _limit_config)
    client = _build_client()

    # Create a 2KB file (exceeds 1KB limit)
    large_content = b"\x89PNG\r\n\x1a\n" + (b"x" * 2048)
    files = {"file": ("large.png", large_content, "image/png")}
    res = client.post("/api/uploads/image?user_id=uploader", files=files)

    assert res.status_code == 413
    assert "too large" in res.json()["detail"].lower()


def test_upload_type_restriction(monkeypatch) -> None:
    """Upload endpoint should reject disallowed MIME types."""
    original_default = api_server.Config._default_config

    def _type_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})
        cfg["api"]["uploads"] = {
            "allowed_types": ["image/png"],  # Only PNG allowed
        }
        return cfg

    monkeypatch.setattr(api_server.Config, "_default_config", _type_config)
    client = _build_client()

    files = {"file": ("doc.pdf", b"content", "application/pdf")}
    res = client.post("/api/uploads/image?user_id=uploader", files=files)

    assert res.status_code == 400
    assert "unsupported file type" in res.json()["detail"].lower()


def test_upload_quota_checking(monkeypatch, tmp_path) -> None:
    """Upload endpoint should enforce per-user quota limits."""
    upload_dir = tmp_path / "uploads"
    user_dir = upload_dir / "quotauser"
    user_dir.mkdir(parents=True)

    # Create existing file that uses 0.09MB of quota
    (user_dir / "existing.png").write_bytes(b"x" * (90 * 1024))

    original_default = api_server.Config._default_config

    def _quota_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})
        cfg["api"]["uploads_dir"] = str(upload_dir)
        cfg["api"]["uploads"] = {
            "max_size_mb": 1,
            "per_user_quota_mb": 0.1,  # 100KB quota
            "allowed_types": ["image/png"],
        }
        return cfg

    monkeypatch.setattr(api_server.Config, "_default_config", _quota_config)
    client = _build_client()

    # Try to upload 20KB file (would exceed quota)
    files = {"file": ("new.png", b"\x89PNG\r\n" + (b"x" * (20 * 1024)), "image/png")}
    res = client.post("/api/uploads/image?user_id=quotauser", files=files)

    assert res.status_code == 413
    assert "quota exceeded" in res.json()["detail"].lower()


def test_websocket_interruption(monkeypatch) -> None:
    """WebSocket should handle interrupt messages and stop agent."""
    import time

    client = _build_client()

    def _long_execution(self, prompt, use_streaming=False):
        # Simulate long-running task with interruption check
        for i in range(10):
            if self.interrupted:
                return "⚠️ Task interrupted by user"
            if use_streaming and self.stream_callback:
                self.stream_callback(f"step {i} ")
            time.sleep(0.01)
        return "completed all steps"

    monkeypatch.setattr(api_server.Agent, "execute", _long_execution)

    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json(
            {
                "user_id": "interrupter",
                "message": "long task",
                "engine": "bladerunner",
                "enable_streaming": True,
                "permission_profile": "none",
            }
        )

        # Receive first status message
        status = ws.receive_json()
        assert status["type"] == "status"

        # Receive a few chunks
        ws.receive_json()
        ws.receive_json()

        # Send interrupt signal
        ws.send_json({"type": "interrupt"})

        # Should receive interrupting status
        interrupt_status = ws.receive_json()
        assert interrupt_status.get("type") == "status" or interrupt_status.get("type") == "chunk"

        # Collect remaining messages until final
        final = None
        while True:
            msg = ws.receive_json()
            if msg["type"] == "final":
                final = msg
                break

    assert final is not None
    assert final.get("interrupted") is True or "interrupt" in final["answer"].lower()


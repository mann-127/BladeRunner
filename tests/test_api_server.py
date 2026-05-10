"""Tests for FastAPI server endpoints."""

import time
from datetime import UTC
from pathlib import Path

from fastapi.middleware.cors import CORSMiddleware
from fastapi.testclient import TestClient

from bladerunner import api


def _build_client():
    app = api.create_app()
    return TestClient(app)


def test_health_endpoint():
    client = _build_client()
    res = client.get("/api/health")

    assert res.status_code == 200
    payload = res.json()
    assert payload["ok"] is True
    assert payload["service"] == "bladerunner-api"


def test_cors_wildcard_disables_credentials():
    app = api.create_app()
    cors = next(m for m in app.user_middleware if m.cls is CORSMiddleware)

    assert cors.kwargs["allow_origins"] == ["*"]
    assert cors.kwargs["allow_credentials"] is False


def test_cors_specific_origins_allow_credentials(monkeypatch):
    original_default = api.Config._defaults

    def _cors_config(self):
        cfg = original_default(self)
        cfg["api"]["cors_origins"] = ["https://example.com"]
        return cfg

    monkeypatch.setattr(api.Config, "_defaults", _cors_config)
    app = api.create_app()
    cors = next(m for m in app.user_middleware if m.cls is CORSMiddleware)

    assert cors.kwargs["allow_origins"] == ["https://example.com"]
    assert cors.kwargs["allow_credentials"] is True


def test_chat_returns_answer(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    client = _build_client()

    def _fake_execute(self, prompt, use_streaming=False):
        return "Hello from agent"

    monkeypatch.setattr(api.Agent, "execute", _fake_execute)

    res = client.post(
        "/api/chat",
        json={
            "user_id": "user-1",
            "message": "hello",
            "permission_profile": "none",
        },
    )

    assert res.status_code == 200
    payload = res.json()
    assert payload["answer"] == "Hello from agent"
    assert "session_id" in payload
    assert "model" in payload


def test_chat_timeout_maps_to_504(monkeypatch):
    original_default = api.Config._defaults

    def _timeout_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})["chat_timeout_seconds"] = 0.01
        return cfg

    def _slow_execute(self, prompt, use_streaming=False):
        time.sleep(0.05)
        return "late"

    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setattr(api.Config, "_defaults", _timeout_config)
    monkeypatch.setattr(api.Agent, "execute", _slow_execute)

    client = _build_client()
    res = client.post(
        "/api/chat",
        json={
            "user_id": "timeout-user",
            "message": "hello",
            "permission_profile": "none",
        },
    )

    assert res.status_code == 504
    assert "timed out" in res.json()["detail"].lower()


def test_auth_enforcement_when_enabled(monkeypatch):
    original_default = api.Config._defaults

    def _auth_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {}).setdefault("auth", {})
        cfg["api"]["auth"]["enabled"] = True
        cfg["api"]["auth"]["keys"] = ["secret-key"]
        return cfg

    monkeypatch.setattr(api.Config, "_defaults", _auth_config)
    client = _build_client()

    assert client.get("/api/health").status_code == 401
    assert client.get("/api/health", headers={"X-API-Key": "secret-key"}).status_code == 200


def test_image_upload_endpoint(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    client = _build_client()

    files = {"file": ("screen.png", b"\x89PNG\r\n\x1a\ncontent", "image/png")}
    res = client.post("/api/uploads/image?user_id=uploader", files=files)

    assert res.status_code == 200
    payload = res.json()
    assert payload["file_path"].endswith(".png")
    assert Path(payload["file_path"]).exists()


def test_upload_size_limit_enforcement(monkeypatch):
    original_default = api.Config._defaults

    def _limit_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})["uploads"] = {
            "max_size_mb": 0.001,
            "allowed_types": ["image/png"],
            "per_user_quota_mb": 100,
            "retention_days": 30,
        }
        return cfg

    monkeypatch.setattr(api.Config, "_defaults", _limit_config)
    client = _build_client()

    large_content = b"\x89PNG\r\n\x1a\n" + (b"x" * 2048)
    files = {"file": ("large.png", large_content, "image/png")}
    res = client.post("/api/uploads/image?user_id=uploader", files=files)

    assert res.status_code == 413
    assert "too large" in res.json()["detail"].lower()


def test_upload_type_restriction(monkeypatch):
    original_default = api.Config._defaults

    def _type_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})["uploads"] = {"allowed_types": ["image/png"]}
        return cfg

    monkeypatch.setattr(api.Config, "_defaults", _type_config)
    client = _build_client()

    files = {"file": ("doc.pdf", b"content", "application/pdf")}
    res = client.post("/api/uploads/image?user_id=uploader", files=files)

    assert res.status_code == 400
    assert "unsupported" in res.json()["detail"].lower()


def test_upload_quota_enforcement(monkeypatch, tmp_path):
    upload_dir = tmp_path / "uploads"
    user_dir = upload_dir / "quotauser"
    user_dir.mkdir(parents=True)
    (user_dir / "existing.png").write_bytes(b"x" * (90 * 1024))

    original_default = api.Config._defaults

    def _quota_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {})
        cfg["api"]["uploads_dir"] = str(upload_dir)
        cfg["api"]["uploads"] = {
            "max_size_mb": 1,
            "per_user_quota_mb": 0.1,
            "allowed_types": ["image/png"],
        }
        return cfg

    monkeypatch.setattr(api.Config, "_defaults", _quota_config)
    client = _build_client()

    files = {"file": ("new.png", b"\x89PNG\r\n" + (b"x" * (20 * 1024)), "image/png")}
    res = client.post("/api/uploads/image?user_id=quotauser", files=files)

    assert res.status_code == 413
    assert "quota" in res.json()["detail"].lower()


def test_websocket_chat(monkeypatch):
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    client = _build_client()

    def _fake_execute(self, prompt, use_streaming=False):
        return "hello from ws"

    monkeypatch.setattr(api.Agent, "execute", _fake_execute)

    messages = []
    with client.websocket_connect("/ws/chat") as ws:
        ws.send_json(
            {
                "user_id": "ws-user",
                "message": "hello",
                "permission_profile": "none",
            }
        )
        from starlette.websockets import WebSocketDisconnect

        try:
            while True:
                messages.append(ws.receive_json())
        except WebSocketDisconnect:
            pass

    types = [m["type"] for m in messages]
    assert "status" in types
    assert "final" in types
    final = next(m for m in messages if m["type"] == "final")
    assert final["answer"] == "hello from ws"


def test_jwt_login_success(monkeypatch):
    import bcrypt

    password_hash = bcrypt.hashpw(b"testpass123", bcrypt.gensalt()).decode("utf-8")
    original_default = api.Config._defaults

    def _jwt_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {}).setdefault("auth", {})
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

    monkeypatch.setattr(api.Config, "_defaults", _jwt_config)
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


def test_jwt_login_invalid_credentials(monkeypatch):
    import bcrypt

    password_hash = bcrypt.hashpw(b"correctpass", bcrypt.gensalt()).decode("utf-8")
    original_default = api.Config._defaults

    def _jwt_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {}).setdefault("auth", {})
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

    monkeypatch.setattr(api.Config, "_defaults", _jwt_config)
    monkeypatch.setenv("BLADERUNNER_JWT_SECRET", "test-secret-key-with-minimum-32chars")
    client = _build_client()

    res = client.post(
        "/api/auth/login",
        json={"username": "testuser", "password": "wrongpass"},
    )

    assert res.status_code == 401


def test_jwt_token_authentication(monkeypatch):
    from datetime import datetime, timedelta

    import bcrypt
    import jwt as pyjwt

    password_hash = bcrypt.hashpw(b"testpass", bcrypt.gensalt()).decode("utf-8")
    secret = "test-jwt-secret-with-minimum-32chars"
    original_default = api.Config._defaults

    def _jwt_config(self):
        cfg = original_default(self)
        cfg.setdefault("api", {}).setdefault("auth", {})
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

    monkeypatch.setattr(api.Config, "_defaults", _jwt_config)
    monkeypatch.setenv("BLADERUNNER_JWT_SECRET", secret)
    client = _build_client()

    token = pyjwt.encode(
        {
            "sub": "testuser",
            "user_id": "test-001",
            "exp": datetime.now(UTC) + timedelta(hours=1),
        },
        secret,
        algorithm="HS256",
    )

    res = client.get("/api/health", headers={"X-API-Key": token})
    assert res.status_code == 200

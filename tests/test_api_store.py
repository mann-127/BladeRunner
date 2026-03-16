"""Tests for API SQLite store."""

from pathlib import Path

from bladerunner.api_store import APISessionStore


def test_api_store_create_and_fetch_session(tmp_path: Path) -> None:
    """Store should persist and return session metadata."""
    db_path = tmp_path / "api.db"
    store = APISessionStore(db_path)

    created = store.create_session(
        user_id="user-1",
        title="Case",
        bladerunner_session_id="api_abc123",
    )

    fetched = store.get_session("user-1", created["id"])
    assert fetched is not None
    assert fetched["title"] == "Case"
    assert fetched["bladerunner_session_id"] == "api_abc123"


def test_api_store_messages_round_trip(tmp_path: Path) -> None:
    """Store should persist and list messages in order."""
    store = APISessionStore(tmp_path / "api.db")
    session = store.create_session(
        user_id="user-1",
        title="Case",
        bladerunner_session_id="api_abc123",
    )

    store.add_message(session["id"], "user", "hello")
    store.add_message(session["id"], "assistant", "world")

    messages = store.list_messages(session["id"])
    assert len(messages) == 2
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"

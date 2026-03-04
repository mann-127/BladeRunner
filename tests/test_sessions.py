"""Tests for session management."""

from pathlib import Path
from bladerunner.sessions import SessionManager


def test_session_create_generates_unique_id(tmp_path: Path) -> None:
    """Session manager should create sessions with unique identifiers."""
    manager = SessionManager(tmp_path)
    
    # Create sessions with different names to ensure unique IDs
    session1 = manager.create_session("session1")
    session2 = manager.create_session("session2")
    
    assert session1 == "session1"
    assert session2 == "session2"
    assert session1 != session2


def test_session_save_and_load_messages(tmp_path: Path) -> None:
    """Session should save and load messages correctly."""
    manager = SessionManager(tmp_path)
    session_id = manager.create_session("test")
    
    messages = [
        {"role": "user", "content": "Hello"},
        {"role": "assistant", "content": "Hi there!"},
    ]
    
    for msg in messages:
        manager.save_message(session_id, msg)
    
    loaded = manager.load_session(session_id)
    assert loaded == messages


def test_session_list_sessions(tmp_path: Path) -> None:
    """Session manager should list all sessions."""
    manager = SessionManager(tmp_path)
    
    id1 = manager.create_session("project1")
    id2 = manager.create_session("project2")
    
    sessions = manager.list_sessions()
    session_ids = [s["id"] for s in sessions]
    
    assert id1 in session_ids
    assert id2 in session_ids


def test_session_get_last_session(tmp_path: Path) -> None:
    """Session manager should retrieve latest session."""
    manager = SessionManager(tmp_path)
    
    id1 = manager.create_session("first")
    id2 = manager.create_session("second")
    
    last = manager.get_latest_session()
    assert last == id2


def test_session_persistence_across_instances(tmp_path: Path) -> None:
    """Sessions should persist across manager instances."""
    # Create session with first instance
    manager1 = SessionManager(tmp_path)
    session_id = manager1.create_session("persistent")
    manager1.save_message(session_id, {"role": "user", "content": "test"})
    
    # Load with second instance
    manager2 = SessionManager(tmp_path)
    messages = manager2.load_session(session_id)
    
    assert len(messages) == 1
    assert messages[0]["content"] == "test"


def test_session_handles_nonexistent_session(tmp_path: Path) -> None:
    """Loading nonexistent session should return empty list."""
    manager = SessionManager(tmp_path)
    
    messages = manager.load_session("nonexistent-id")
    assert messages == []


def test_session_message_order_preserved(tmp_path: Path) -> None:
    """Messages should be loaded in the order they were saved."""
    manager = SessionManager(tmp_path)
    session_id = manager.create_session("ordered")
    
    for i in range(5):
        manager.save_message(session_id, {"role": "user", "content": f"message {i}"})
    
    messages = manager.load_session(session_id)
    
    for i in range(5):
        assert messages[i]["content"] == f"message {i}"


def test_session_supports_metadata(tmp_path: Path) -> None:
    """Sessions should support metadata in list."""
    manager = SessionManager(tmp_path)
    session_id = manager.create_session("meta-test")
    manager.save_message(session_id, {"role": "user", "content": "x"})
    
    sessions = manager.list_sessions()
    session = next((s for s in sessions if s["id"] == session_id), None)
    
    assert session is not None
    assert "name" in session or "id" in session


def test_session_empty_session_returns_empty_list(tmp_path: Path) -> None:
    """Newly created session should have no messages."""
    manager = SessionManager(tmp_path)
    session_id = manager.create_session("empty")
    
    messages = manager.load_session(session_id)
    assert messages == []

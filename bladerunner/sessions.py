"""Session management for conversation persistence."""

import json
import logging
from datetime import datetime
from pathlib import Path

logger = logging.getLogger(__name__)


class SessionManager:
    """Manages conversation sessions."""

    def __init__(self, sessions_dir=None):
        default_dir = Path.home() / ".bladerunner" / "sessions"
        self.sessions_dir = Path(sessions_dir) if sessions_dir else default_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, name=None):
        """Create new session and return session ID."""
        session_id = name or datetime.now().strftime("%Y%m%d_%H%M%S")
        session_file = self.sessions_dir / f"{session_id}.jsonl"

        # Write metadata
        self._append_log(
            session_file,
            {
                "type": "session_start",
                "id": session_id,
                "timestamp": datetime.now().isoformat(),
            },
        )

        return session_id

    def load_session(self, session_id):
        """Load conversation history from session."""
        session_file = self.sessions_dir / f"{session_id}.jsonl"

        if not session_file.exists():
            return []

        messages = []
        try:
            with open(session_file) as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("type") == "message":
                        messages.append(entry["content"])
        except Exception as exc:
            logger.warning("Failed to load session '%s': %s", session_id, exc)
            return []

        return messages

    def save_message(self, session_id, message):
        """Append message to session log."""
        role = message.get("role")
        if role not in {"user", "assistant", "tool"}:
            return

        session_file = self.sessions_dir / f"{session_id}.jsonl"
        self._append_log(
            session_file,
            {
                "type": "message",
                "content": message,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def list_sessions(self):
        """List all sessions."""
        sessions = []
        for session_file in self.sessions_dir.glob("*.jsonl"):
            try:
                with open(session_file) as f:
                    lines = f.readlines()
                    if not lines:
                        continue

                    first = json.loads(lines[0])
                    last = json.loads(lines[-1])

                    sessions.append(
                        {
                            "id": first.get("id", session_file.stem),
                            "created": first.get("timestamp", ""),
                            "updated": last.get("timestamp", ""),
                            "message_count": len(lines) - 1,
                        }
                    )
            except Exception as exc:
                logger.warning("Failed to inspect session file '%s': %s", session_file, exc)
                continue

        return sorted(sessions, key=lambda x: x.get("updated", ""), reverse=True)

    def get_latest_session(self):
        """Get ID of the most recent session."""
        sessions = self.list_sessions()
        return sessions[0]["id"] if sessions else None

    def _append_log(self, file, entry):
        """Append JSON entry to log file."""
        entry = self._make_serializable(entry)
        try:
            with open(file, "a") as f:
                f.write(json.dumps(entry, default=str) + "\n")
        except Exception as exc:
            logger.error("Failed to append session log '%s': %s", file, exc)

    def _make_serializable(self, obj):
        """Convert nested objects to JSON-safe structures."""
        if isinstance(obj, dict):
            return {k: self._make_serializable(v) for k, v in obj.items()}
        if isinstance(obj, list):
            return [self._make_serializable(item) for item in obj]
        if hasattr(obj, "model_dump"):
            return self._make_serializable(obj.model_dump())
        if hasattr(obj, "dict") and callable(getattr(obj, "dict")):
            try:
                return self._make_serializable(obj.dict())
            except Exception:
                pass
        if hasattr(obj, "__dict__"):
            return {k: self._make_serializable(v) for k, v in obj.__dict__.items() if not k.startswith("_")}
        return obj

"""Session management for conversation persistence."""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


class SessionManager:
    """Manages conversation sessions."""

    def __init__(self, sessions_dir: Optional[Path] = None):
        default_dir = Path.home() / ".bladerunner" / "sessions"
        self.sessions_dir = Path(sessions_dir) if sessions_dir else default_dir
        self.sessions_dir.mkdir(parents=True, exist_ok=True)

    def create_session(self, name: Optional[str] = None) -> str:
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

    def load_session(self, session_id: str) -> List[Dict]:
        """Load conversation history from session."""
        session_file = self.sessions_dir / f"{session_id}.jsonl"

        if not session_file.exists():
            return []

        messages = []
        try:
            with open(session_file, "r") as f:
                for line in f:
                    entry = json.loads(line)
                    if entry.get("type") == "message":
                        messages.append(entry["content"])
        except Exception:
            return []

        return messages

    def save_message(self, session_id: str, message: Dict):
        """Append message to session log."""
        session_file = self.sessions_dir / f"{session_id}.jsonl"
        self._append_log(
            session_file,
            {
                "type": "message",
                "content": message,
                "timestamp": datetime.now().isoformat(),
            },
        )

    def list_sessions(self) -> List[Dict]:
        """List all sessions."""
        sessions = []
        for session_file in self.sessions_dir.glob("*.jsonl"):
            try:
                with open(session_file, "r") as f:
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
            except Exception:
                continue

        return sorted(sessions, key=lambda x: x.get("updated", ""), reverse=True)

    def get_latest_session(self) -> Optional[str]:
        """Get ID of the most recent session."""
        sessions = self.list_sessions()
        return sessions[0]["id"] if sessions else None

    def _append_log(self, file: Path, entry: Dict):
        """Append JSON entry to log file."""
        with open(file, "a") as f:
            f.write(json.dumps(entry) + "\n")

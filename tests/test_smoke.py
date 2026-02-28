from pathlib import Path

from bladerunner.config import Config
from bladerunner.sessions import SessionManager
from bladerunner.skills import SkillManager


def test_config_defaults(tmp_path: Path) -> None:
    config = Config(tmp_path / "config.yml")

    assert config.get("model") == "haiku"
    assert config.get("permissions.enabled") is True
    assert config.resolve_model("haiku").startswith("anthropic/")


def test_sessions_roundtrip(tmp_path: Path) -> None:
    manager = SessionManager(tmp_path)
    session_id = manager.create_session("smoke")

    manager.save_message(session_id, {"role": "user", "content": "hello"})
    messages = manager.load_session(session_id)

    assert messages == [{"role": "user", "content": "hello"}]


def test_skills_loading(tmp_path: Path) -> None:
    skill_dir = tmp_path / "example-skill"
    skill_dir.mkdir(parents=True, exist_ok=True)

    (skill_dir / "SKILL.md").write_text("""---
name: smoke-skill
description: smoke test skill
tools: [Read]
---

You are a test skill.
""")

    manager = SkillManager(tmp_path)
    skills = manager.list_skills()

    assert skills[0]["name"] == "smoke-skill"

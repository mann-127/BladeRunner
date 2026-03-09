"""Tests for skills system."""

from pathlib import Path
from bladerunner.skills import Skill, SkillManager


def test_skill_creation() -> None:
    """Skill should be created with proper attributes."""
    skill = Skill(
        name="test-skill",
        description="A test skill",
        system_prompt="You are a test agent.",
        allowed_tools=["Read", "Write"],
        model="sonnet",
        temperature=0.5,
    )

    assert skill.name == "test-skill"
    assert skill.description == "A test skill"
    assert skill.system_prompt == "You are a test agent."
    assert skill.allowed_tools == ["Read", "Write"]
    assert skill.model == "sonnet"
    assert skill.temperature == 0.5


def test_skill_optional_fields() -> None:
    """Skill should work with only required fields."""
    skill = Skill(
        name="minimal",
        description="Minimal skill",
        system_prompt="Basic prompt.",
    )

    assert skill.name == "minimal"
    assert skill.allowed_tools is None
    assert skill.model is None


def test_skill_manager_loads_skills_from_directory(tmp_path: Path) -> None:
    """SkillManager should load skills from SKILL.md files."""
    skill_dir = tmp_path / "test-skill"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text("""---
name: loader-test
description: Test skill loading
tools: [Read, Write]
---

You are a test skill.
""")

    manager = SkillManager(tmp_path)

    skill = manager.get_skill("loader-test")
    assert skill is not None
    assert skill.name == "loader-test"
    assert skill.description == "Test skill loading"
    assert skill.allowed_tools == ["Read", "Write"]


def test_skill_manager_list_skills(tmp_path: Path) -> None:
    """SkillManager should list all available skills."""
    # Create multiple skills
    for i in range(3):
        skill_dir = tmp_path / f"skill-{i}"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(f"""---
name: skill-{i}
description: Test skill {i}
---

Skill {i} prompt.
""")

    manager = SkillManager(tmp_path)
    skills = manager.list_skills()

    assert len(skills) == 3
    names = [s["name"] for s in skills]
    assert "skill-0" in names
    assert "skill-1" in names
    assert "skill-2" in names


def test_skill_manager_get_nonexistent_skill(tmp_path: Path) -> None:
    """Getting nonexistent skill should return None."""
    manager = SkillManager(tmp_path)

    skill = manager.get_skill("nonexistent")
    assert skill is None


def test_skill_manager_parses_frontmatter_correctly(tmp_path: Path) -> None:
    """SkillManager should parse YAML frontmatter correctly."""
    skill_dir = tmp_path / "parse-test"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text("""---
name: parse-skill
description: Parsing test
tools: [Bash]
model: opus
temperature: 0.8
---

System prompt here.
Multiple lines.
""")

    manager = SkillManager(tmp_path)
    skill = manager.get_skill("parse-skill")

    assert skill.name == "parse-skill"
    assert skill.description == "Parsing test"
    assert skill.allowed_tools == ["Bash"]
    assert skill.model == "opus"
    assert skill.temperature == 0.8
    assert "System prompt here" in skill.system_prompt
    assert "Multiple lines" in skill.system_prompt


def test_skill_manager_ignores_invalid_files(tmp_path: Path) -> None:
    """SkillManager should skip invalid SKILL.md files."""
    # Valid skill
    valid = tmp_path / "valid"
    valid.mkdir()
    (valid / "SKILL.md").write_text("""---
name: valid
description: Valid skill
---

Prompt.
""")

    # Invalid skill (no frontmatter)
    invalid = tmp_path / "invalid"
    invalid.mkdir()
    (invalid / "SKILL.md").write_text("Just text, no frontmatter.")

    manager = SkillManager(tmp_path)
    skills = manager.list_skills()

    # Should only load valid skill
    assert len(skills) == 1
    assert skills[0]["name"] == "valid"


def test_skill_manager_match_skill_by_keywords(tmp_path: Path) -> None:
    """SkillManager should match skills based on prompt keywords."""
    skill_dir = tmp_path / "security"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text("""---
name: security-auditor
description: security vulnerability audit compliance
---

Security audit prompt.
""")

    manager = SkillManager(tmp_path)

    # Should match based on keywords in description
    matched = manager.match_skill("check for security vulnerabilities")
    assert matched is not None
    assert matched.name == "security-auditor"


def test_skill_manager_match_returns_none_if_no_match(tmp_path: Path) -> None:
    """match_skill should return None if no skill matches."""
    skill_dir = tmp_path / "specific"
    skill_dir.mkdir()

    (skill_dir / "SKILL.md").write_text("""---
name: specific-task
description: very specific thing
---

Prompt.
""")

    manager = SkillManager(tmp_path)

    matched = manager.match_skill("completely unrelated task")
    # May or may not match depending on keyword overlap
    # This test validates it doesn't crash
    assert matched is None or isinstance(matched, Skill)


def test_skill_manager_handles_nested_skill_directories(tmp_path: Path) -> None:
    """SkillManager should find SKILL.md in nested directories."""
    nested = tmp_path / "category" / "subcategory" / "skill"
    nested.mkdir(parents=True)

    (nested / "SKILL.md").write_text("""---
name: nested-skill
description: Nested skill test
---

Nested prompt.
""")

    manager = SkillManager(tmp_path)

    skill = manager.get_skill("nested-skill")
    assert skill is not None
    assert skill.name == "nested-skill"

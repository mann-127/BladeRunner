"""Skills system for specialized agent capabilities."""

from pathlib import Path
from typing import Dict, List, Optional
import yaml


class Skill:
    """Represents a skill that can be loaded."""

    def __init__(
        self,
        name: str,
        description: str,
        system_prompt: str,
        allowed_tools: Optional[List[str]] = None,
        model: Optional[str] = None,
        temperature: Optional[float] = None,
    ):
        self.name = name
        self.description = description
        self.system_prompt = system_prompt
        self.allowed_tools = allowed_tools
        self.model = model
        self.temperature = temperature


class SkillManager:
    """Manages skills for the agent."""

    def __init__(self, skills_dir: Optional[Path] = None):
        default_dir = Path.home() / ".bladerunner" / "skills"
        self.skills_dir = Path(skills_dir) if skills_dir else default_dir
        self.skills_dir.mkdir(parents=True, exist_ok=True)
        self.skills: Dict[str, Skill] = {}
        self._load_skills()

    def _load_skills(self):
        """Load all SKILL.md files from skills directory."""
        for skill_file in self.skills_dir.rglob("SKILL.md"):
            try:
                skill = self._parse_skill_file(skill_file)
                if skill:
                    self.skills[skill.name] = skill
            except Exception:
                continue

    def _parse_skill_file(self, file_path: Path) -> Optional[Skill]:
        """Parse a SKILL.md file."""
        try:
            content = file_path.read_text()

            # Split frontmatter and body
            if content.startswith("---"):
                parts = content.split("---", 2)
                if len(parts) >= 3:
                    frontmatter = yaml.safe_load(parts[1])
                    body = parts[2].strip()
                else:
                    return None
            else:
                return None

            return Skill(
                name=frontmatter.get("name", ""),
                description=frontmatter.get("description", ""),
                system_prompt=body,
                allowed_tools=frontmatter.get("tools"),
                model=frontmatter.get("model"),
                temperature=frontmatter.get("temperature"),
            )
        except Exception:
            return None

    def get_skill(self, name: str) -> Optional[Skill]:
        """Get a skill by name."""
        return self.skills.get(name)

    def list_skills(self) -> List[Dict[str, str]]:
        """List all available skills."""
        return [
            {"name": skill.name, "description": skill.description}
            for skill in self.skills.values()
        ]

    def match_skill(self, prompt: str) -> Optional[Skill]:
        """Match a skill based on prompt (simple keyword matching)."""
        prompt_lower = prompt.lower()

        for skill in self.skills.values():
            # Simple keyword matching
            if any(word in prompt_lower for word in skill.description.lower().split()):
                return skill

        return None

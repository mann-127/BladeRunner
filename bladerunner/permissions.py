"""Permission system for command and file access control."""

from enum import Enum
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Dict, Optional


class PermissionLevel(Enum):
    """Permission levels."""

    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class PermissionChecker:
    """Checks permissions for operations."""

    def __init__(self, config_path: Optional[Path] = None, profile: str = "standard"):
        self.profile = profile
        self.rules = self._load_profile(profile)

    def _load_profile(self, profile: str) -> Dict[str, Any]:
        """Load permission profile."""
        profiles = {
            "permissive": {
                "files": {"read": {"default": "allow"}, "write": {"default": "allow"}},
                "bash": {"default": "allow"},
            },
            "standard": {
                "files": {
                    "read": {
                        "default": "allow",
                        "deny": ["**/secret*", "**/.env*", "**/password*"],
                    },
                    "write": {
                        "default": "ask",
                        "allow": ["test/**", "docs/**", "*.md"],
                        "deny": ["**/production/**", "**/prod/**"],
                    },
                },
                "bash": {
                    "default": "ask",
                    "deny": ["rm -rf *", "sudo *", "curl * | *", "wget * | *"],
                },
            },
            "strict": {
                "files": {
                    "read": {"default": "ask", "deny": ["**/secret*", "**/.env*"]},
                    "write": {"default": "deny", "allow": ["test/**"]},
                },
                "bash": {
                    "default": "deny",
                    "allow": ["ls *", "cat *", "grep *", "echo *"],
                },
            },
        }

        return profiles.get(profile, profiles["standard"])

    def check_file_read(self, file_path: str) -> PermissionLevel:
        """Check if file read is allowed."""
        return self._check_permission(file_path, self.rules["files"]["read"])

    def check_file_write(self, file_path: str) -> PermissionLevel:
        """Check if file write is allowed."""
        return self._check_permission(file_path, self.rules["files"]["write"])

    def check_bash_command(self, command: str) -> PermissionLevel:
        """Check if bash command is allowed."""
        return self._check_permission(command, self.rules["bash"])

    def _check_permission(self, target: str, rules: Dict) -> PermissionLevel:
        """Check permission based on rules."""
        # Check deny rules first
        for pattern in rules.get("deny", []):
            if fnmatch(target, pattern):
                return PermissionLevel.DENY

        # Check allow rules
        for pattern in rules.get("allow", []):
            if fnmatch(target, pattern):
                return PermissionLevel.ALLOW

        # Use default
        default = rules.get("default", "ask")
        return PermissionLevel(default)

    def prompt_user(self, operation: str, details: str) -> bool:
        """Prompt user for permission."""
        print("\n⚠️  Permission required:")
        print(f"   Operation: {operation}")
        print(f"   Details: {details}")
        response = input("   Allow? [y/N]: ").strip().lower()
        return response in {"y", "yes"}

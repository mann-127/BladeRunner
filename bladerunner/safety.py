"""Safety and permission system — merged from safety.py + permissions.py."""

import hashlib
import re
from enum import Enum
from fnmatch import fnmatch


class PermissionLevel(Enum):
    ALLOW = "allow"
    DENY = "deny"
    ASK = "ask"


class Safety:
    """Unified critical-operation detector and permission checker."""

    _CRITICAL_BASH = [
        (r"\brm\s+-", "Delete files with 'rm'"),
        (r"\brm\s+/", "Delete files with 'rm'"),
        (r"\bdd\s+(if|of)=", "Disk write with 'dd'"),
    ]

    _CRITICAL_CMDS = {
        "mkfs": "Format filesystem",
        "fdisk": "Partition disk",
        "parted": "Partition disk",
    }

    _CRITICAL_WRITE_PATHS = {
        "/etc": "System configuration",
        "/sys": "System kernel interface",
        "/proc": "Process information",
        "~/.ssh": "SSH keys",
        "~/.aws": "AWS credentials",
        ".env": "Environment variables",
    }

    _CRITICAL_EXTENSIONS = {".key", ".pem", ".p12", ".pfx"}

    _SENSITIVE_READ_PATHS = {
        "~/.ssh": "SSH keys",
        "~/.aws": "AWS credentials",
        ".env": "Environment variables",
    }

    _PROFILES = {
        "permissive": {
            "files": {
                "read": {"default": "allow"},
                "write": {"default": "allow"},
            },
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

    def __init__(self, profile="standard"):
        self.profile = profile
        self.rules = self._PROFILES.get(profile, self._PROFILES["standard"])
        self._approved = set()
        self._denied = set()

    # ------------------------------------------------------------------
    # Permission checks
    # ------------------------------------------------------------------

    def check_bash(self, command):
        if self.profile != "permissive" and self._has_shell_operators(command):
            return PermissionLevel.DENY
        return self._check(command, self.rules["bash"])

    def check_file_read(self, path):
        return self._check(path, self.rules["files"]["read"])

    def check_file_write(self, path):
        return self._check(path, self.rules["files"]["write"])

    # ------------------------------------------------------------------
    # Critical-operation detection
    # ------------------------------------------------------------------

    def is_critical_bash(self, command):
        cmd_lower = command.lower()
        for pattern, reason in self._CRITICAL_BASH:
            if re.search(pattern, cmd_lower):
                return True, reason
        for cmd, reason in self._CRITICAL_CMDS.items():
            if cmd in cmd_lower:
                return True, reason
        return False, None

    def is_critical_write(self, path):
        path_lower = path.lower()
        for critical_path, reason in self._CRITICAL_WRITE_PATHS.items():
            if critical_path in path_lower:
                return True, f"Write to sensitive path: {reason}"
        for ext in self._CRITICAL_EXTENSIONS:
            if path.endswith(ext):
                return True, f"Write to {ext} file"
        return False, None

    def is_critical_read(self, path):
        path_lower = path.lower()
        for sensitive_path, reason in self._SENSITIVE_READ_PATHS.items():
            if sensitive_path in path_lower:
                return True, f"Read sensitive file: {reason}"
        return False, None

    # ------------------------------------------------------------------
    # User prompts
    # ------------------------------------------------------------------

    def prompt_approval(self, operation, reason, details):
        """Prompt user for approval of a critical operation, with caching."""
        op_hash = hashlib.sha256(f"{operation}:{details}".encode()).hexdigest()
        if op_hash in self._approved:
            print(f"✓ {operation} (previously approved)", flush=True)
            return True
        if op_hash in self._denied:
            print(f"✗ {operation} (previously denied)", flush=True)
            return False
        print(f"\n⚠️  CRITICAL OPERATION: {operation}")
        print(f"   Reason: {reason}")
        print(f"   Details: {details}")
        try:
            response = input("   Approve? [y]es / [n]o / [a]lways: ").strip().lower()
            if response in ("y", "yes"):
                return True
            if response in ("a", "always"):
                self._approved.add(op_hash)
                return True
            self._denied.add(op_hash)
            return False
        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled")
            return False

    def prompt_permission(self, operation, details):
        """Prompt user for a standard permission check."""
        print(f"\n⚠️  Permission required: {operation}")
        print(f"   Details: {details}")
        try:
            return input("   Allow? [y/N]: ").strip().lower() in ("y", "yes")
        except (KeyboardInterrupt, EOFError):
            return False

    # ------------------------------------------------------------------
    # Internals
    # ------------------------------------------------------------------

    def _check(self, target, rules):
        for pattern in rules.get("deny", []):
            if fnmatch(target, pattern):
                return PermissionLevel.DENY
        for pattern in rules.get("allow", []):
            if fnmatch(target, pattern):
                return PermissionLevel.ALLOW
        return PermissionLevel(rules.get("default", "ask"))

    @staticmethod
    def _has_shell_operators(command):
        return any(op in command for op in ["&&", "||", ";", "$(", "`", "\n", "\r"])


# Keep PermissionChecker as an alias so existing imports don't break
# during the transition — remove after all references are updated.
class PermissionChecker(Safety):
    def __init__(self, config_path=None, profile="standard"):
        super().__init__(profile=profile)

    def check_file_read(self, file_path):
        return super().check_file_read(file_path)

    def check_file_write(self, file_path):
        return super().check_file_write(file_path)

    def check_bash_command(self, command):
        return super().check_bash(command)

    def prompt_user(self, operation, details):
        return super().prompt_permission(operation, details)


# Keep CriticalOperation as an alias too
class CriticalOperation(Safety):
    def __init__(self):
        super().__init__(profile="standard")

    def is_critical_bash(self, command):
        return super().is_critical_bash(command)

    def is_critical_file_write(self, path):
        return super().is_critical_write(path)

    def is_critical_read(self, path):
        return super().is_critical_read(path)

    def get_approval_message(self, operation, reason, details):
        return (
            f"\n⚠️  CRITICAL OPERATION REQUIRES APPROVAL\n\n"
            f"Operation: {operation}\nReason: {reason}\nDetails: {details}\n\n"
            "Approve? (y)es / (n)o / (a)lways approve this pattern\n> "
        )

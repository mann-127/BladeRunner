"""Safety and approval system for critical operations."""

import re
from typing import Tuple, Optional, Set


class CriticalOperation:
    """Detects and manages approval for dangerous operations."""

    def __init__(self):
        """Initialize critical operation patterns."""
        # Destructive bash patterns
        self.rm_patterns = [
            r"\brm\s+-",  # rm with options
            r"\brm\s+/",  # rm with path
            r">>\s*/dev/null",  # redirect to /dev/null
        ]

        self.dd_patterns = [
            r"\bdd\s+if=",  # disk dump write
            r"\bdd\s+of=",  # disk dump output
        ]

        self.dangerous_bash_cmds = {
            "mkfs": "Format filesystem",
            "fdisk": "Partition disk",
            "parted": "Partition disk",
            "dd": "Low-level disk write",
            ":`": "Execute shell",
        }

        # File operations
        self.critical_file_paths = {
            "/etc": "System configuration",
            "/sys": "System kernel interface",
            "/proc": "Process information",
            "~/.ssh": "SSH keys",
            "~/.aws": "AWS credentials",
            ".env": "Environment variables (may contain secrets)",
        }

        self.critical_extensions = {".key", ".pem", ".p12", ".pfx"}

        # Track approved operations
        self.approved_operations: Set[str] = set()
        self.denied_operations: Set[str] = set()

    def is_critical_bash(self, command: str) -> Tuple[bool, Optional[str]]:
        """Check if bash command is critical/destructive."""
        cmd_lower = command.lower()

        # Check for rm patterns
        for pattern in self.rm_patterns:
            if re.search(pattern, cmd_lower):
                return True, "Delete files with 'rm' command"

        # Check for dd patterns
        for pattern in self.dd_patterns:
            if re.search(pattern, cmd_lower):
                return True, "Disk write with 'dd' command"

        # Check dangerous commands
        for dangerous_cmd, description in self.dangerous_bash_cmds.items():
            if dangerous_cmd in cmd_lower:
                return True, description

        return False, None

    def is_critical_file_write(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if file write is to sensitive location."""
        path_lower = file_path.lower()

        # Check critical paths
        for critical_path, reason in self.critical_file_paths.items():
            if critical_path in path_lower:
                return True, f"Write to sensitive path: {reason}"

        # Check file extensions
        for ext in self.critical_extensions:
            if file_path.endswith(ext):
                return True, f"Write to {ext} file (possible secret)"

        return False, None

    def is_critical_read(self, file_path: str) -> Tuple[bool, Optional[str]]:
        """Check if file read is from sensitive location."""
        path_lower = file_path.lower()

        # Only flag SSH/AWS/env reads as critical
        sensitive_reads = {
            "~/.ssh": "SSH keys",
            "~/.aws": "AWS credentials",
            ".env": "Environment variables",
            "requirements.txt": "No - development file",
        }

        for sensitive_path, reason in sensitive_reads.items():
            if sensitive_path in path_lower:
                if "No -" not in reason:
                    return True, f"Read sensitive file: {reason}"

        return False, None

    def get_approval_message(self, operation: str, reason: str, details: str) -> str:
        """Generate approval prompt message."""
        return f"""
⚠️  CRITICAL OPERATION REQUIRES APPROVAL

Operation: {operation}
Reason: {reason}
Details: {details}

Approve? (y)es / (n)o / (a)lways approve this pattern
> """

    def prompt_approval(
        self,
        operation: str,
        reason: str,
        details: str,
    ) -> bool:
        """Prompt user for approval of critical operation."""
        # Check if already approved
        op_hash = self._hash_operation(operation, details)
        if op_hash in self.approved_operations:
            print(f"✓ {operation} (previously approved)", flush=True)
            return True

        if op_hash in self.denied_operations:
            print(f"✗ {operation} (previously denied)", flush=True)
            return False

        # Prompt user
        msg = self.get_approval_message(operation, reason, details)
        try:
            response = input(msg).strip().lower()

            if response == "y" or response == "yes":
                return True
            elif response == "a" or response == "always":
                self.approved_operations.add(op_hash)
                return True
            else:
                self.denied_operations.add(op_hash)
                return False

        except (KeyboardInterrupt, EOFError):
            print("\nOperation cancelled by user")
            return False

    def _hash_operation(self, operation: str, details: str) -> str:
        """Create a hash for operation tracking."""
        # Simple hash - could be improved with actual hash function
        return f"{operation}:{details}"[:100]

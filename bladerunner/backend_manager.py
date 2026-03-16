"""Intelligent backend selection and fallback management."""

from __future__ import annotations

import os
import time
from dataclasses import dataclass
from typing import Dict, List, Optional


@dataclass
class BackendStatus:
    """Track backend health and availability."""

    name: str
    available: bool = True
    last_failure: Optional[float] = None
    failure_count: int = 0
    cooldown_until: Optional[float] = None

    def is_in_cooldown(self) -> bool:
        """Check if backend is in cooldown period."""
        if self.cooldown_until is None:
            return False
        return time.time() < self.cooldown_until

    def record_failure(self, cooldown_seconds: int = 60):
        """Record a failure and set cooldown."""
        self.failure_count += 1
        self.last_failure = time.time()
        self.cooldown_until = time.time() + cooldown_seconds

    def record_success(self):
        """Record a successful request."""
        self.failure_count = 0
        self.last_failure = None
        self.cooldown_until = None
        self.available = True


class BackendManager:
    """Manages multiple backends with automatic fallback."""

    def __init__(self, config: dict, primary_backend: Optional[str] = None):
        """Initialize backend manager.

        Args:
            config: Configuration dictionary
            primary_backend: Preferred backend (defaults to config backend)
        """
        self.config = config
        self.primary_backend = primary_backend or config.get("backend", "openrouter")
        self.backends: Dict[str, BackendStatus] = {}
        self._initialize_backends()

    def _initialize_backends(self):
        """Initialize backend status tracking."""
        backends_config = self.config.get("backends", {})

        for backend_name, backend_config in backends_config.items():
            # Skip google_adk as it's handled separately
            if backend_name == "google_adk":
                continue

            # Check if API key is available
            env_var = backend_config.get("api_key_env", "")
            has_api_key = bool(os.getenv(env_var))

            self.backends[backend_name] = BackendStatus(
                name=backend_name,
                available=has_api_key,
            )

    def get_backend_priority(self) -> List[str]:
        """Get list of backends in priority order.

        Returns:
            List of backend names, primary first, then others
        """
        if self.primary_backend not in self.backends:
            return [name for name, status in self.backends.items() if status.available]

        priority = [self.primary_backend]

        # Add other available backends
        for backend_name in self.backends:
            if (
                backend_name != self.primary_backend
                and self.backends[backend_name].available
            ):
                priority.append(backend_name)

        return priority

    def get_next_backend(self, exclude: Optional[List[str]] = None) -> Optional[str]:
        """Get next available backend for retry.

        Args:
            exclude: List of backends to exclude

        Returns:
            Backend name or None if no backends available
        """
        exclude = exclude or []

        for backend_name in self.get_backend_priority():
            if backend_name in exclude:
                continue

            status = self.backends.get(backend_name)
            if status and status.available and not status.is_in_cooldown():
                return backend_name

        return None

    def record_request_failure(
        self, backend_name: str, error_code: Optional[int] = None
    ):
        """Record a failed request.

        Args:
            backend_name: Name of the backend
            error_code: HTTP error code if available
        """
        if backend_name not in self.backends:
            return

        # Set cooldown based on error type
        if error_code == 429:
            # Rate limit: longer cooldown
            cooldown = 120  # 2 minutes
        elif error_code == 402:
            # Payment/credits: very long cooldown
            cooldown = 300  # 5 minutes
        else:
            # Other errors: short cooldown
            cooldown = 60  # 1 minute

        self.backends[backend_name].record_failure(cooldown)

    def record_request_success(self, backend_name: str):
        """Record a successful request.

        Args:
            backend_name: Name of the backend
        """
        if backend_name in self.backends:
            self.backends[backend_name].record_success()

    def should_attempt_fallback(
        self, backend_name: str, error_code: Optional[int] = None
    ) -> bool:
        """Determine if we should try a fallback backend.

        Args:
            backend_name: Current backend that failed
            error_code: HTTP error code if available

        Returns:
            True if fallback should be attempted
        """
        # Always fallback on rate limits and payment errors
        if error_code in [429, 402]:
            return True

        # Fallback on repeated failures
        status = self.backends.get(backend_name)
        if status and status.failure_count >= 2:
            return True

        return False

    def get_backend_info(self) -> Dict[str, dict]:
        """Get information about all backends.

        Returns:
            Dictionary with backend status information
        """
        info = {}
        for name, status in self.backends.items():
            info[name] = {
                "available": status.available,
                "in_cooldown": status.is_in_cooldown(),
                "failure_count": status.failure_count,
                "is_primary": name == self.primary_backend,
            }
        return info

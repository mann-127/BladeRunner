"""Backward-compat shim — PermissionChecker now lives in safety.py."""

from .safety import PermissionChecker, PermissionLevel

__all__ = ["PermissionChecker", "PermissionLevel"]

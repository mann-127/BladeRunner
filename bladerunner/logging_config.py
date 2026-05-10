"""Logging utilities for BladeRunner services."""

import logging


def _resolve_level(level):
    """Map config values to stdlib logging levels."""
    if isinstance(level, int):
        return level
    if isinstance(level, str):
        return getattr(logging, level.upper(), logging.INFO)
    return logging.INFO


def configure_logging(config, service_name="bladerunner"):
    """Configure root logging once per process from config keys."""
    level = _resolve_level(config.get("logging.level", "INFO"))
    fmt = config.get(
        "logging.format",
        "%(asctime)s %(levelname)s [%(name)s] %(message)s",
    )
    datefmt = config.get("logging.date_format", "%Y-%m-%dT%H:%M:%S%z")

    logging.basicConfig(level=level, format=fmt, datefmt=datefmt, force=True)
    logging.getLogger(service_name).debug("Logging initialized at level=%s", level)

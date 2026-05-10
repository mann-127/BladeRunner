"""Tests for CLI module."""

import contextlib
import sys

import pytest

from bladerunner.cli import main
from bladerunner.config import Config


def _disable_sessions(monkeypatch):
    original_defaults = Config._defaults

    def _patched_defaults(self):
        cfg = original_defaults(self)
        cfg["sessions"]["enabled"] = False
        return cfg

    monkeypatch.setattr(Config, "_defaults", _patched_defaults)


def test_version_outputs_version_and_exits(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["bladerunner", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    assert "BladeRunner" in capsys.readouterr().out


def test_verbose_version_outputs_codename(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["bladerunner", "--verbose", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert "BladeRunner" in out
    assert 'KD6-3.7 "K"' in out


def test_help_shows_permissions_hides_easter_eggs(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["bladerunner", "--help"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    out = capsys.readouterr().out
    assert "--permissions" in out
    assert "--officer-k" not in out
    assert "--constant-k" not in out
    assert "--agent-k" not in out


def test_cli_image_flag_augments_prompt(monkeypatch, capsys):
    _disable_sessions(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "bladerunner",
            "-p",
            "Analyze this",
            "--image",
            "a.png",
            "--permissions",
            "none",
        ],
    )

    captured_prompt = {}

    def _fake_execute(self, prompt, use_streaming=False):
        captured_prompt["value"] = prompt
        return "ok"

    monkeypatch.setattr("bladerunner.agent.Agent.execute", _fake_execute)

    main()
    assert "ok" in capsys.readouterr().out
    assert "Attached image paths" in captured_prompt["value"]
    assert "- a.png" in captured_prompt["value"]


def test_cli_debug_flag_configures_logging(monkeypatch, capsys):
    _disable_sessions(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setattr(
        sys,
        "argv",
        ["bladerunner", "-p", "hello", "--debug", "--permissions", "none"],
    )
    monkeypatch.setattr(
        "bladerunner.agent.Agent.execute",
        lambda *_args, **_kwargs: "ok",
    )

    logging_calls = []

    def _fake_configure_logging(config, service_name="bladerunner"):
        logging_calls.append((config.get("debug"), service_name))

    monkeypatch.setattr("bladerunner.cli.configure_logging", _fake_configure_logging)

    main()
    assert "ok" in capsys.readouterr().out
    assert logging_calls == [(True, "bladerunner.cli")]


def test_cli_officer_k_sets_strict_permissions(monkeypatch, capsys):
    _disable_sessions(monkeypatch)
    monkeypatch.setenv("OPENROUTER_API_KEY", "fake-key")
    monkeypatch.setattr(
        sys,
        "argv",
        ["bladerunner", "hello", "--officer-k"],
    )

    captured_profile = {}

    def _fake_agent(config, model, use_permissions, permission_profile, session_id):
        captured_profile["value"] = permission_profile
        from bladerunner.agent import Agent

        return Agent.__new__(Agent)

    monkeypatch.setattr("bladerunner.cli.Agent", _fake_agent)
    monkeypatch.setattr(
        "bladerunner.agent.Agent.execute",
        lambda *_args, **_kwargs: "ok",
    )

    # Just check the profile is set — agent init may fail, so we only verify the arg
    with contextlib.suppress(Exception):
        main()

    assert captured_profile.get("value") == "strict"


def test_cli_requires_prompt(monkeypatch, capsys):
    monkeypatch.setattr(sys, "argv", ["bladerunner"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code != 0

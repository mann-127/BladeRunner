import sys

import pytest

from bladerunner.cli import main


def test_version_outputs_codename_and_exits(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["bladerunner", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "BladeRunner" in captured.out
    assert 'KD6-3.7 "K"' in captured.out


def test_verbose_version_outputs_aliases(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["bladerunner", "--verbose", "--version"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "Designation:" in captured.out
    assert "Also known as:" in captured.out
    assert "Officer K" in captured.out


def test_help_shows_profile_but_hides_easter_egg_flags(monkeypatch, capsys) -> None:
    monkeypatch.setattr(sys, "argv", ["bladerunner", "--help"])

    with pytest.raises(SystemExit) as exit_info:
        main()

    assert exit_info.value.code == 0
    captured = capsys.readouterr()
    assert "--profile" in captured.out
    assert "--officer-k" not in captured.out
    assert "--constant-k" not in captured.out
    assert "--agent-k" not in captured.out

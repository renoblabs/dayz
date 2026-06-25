"""Tests for CLI — command wiring and exit codes."""
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from modctl.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "modctl" in result.stdout


def test_help_shows_all_top_level_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["version", "doctor", "build", "deploy", "ship"]:
        assert cmd in result.stdout


def test_build_missing_mod_returns_config_error_exit_code(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_SECRET", "x")
    result = runner.invoke(app, [
        "--config", str(FIXTURES / "mods.example.yaml"),
        "build", "nonexistent-mod",
    ])
    assert result.exit_code == 10


def test_build_json_mode_emits_valid_json(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "x")
    result = runner.invoke(app, [
        "--config", str(FIXTURES / "mods.example.yaml"),
        "--json",
        "build", "nonexistent-mod",
    ])
    parsed = json.loads(result.stdout)
    assert parsed["command"] == "build"
    assert parsed["status"] == "error"

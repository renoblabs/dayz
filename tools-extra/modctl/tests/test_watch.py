"""Tests for watch orchestration."""
import threading
import time
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modctl.config import load_mods_yaml
from modctl.orchestration.watch import WatchOrchestrator
from modctl.output import CommandResult, StepResult


def _make_config(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "x")
    mod_source = tmp_path / "fake-mod"
    (mod_source / "scripts" / "3_game").mkdir(parents=True)
    (mod_source / "scripts" / "3_game" / "FakeConfig.c").write_text(
        'class FakeConfig { static string SERVER_ID = "s1"; };\n'
    )

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{(tmp_path / 'tools').as_posix()}"
  dayz_server_path: "{(tmp_path / 'server').as_posix()}"
  signing_keys_dir: "{(tmp_path / 'keys').as_posix()}"
  output_dir: "{(tmp_path / 'out').as_posix()}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods:
  - name: fakemod
    source: "{mod_source.as_posix()}"
    pbo_name: "FakeMod"
    mod_folder: "@FakeMod"
    depends_on: []
    watch: ["*.c"]
""")
    return load_mods_yaml(mods_yaml)


def test_watch_fires_ship_on_file_change(tmp_path, monkeypatch):
    config = _make_config(tmp_path, monkeypatch)

    ship_calls = []
    def fake_ship(mod_name):
        result = CommandResult(command="ship", mod=mod_name, status="ok")
        result.steps.append(StepResult(name="build+deploy", status="ok", duration_s=0.1))
        ship_calls.append(mod_name)
        return result

    orch = WatchOrchestrator(config, ship_callable=fake_ship, debounce_ms=100)
    orch.start("fakemod")
    try:
        time.sleep(0.3)  # watcher spin-up
        # Modify the watched file
        target = tmp_path / "fake-mod" / "scripts" / "3_game" / "FakeConfig.c"
        target.write_text('// touched')
        # Give debounce + callback time to fire
        time.sleep(0.6)
        assert "fakemod" in ship_calls
    finally:
        orch.stop()


def test_watch_raises_on_unknown_mod(tmp_path, monkeypatch):
    config = _make_config(tmp_path, monkeypatch)
    from modctl.errors import ModctlError

    orch = WatchOrchestrator(config, ship_callable=lambda n: None)
    with pytest.raises(ModctlError):
        orch.start("nonexistent")

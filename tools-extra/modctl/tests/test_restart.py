"""Tests for restart orchestration."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modctl.config import load_mods_yaml
from modctl.orchestration.restart import RestartOrchestrator


def _make_config(tmp_path):
    server_path = tmp_path / "dayz-server"
    (server_path / "profiles").mkdir(parents=True)
    (server_path / "DayZServer_x64.exe").write_text("fake")

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{(tmp_path / 'tools').as_posix()}"
  dayz_server_path: "{server_path.as_posix()}"
  signing_keys_dir: "{(tmp_path / 'keys').as_posix()}"
  output_dir: "{(tmp_path / 'out').as_posix()}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods: []
dependencies:
  cf:
    name: "CF"
    mod_folder: "@CommunityFramework"
    required: true
""")
    return load_mods_yaml(mods_yaml)


def test_restart_when_no_prior_pid_starts_fresh(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    with patch("modctl.orchestration.serve.start_server") as MS:
        fake_proc = MagicMock()
        fake_proc.pid = 777
        MS.return_value = fake_proc

        orch = RestartOrchestrator(config)
        result = orch.restart()

    assert result.status == "ok"
    # When there's no prior PID the "stop" step is a no-op; start still runs.
    step_names = [s.name for s in result.steps]
    assert "stop_prior" in step_names
    assert "start_server" in step_names


def test_restart_stops_prior_pid(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    monkeypatch.chdir(tmp_path)
    # Seed state.json with a fake prior PID
    state_dir = tmp_path / ".modctl"
    state_dir.mkdir()
    (state_dir / "state.json").write_text('{"server_pid": 12345}')

    with patch("modctl.orchestration.restart.psutil_terminate_pid") as MT:
        MT.return_value = True
        with patch("modctl.orchestration.serve.start_server") as MS:
            fake_proc = MagicMock()
            fake_proc.pid = 999
            MS.return_value = fake_proc

            orch = RestartOrchestrator(config)
            result = orch.restart()

    assert result.status == "ok"
    MT.assert_called_once_with(12345, timeout_s=10.0)

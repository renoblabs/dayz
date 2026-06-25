"""Tests for serve orchestration."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modctl.config import load_mods_yaml
from modctl.orchestration.serve import ServeOrchestrator


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
  dayz_server_port: 2302
backends: {{}}
mods:
  - name: bosssignal
    source: "bosssignal-mod"
    pbo_name: "BossSignal"
    mod_folder: "@BossSignal"
    depends_on: [cf]
dependencies:
  cf:
    name: "CF"
    mod_folder: "@CommunityFramework"
    required: true
""")
    return load_mods_yaml(mods_yaml)


def test_serve_builds_correct_mod_list(tmp_path):
    config = _make_config(tmp_path)

    with patch("modctl.orchestration.serve.start_server") as MS:
        fake_proc = MagicMock()
        fake_proc.pid = 4242
        MS.return_value = fake_proc

        orch = ServeOrchestrator(config)
        result = orch.start()

    assert result.status == "ok"
    _, kwargs = MS.call_args
    mods = kwargs["mods"]
    # CF always first, then deployed mods
    assert mods[0] == "@CommunityFramework"
    assert "@BossSignal" in mods


def test_serve_start_writes_state(tmp_path, monkeypatch):
    config = _make_config(tmp_path)
    monkeypatch.chdir(tmp_path)

    with patch("modctl.orchestration.serve.start_server") as MS:
        fake_proc = MagicMock()
        fake_proc.pid = 9999
        MS.return_value = fake_proc

        orch = ServeOrchestrator(config)
        result = orch.start()

    assert result.status == "ok"
    assert result.result["pid"] == 9999
    state_file = tmp_path / ".modctl" / "state.json"
    assert state_file.exists()


def test_serve_start_fails_cleanly_when_server_exe_missing(tmp_path):
    # Rebuild config pointing at a directory without DayZServer_x64.exe
    server_path = tmp_path / "empty-server"
    server_path.mkdir()

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
""")
    config = load_mods_yaml(mods_yaml)

    orch = ServeOrchestrator(config)
    result = orch.start()

    assert result.status == "error"
    assert result.failing_step == "verify_server_exe"

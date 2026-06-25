"""Tests for the doctor orchestration."""
from pathlib import Path
from unittest.mock import patch

import pytest

from modctl.config import load_mods_yaml
from modctl.orchestration.doctor import DoctorReport, run_doctor


def test_doctor_all_green(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "value")
    tools_path = tmp_path / "dayz-tools"
    (tools_path / "Bin" / "AddonBuilder").mkdir(parents=True)
    (tools_path / "Bin" / "AddonBuilder" / "AddonBuilder.exe").write_text("fake")
    (tools_path / "Bin" / "DsUtils").mkdir(parents=True)
    (tools_path / "Bin" / "DsUtils" / "DSCreateKey.exe").write_text("fake")

    server_path = tmp_path / "dayz-server"
    server_path.mkdir()

    keys_path = tmp_path / "keys"
    keys_path.mkdir()
    (keys_path / "BossSignal.biprivatekey").write_text("fake")
    (keys_path / "BossSignal.bikey").write_text("fake")

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tools_path.as_posix()}"
  dayz_server_path: "{server_path.as_posix()}"
  signing_keys_dir: "{keys_path.as_posix()}"
  output_dir: "{(tmp_path / 'output').as_posix()}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods:
  - name: bosssignal
    source: "bosssignal-mod"
    pbo_name: "BossSignal"
    mod_folder: "@BossSignal"
    depends_on: []
""")

    config = load_mods_yaml(mods_yaml)
    report = run_doctor(config)

    assert isinstance(report, DoctorReport)
    assert report.overall_ok is True
    assert all(c.ok for c in report.checks)


def test_doctor_flags_missing_addon_builder(tmp_path):
    tools_path = tmp_path / "dayz-tools"
    tools_path.mkdir()

    server_path = tmp_path / "dayz-server"
    server_path.mkdir()

    keys_path = tmp_path / "keys"
    keys_path.mkdir()

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tools_path.as_posix()}"
  dayz_server_path: "{server_path.as_posix()}"
  signing_keys_dir: "{keys_path.as_posix()}"
  output_dir: "{(tmp_path / 'output').as_posix()}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods: []
""")

    config = load_mods_yaml(mods_yaml)
    report = run_doctor(config)

    assert report.overall_ok is False
    failed = [c for c in report.checks if not c.ok]
    assert any("AddonBuilder" in c.name for c in failed)

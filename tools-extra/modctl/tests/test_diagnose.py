"""Tests for diagnose orchestration — RPT file → list of DiagnosedError."""
from pathlib import Path

import pytest

from modctl.config import load_mods_yaml
from modctl.orchestration.diagnose import DiagnoseOrchestrator
from modctl.errors import ErrorCategory


def _make_config(tmp_path):
    server_path = tmp_path / "dayz-server"
    profile_dir = server_path / "profiles"
    profile_dir.mkdir(parents=True)

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
    return load_mods_yaml(mods_yaml), profile_dir


def test_diagnose_finds_multiple_errors_in_rpt(tmp_path):
    config, profile_dir = _make_config(tmp_path)
    rpt = profile_dir / "DayZServer_x64_2026-04-23.RPT"
    rpt.write_text(
        "[INFO] Mission initialized.\n"
        "[ERROR] Script compilation failed: bosssignal-mod/scripts/5_mission/Emitter.c @ line 78\n"
        "[ERROR] NULL pointer to instance at BossSignalEmitter::OnBossKilled — killer.GetIdentity()\n"
        "[WARN]  [BossSignal] HTTP request failed: Connection refused 127.0.0.1:8080\n"
        "[FATAL] Mission shutdown requested\n"
    )

    orch = DiagnoseOrchestrator(config)
    result = orch.diagnose()

    assert result.status == "ok"
    diagnoses = result.result["diagnoses"]
    # Should catch: compile_failed, null_identity, http_refused, mission_shutdown
    assert len(diagnoses) >= 4
    rule_ids = [d["rule_id"] for d in diagnoses]
    assert "rpt.script_compile_failed" in rule_ids
    assert "rpt.null_identity_dereference" in rule_ids
    assert "rpt.http_connection_refused" in rule_ids
    assert "rpt.mission_shutdown" in rule_ids


def test_diagnose_returns_error_when_no_rpt(tmp_path):
    config, _ = _make_config(tmp_path)

    orch = DiagnoseOrchestrator(config)
    result = orch.diagnose()

    assert result.status == "error"
    assert result.failing_step == "find_rpt"


def test_diagnose_custom_rpt_path(tmp_path):
    config, _ = _make_config(tmp_path)
    custom_rpt = tmp_path / "custom.RPT"
    custom_rpt.write_text(
        "[ERROR] NULL pointer to instance (GetIdentity())\n"
    )

    orch = DiagnoseOrchestrator(config)
    result = orch.diagnose(rpt_path=custom_rpt)

    assert result.status == "ok"
    assert len(result.result["diagnoses"]) == 1
    assert result.result["diagnoses"][0]["rule_id"] == "rpt.null_identity_dereference"


def test_diagnose_records_line_numbers(tmp_path):
    config, profile_dir = _make_config(tmp_path)
    rpt = profile_dir / "test.RPT"
    rpt.write_text(
        "line one, no match\n"
        "line two, no match\n"
        "[ERROR] NULL pointer to instance (GetIdentity())\n"
    )

    orch = DiagnoseOrchestrator(config)
    result = orch.diagnose()
    assert result.result["diagnoses"][0]["line_num"] == 3


def test_diagnose_clean_rpt_returns_ok_with_empty_list(tmp_path):
    config, profile_dir = _make_config(tmp_path)
    rpt = profile_dir / "clean.RPT"
    rpt.write_text(
        "[INFO] Mission initialized.\n"
        "[BossSignal] Config loaded.\n"
        "[BossSignal] Emitter ready.\n"
    )

    orch = DiagnoseOrchestrator(config)
    result = orch.diagnose()

    assert result.status == "ok"
    assert result.result["diagnoses"] == []

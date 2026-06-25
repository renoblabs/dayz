"""Tests for fix orchestration — apply diff / action with verify loop."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modctl.config import load_mods_yaml
from modctl.diagnosis import DiagnosedError
from modctl.errors import ErrorCategory
from modctl.orchestration.fix import FixOrchestrator
from modctl.output import CommandResult, StepResult


def _make_config(tmp_path):
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
mods: []
""")
    return load_mods_yaml(mods_yaml)


def _make_diag(fix_action=None, fix_template=None) -> DiagnosedError:
    return DiagnosedError(
        rule_id="rpt.test_rule",
        category=ErrorCategory.BUILD_ERROR,
        severity="critical",
        confidence="high",
        raw_line="[ERROR] test",
        line_num=1,
        diagnosis="test diagnosis",
        fix_template=fix_template,
        fix_action=fix_action,
        can_auto_fix=False,
    )


def test_fix_runs_shell_action_when_approved(tmp_path):
    config = _make_config(tmp_path)
    diag = _make_diag(fix_action="echo hello")

    with patch("modctl.orchestration.fix.run_command") as mock_run:
        from modctl.actions.runner import CommandOutput
        mock_run.return_value = CommandOutput(
            returncode=0, stdout="hello", stderr="", duration_s=0.01, command=["echo", "hello"]
        )
        orch = FixOrchestrator(config, approve_callback=lambda d: True)
        result = orch.fix(diag)

    assert result.status == "ok"
    step_names = [s.name for s in result.steps]
    assert "run_fix_action" in step_names


def test_fix_skips_when_not_approved(tmp_path):
    config = _make_config(tmp_path)
    diag = _make_diag(fix_action="echo hello")

    orch = FixOrchestrator(config, approve_callback=lambda d: False)
    result = orch.fix(diag)

    assert result.status == "ok"
    step_names = [s.name for s in result.steps]
    assert "skipped" in step_names
    assert "run_fix_action" not in step_names


def test_fix_reports_template_only_fixes_as_manual(tmp_path):
    config = _make_config(tmp_path)
    diag = _make_diag(fix_template="Add ; at line 51")

    # Template-only fixes are instructional — no auto-apply.
    orch = FixOrchestrator(config, approve_callback=lambda d: True)
    result = orch.fix(diag)

    assert result.status == "ok"
    step_names = [s.name for s in result.steps]
    # Should flag as manual_fix_required, not attempt to apply
    assert "manual_fix_required" in step_names


def test_fix_fails_when_shell_action_exits_nonzero(tmp_path):
    config = _make_config(tmp_path)
    # Use an exit-1 shell command that we control via the runner mock
    diag = _make_diag(fix_action="false-command-that-will-fail")

    with patch("modctl.orchestration.fix.run_command") as MR:
        from modctl.actions.runner import CommandOutput
        MR.return_value = CommandOutput(
            returncode=1, stdout="", stderr="bad thing",
            duration_s=0.01, command=["sh"],
        )

        orch = FixOrchestrator(config, approve_callback=lambda d: True)
        result = orch.fix(diag)

    assert result.status == "error"
    assert result.failing_step == "run_fix_action"


def test_fix_returns_no_fix_available(tmp_path):
    config = _make_config(tmp_path)
    # Diagnosis with no fix — nothing to do
    diag = _make_diag()  # no fix_action, no fix_template

    orch = FixOrchestrator(config, approve_callback=lambda d: True)
    result = orch.fix(diag)

    assert result.status == "ok"
    step_names = [s.name for s in result.steps]
    assert "no_fix_available" in step_names

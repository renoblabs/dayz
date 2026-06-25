"""Diagnose orchestration — parse an RPT log file, apply rule matching,
return a structured list of DiagnosedError as a CommandResult.
"""
from __future__ import annotations

import time
from dataclasses import asdict
from pathlib import Path
from typing import List, Optional

from modctl.actions.dayz_server import find_rpt_log
from modctl.config import ModsConfig
from modctl.diagnosis import DiagnosedError, diagnose_line, load_rules
from modctl.errors import ErrorCategory
from modctl.output import CommandResult, StepResult


class DiagnoseOrchestrator:
    def __init__(self, config: ModsConfig, rules_path: Optional[Path] = None) -> None:
        self.config = config
        self._rules = load_rules(rules_path)

    def diagnose(self, rpt_path: Optional[Path] = None) -> CommandResult:
        started = time.monotonic()
        result = CommandResult(command="diagnose", mod=None, status="ok")

        # Step: locate RPT
        step_start = time.monotonic()
        if rpt_path is None:
            defaults = self.config.defaults
            server_root = Path(defaults.dayz_server_path)
            profile_dir = server_root / defaults.dayz_server_profile_dir
            rpt_path = find_rpt_log(profile_dir)

        if rpt_path is None or not rpt_path.exists():
            result.steps.append(StepResult(
                name="find_rpt", status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "find_rpt"
            result.errors.append({
                "category": ErrorCategory.IO_ERROR.value,
                "message": "No RPT log file found to diagnose",
                "suggested_fix": "Start the DayZ Server (modctl serve) first, or pass --rpt <path>.",
            })
            result.duration_s = time.monotonic() - started
            return result

        result.steps.append(StepResult(
            name="find_rpt", status="ok",
            duration_s=time.monotonic() - step_start,
            details=f"RPT: {rpt_path}",
        ))

        # Step: parse + match
        step_start = time.monotonic()
        diagnoses: List[DiagnosedError] = []
        with open(rpt_path, "r", encoding="utf-8", errors="replace") as f:
            for i, line in enumerate(f, start=1):
                diag = diagnose_line(line, self._rules, line_num=i)
                if diag is not None:
                    diagnoses.append(diag)

        result.steps.append(StepResult(
            name="match_rules", status="ok",
            duration_s=time.monotonic() - step_start,
            details=f"Matched {len(diagnoses)} error(s)",
        ))

        # Serialize for CommandResult.result (needs to be JSON-safe dicts)
        result.result["rpt_path"] = str(rpt_path)
        result.result["diagnoses"] = [_diag_to_dict(d) for d in diagnoses]
        result.duration_s = time.monotonic() - started
        return result


def _diag_to_dict(d: DiagnosedError) -> dict:
    return {
        "rule_id": d.rule_id,
        "category": d.category.value,
        "severity": d.severity,
        "confidence": d.confidence,
        "line_num": d.line_num,
        "raw_line": d.raw_line,
        "diagnosis": d.diagnosis,
        "fix_template": d.fix_template,
        "fix_action": d.fix_action,
        "can_auto_fix": d.can_auto_fix,
    }

"""Fix orchestration — apply a diagnosis's suggested fix with approval.

Supported fix types:
  - shell action (e.g. `modctl backend up`) — runs a shell command
  - template only (e.g. "Add ; at line 51") — flagged as manual_fix_required,
    not auto-applied (future: LLM-generated diff goes here)

Every fix requires user approval via the injected approve_callback. In CLI mode
that's an interactive prompt; tests inject a lambda.
"""
from __future__ import annotations

import shlex
import time
from typing import Callable, Optional

from modctl.actions.runner import run_command
from modctl.config import ModsConfig
from modctl.diagnosis import DiagnosedError
from modctl.errors import ErrorCategory
from modctl.output import CommandResult, StepResult


ApproveCallback = Callable[[DiagnosedError], bool]


class FixOrchestrator:
    def __init__(self, config: ModsConfig, approve_callback: ApproveCallback) -> None:
        self.config = config
        self._approve = approve_callback

    def fix(self, diag: DiagnosedError) -> CommandResult:
        started = time.monotonic()
        result = CommandResult(command="fix", mod=None, status="ok")
        result.result["rule_id"] = diag.rule_id
        result.result["diagnosis"] = diag.diagnosis

        # Case 1: nothing actionable
        if diag.fix_action is None and diag.fix_template is None:
            result.steps.append(StepResult(
                name="no_fix_available", status="skipped",
                details=f"Rule {diag.rule_id} has no auto-fix recipe.",
            ))
            result.duration_s = time.monotonic() - started
            return result

        # Case 2: template-only — manual, we can't auto-apply text instructions
        if diag.fix_action is None and diag.fix_template is not None:
            result.steps.append(StepResult(
                name="manual_fix_required", status="skipped",
                details=f"Fix requires manual edit: {diag.fix_template}",
            ))
            result.duration_s = time.monotonic() - started
            return result

        # Case 3: shell action — prompt + run
        if not self._approve(diag):
            result.steps.append(StepResult(
                name="skipped", status="skipped",
                details="User declined the fix.",
            ))
            result.duration_s = time.monotonic() - started
            return result

        # Run the shell action
        step_start = time.monotonic()
        try:
            out = run_command(shlex.split(diag.fix_action), timeout_s=60.0)
            if out.returncode != 0:
                result.steps.append(StepResult(
                    name="run_fix_action", status="error",
                    duration_s=time.monotonic() - step_start,
                    details=(out.stderr or out.stdout or "").strip()[:200],
                ))
                result.status = "error"
                result.failing_step = "run_fix_action"
                result.errors.append({
                    "category": ErrorCategory.UNKNOWN.value,
                    "message": f"Fix action failed: {diag.fix_action}",
                    "details": (out.stderr or out.stdout or "").strip()[:500],
                    "suggested_fix": "Review the error above and run the command manually to debug.",
                })
                result.duration_s = time.monotonic() - started
                return result

            result.steps.append(StepResult(
                name="run_fix_action", status="ok",
                duration_s=time.monotonic() - step_start,
                details=f"Ran: {diag.fix_action}",
            ))
        except Exception as e:
            result.steps.append(StepResult(
                name="run_fix_action", status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "run_fix_action"
            result.errors.append({
                "category": ErrorCategory.UNKNOWN.value,
                "message": str(e),
            })
            result.duration_s = time.monotonic() - started
            return result

        result.duration_s = time.monotonic() - started
        return result

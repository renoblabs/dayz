"""Restart orchestration — graceful stop of a running DayZ Server (via
previously-saved PID in state.json) + start fresh via ServeOrchestrator.

Uses os.kill to terminate; falls back to no-op if the PID is gone.
We deliberately avoid adding psutil as a dep — Python stdlib handles
the narrow case we need (signal a pid, wait briefly, proceed).
"""
from __future__ import annotations

import json
import os
import signal
import time
from pathlib import Path

from modctl.config import ModsConfig
from modctl.orchestration.serve import ServeOrchestrator, STATE_FILE
from modctl.output import CommandResult, StepResult


def psutil_terminate_pid(pid: int, timeout_s: float = 10.0) -> bool:
    """Terminate a pid gracefully, escalating to kill on timeout.

    Returns True if the pid was signalled, False if the pid was already gone.
    Name keeps `psutil_` prefix for legibility + easy mocking — implementation
    is stdlib-only to avoid a new dep.
    """
    try:
        # On Windows, signal.CTRL_BREAK_EVENT + SIGTERM semantics differ;
        # fall back to terminate via taskkill-equivalent os.kill with SIGTERM.
        os.kill(pid, signal.SIGTERM)
    except (ProcessLookupError, OSError):
        return False

    deadline = time.monotonic() + timeout_s
    while time.monotonic() < deadline:
        try:
            os.kill(pid, 0)  # signal 0 = check existence
            time.sleep(0.25)
        except (ProcessLookupError, OSError):
            return True

    # Still alive — escalate
    try:
        os.kill(pid, signal.SIGKILL)
    except (ProcessLookupError, OSError, AttributeError):
        # SIGKILL may not exist on Windows; fall back to SIGTERM again
        try:
            os.kill(pid, signal.SIGTERM)
        except Exception:
            pass
    return True


class RestartOrchestrator:
    def __init__(self, config: ModsConfig) -> None:
        self.config = config

    def _read_prior_pid(self) -> int | None:
        if not STATE_FILE.exists():
            return None
        try:
            data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
            return data.get("server_pid")
        except Exception:
            return None

    def restart(self) -> CommandResult:
        started = time.monotonic()
        result = CommandResult(command="restart", mod=None, status="ok")

        # Step: stop prior
        step_start = time.monotonic()
        prior_pid = self._read_prior_pid()
        if prior_pid is not None:
            psutil_terminate_pid(prior_pid, timeout_s=10.0)
        result.steps.append(StepResult(
            name="stop_prior", status="ok",
            duration_s=time.monotonic() - step_start,
            details=f"Prior PID: {prior_pid}" if prior_pid else "No prior PID in state",
        ))

        # Step: start fresh via ServeOrchestrator
        start_result = ServeOrchestrator(self.config).start()
        result.steps.extend(start_result.steps)
        if start_result.status == "error":
            result.status = "error"
            result.failing_step = start_result.failing_step
            result.errors.extend(start_result.errors)
            result.result.update(start_result.result)
            result.duration_s = time.monotonic() - started
            return result
        result.result.update(start_result.result)

        result.duration_s = time.monotonic() - started
        return result

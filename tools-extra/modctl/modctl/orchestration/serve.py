"""Serve orchestration — boot a local DayZ Server with deployed mods.

`modctl serve --detached` forks a background process and writes its PID
to `.modctl/state.json` so `modctl restart` and `modctl tail` can find it.
Foreground mode streams stdout + RPT to the terminal (handled at CLI layer).
"""
from __future__ import annotations

import json
import time
from pathlib import Path
from typing import List

from modctl.actions.dayz_server import start_server
from modctl.actions.filesystem import verify_path_exists
from modctl.config import ModsConfig
from modctl.errors import ErrorCategory, ModctlError
from modctl.output import CommandResult, StepResult


STATE_DIR = Path(".modctl")
STATE_FILE = STATE_DIR / "state.json"


def _load_state() -> dict:
    if not STATE_FILE.exists():
        return {}
    try:
        return json.loads(STATE_FILE.read_text(encoding="utf-8"))
    except Exception:
        return {}


def _save_state(state: dict) -> None:
    STATE_DIR.mkdir(parents=True, exist_ok=True)
    STATE_FILE.write_text(json.dumps(state, indent=2), encoding="utf-8")


class ServeOrchestrator:
    def __init__(self, config: ModsConfig) -> None:
        self.config = config

    def _resolve_mod_list(self) -> List[str]:
        """Required deps first (CF), then all declared mods in source order."""
        mods: List[str] = []
        # Required external deps first
        for dep in self.config.dependencies.values():
            if dep.required:
                mods.append(dep.mod_folder)
        # Then project mods
        for m in self.config.mods:
            if m.mod_folder not in mods:
                mods.append(m.mod_folder)
        return mods

    def start(self) -> CommandResult:
        started = time.monotonic()
        result = CommandResult(command="serve", mod=None, status="ok")
        defaults = self.config.defaults
        server_root = Path(defaults.dayz_server_path)
        server_exe = server_root / defaults.dayz_server_exe

        # Verify server exe
        step_start = time.monotonic()
        try:
            verify_path_exists(server_exe, f"DayZ Server executable ({defaults.dayz_server_exe})")
            result.steps.append(StepResult(
                name="verify_server_exe", status="ok",
                duration_s=time.monotonic() - step_start,
            ))
        except ModctlError as e:
            result.steps.append(StepResult(
                name="verify_server_exe", status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "verify_server_exe"
            result.errors.append({
                "category": e.category.value,
                "message": e.message,
                "details": e.details,
                "suggested_fix": e.suggested_fix,
            })
            result.duration_s = time.monotonic() - started
            return result

        # Build mod list
        mods = self._resolve_mod_list()

        # Launch
        step_start = time.monotonic()
        try:
            proc = start_server(
                server_exe=server_exe,
                mods=mods,
                config_file=defaults.dayz_server_config,
                port=defaults.dayz_server_port,
                profile_dir=defaults.dayz_server_profile_dir,
                extra_params=defaults.dayz_server_startup_params or None,
                cwd=server_root,
            )
            # Persist PID so restart/tail can find it
            state = _load_state()
            state["server_pid"] = proc.pid
            state["server_started_at"] = time.time()
            _save_state(state)

            result.steps.append(StepResult(
                name="start_server", status="ok",
                duration_s=time.monotonic() - step_start,
            ))
            result.result["pid"] = proc.pid
            result.result["mods"] = mods
            result.result["port"] = defaults.dayz_server_port
        except Exception as e:
            result.steps.append(StepResult(
                name="start_server", status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "start_server"
            result.errors.append({
                "category": ErrorCategory.SERVER_ERROR.value,
                "message": str(e),
            })

        result.duration_s = time.monotonic() - started
        return result

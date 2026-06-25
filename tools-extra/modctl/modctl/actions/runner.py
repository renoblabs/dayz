"""Subprocess runner — unified interface for external tool invocation.

All external process calls go through this. Enforces timeouts, captures
stdout+stderr, measures duration. Never uses shell=True.
"""
from __future__ import annotations

import subprocess
import time
from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from modctl.errors import ErrorCategory, ModctlError


@dataclass
class CommandOutput:
    returncode: int
    stdout: str
    stderr: str
    duration_s: float
    command: List[str]


def run_command(
    command: List[str],
    timeout_s: float = 120.0,
    cwd: Optional[Path] = None,
    env: Optional[dict] = None,
) -> CommandOutput:
    """Run an external command. Returns CommandOutput or raises ModctlError on timeout.

    Does NOT raise on non-zero exit — caller inspects returncode + stderr.
    """
    started = time.monotonic()
    try:
        proc = subprocess.run(
            command,
            capture_output=True,
            text=True,
            timeout=timeout_s,
            cwd=cwd,
            env=env,
        )
    except subprocess.TimeoutExpired:
        duration = time.monotonic() - started
        raise ModctlError(
            ErrorCategory.IO_ERROR,
            f"Command timed out after {timeout_s:.1f}s",
            details=f"{' '.join(command)}  (ran for {duration:.1f}s)",
            suggested_fix=f"Increase --timeout or check why the command hangs",
        )

    return CommandOutput(
        returncode=proc.returncode,
        stdout=proc.stdout or "",
        stderr=proc.stderr or "",
        duration_s=time.monotonic() - started,
        command=list(command),
    )

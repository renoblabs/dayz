"""Tail orchestration — stream DayZ Server RPT logs with colored prefixes.

Classifies each line into one of: error, warn, mod (BossSignal/TrophyHunter/etc.),
info. Applies Rich color tags. When stdout isn't a TTY or use_color=False,
emits plain text (safe for piping to json, grep, etc.).
"""
from __future__ import annotations

import re
import sys
import time
from pathlib import Path
from typing import Iterator, Literal, Optional

from rich.console import Console
from rich.text import Text

from modctl.actions.dayz_server import find_rpt_log
from modctl.config import ModsConfig
from modctl.errors import ErrorCategory, ModctlError
from modctl.output import CommandResult, StepResult


LineKind = Literal["error", "warn", "mod", "info"]

_PATTERNS = {
    "error": re.compile(r"\[(ERROR|FATAL)\]|Script compilation failed|NULL pointer", re.IGNORECASE),
    "warn": re.compile(r"\[WARN\]|WARNING:", re.IGNORECASE),
    "mod": re.compile(r"\[(BossSignal|TrophyHunter|HiveApi|CommunityFramework|CF)\]"),
}

_STYLES = {
    "error": "bold red",
    "warn": "yellow",
    "mod": "cyan",
    "info": "dim",
}


def classify_line(line: str) -> LineKind:
    if _PATTERNS["error"].search(line):
        return "error"
    if _PATTERNS["warn"].search(line):
        return "warn"
    if _PATTERNS["mod"].search(line):
        return "mod"
    return "info"


def colorize_line(line: str, kind: LineKind, use_color: bool = True) -> str:
    """Return the line with Rich-style color wrapping, or plain if no color."""
    if not use_color:
        return line
    # Rich Text API lets us build a styled string without side effects
    text = Text(line, style=_STYLES[kind])
    return text.markup  # render as "[style]line[/style]" so callers can print via Console


def tail_rpt(
    rpt_path: Path,
    console: Optional[Console] = None,
    poll_interval_s: float = 0.3,
    stop_event=None,
) -> None:
    """Stream the RPT file to the console. Blocks until stop_event is set
    or the file is deleted. Designed for long-running CLI use.
    """
    console = console or Console()
    with open(rpt_path, "r", encoding="utf-8", errors="replace") as f:
        # Seek to end — only stream new lines (standard tail -f behavior)
        f.seek(0, 2)
        while True:
            if stop_event is not None and stop_event.is_set():
                break
            line = f.readline()
            if not line:
                time.sleep(poll_interval_s)
                continue
            kind = classify_line(line.rstrip("\n"))
            console.print(Text(line.rstrip("\n"), style=_STYLES[kind]))


class TailOrchestrator:
    def __init__(self, config: ModsConfig) -> None:
        self.config = config

    def find(self) -> CommandResult:
        """Find + report the latest RPT log path, without streaming."""
        started = time.monotonic()
        result = CommandResult(command="tail", mod=None, status="ok")
        defaults = self.config.defaults
        server_root = Path(defaults.dayz_server_path)
        profile_dir = server_root / defaults.dayz_server_profile_dir

        step_start = time.monotonic()
        rpt = find_rpt_log(profile_dir)
        if rpt is None:
            result.steps.append(StepResult(
                name="find_rpt", status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "find_rpt"
            result.errors.append({
                "category": ErrorCategory.IO_ERROR.value,
                "message": f"No .RPT log found in {profile_dir}",
                "suggested_fix": "Start the DayZ Server (modctl serve) first so it writes its RPT log.",
            })
            result.duration_s = time.monotonic() - started
            return result

        result.steps.append(StepResult(
            name="find_rpt", status="ok",
            duration_s=time.monotonic() - step_start,
            details=f"Latest RPT: {rpt}",
        ))
        result.result["rpt_path"] = str(rpt)
        result.duration_s = time.monotonic() - started
        return result

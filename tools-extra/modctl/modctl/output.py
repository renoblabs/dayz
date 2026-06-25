"""Output formatting — human (Rich) and JSON modes."""
from __future__ import annotations

import json
import sys
from dataclasses import dataclass, field
from typing import Any, Dict, List, Literal, Optional, TextIO

OutputMode = Literal["human", "json"]


@dataclass
class StepResult:
    name: str
    status: Literal["ok", "skipped", "error"]
    duration_s: float = 0.0
    details: Optional[str] = None
    warnings: List[str] = field(default_factory=list)


@dataclass
class CommandResult:
    command: str
    mod: Optional[str]
    status: Literal["ok", "error"]
    duration_s: float = 0.0
    steps: List[StepResult] = field(default_factory=list)
    result: Dict[str, Any] = field(default_factory=dict)
    warnings: List[Dict[str, Any]] = field(default_factory=list)
    errors: List[Dict[str, Any]] = field(default_factory=list)
    failing_step: Optional[str] = None


class OutputFormatter:
    def __init__(self, mode: OutputMode = "human", stream: Optional[TextIO] = None) -> None:
        self.mode = mode
        self.stream = stream if stream is not None else sys.stdout

    def emit(self, result: CommandResult) -> None:
        if self.mode == "json":
            self._emit_json(result)
        else:
            self._emit_human(result)

    def _emit_json(self, result: CommandResult) -> None:
        payload = {
            "command": result.command,
            "mod": result.mod,
            "status": result.status,
            "duration_s": result.duration_s,
            "steps": [
                {
                    "name": s.name,
                    "status": s.status,
                    "duration_s": s.duration_s,
                    "details": s.details,
                    "warnings": s.warnings,
                }
                for s in result.steps
            ],
            "result": result.result,
            "warnings": result.warnings,
            "errors": result.errors,
            "failing_step": result.failing_step,
        }
        json.dump(payload, self.stream, indent=2)
        self.stream.write("\n")

    def _emit_human(self, result: CommandResult) -> None:
        stream = self.stream
        total = len(result.steps)
        # ASCII icons only — Windows cp1252 stdout crashes on Unicode glyphs.
        icons = {"ok": "[OK]", "skipped": "[SKIP]", "error": "[FAIL]"}
        for i, step in enumerate(result.steps, start=1):
            icon = icons[step.status]
            stream.write(f"[{i}/{total}] {step.name} {icon}")
            if step.duration_s:
                stream.write(f" ({step.duration_s:.1f}s)")
            stream.write("\n")
            if step.details:
                stream.write(f"        {step.details}\n")
        if result.status == "ok":
            target = f" {result.mod}" if result.mod else ""
            stream.write(f"OK: {result.command}{target} completed in {result.duration_s:.1f}s\n")
        else:
            target = f" {result.mod}" if result.mod else ""
            stream.write(f"FAIL: {result.command}{target}")
            if result.failing_step:
                stream.write(f" at step: {result.failing_step}")
            stream.write("\n")
            for err in result.errors:
                stream.write(f"   [{err.get('category', 'UNKNOWN')}] {err.get('message', '')}\n")
                fix = err.get("suggested_fix")
                if fix:
                    stream.write(f"   -> {fix}\n")

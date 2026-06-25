"""Diagnosis — rule-based matching of Enforce / DayZ Server log lines to
structured errors with suggested fixes.

Layer 1 of the diagnose subsystem (rules). Layer 2 (LLM-assisted diagnosis
of unmatched lines) is deferred; the architecture leaves a clean seam for it.
"""
from __future__ import annotations

import re
from dataclasses import dataclass, field
from importlib import resources
from pathlib import Path
from typing import List, Optional

import yaml

from modctl.errors import ErrorCategory


@dataclass
class Rule:
    id: str
    match: str
    category: ErrorCategory
    severity: str  # critical | warning | info
    confidence: str  # high | medium | low
    diagnosis: str
    fix_template: Optional[str] = None
    fix_action: Optional[str] = None
    can_auto_fix: bool = False

    _compiled: Optional[re.Pattern] = field(default=None, init=False, repr=False)

    @property
    def pattern(self) -> re.Pattern:
        if self._compiled is None:
            self._compiled = re.compile(self.match)
        return self._compiled


@dataclass
class DiagnosedError:
    rule_id: str
    category: ErrorCategory
    severity: str
    confidence: str
    raw_line: str
    line_num: int
    diagnosis: str
    fix_template: Optional[str] = None
    fix_action: Optional[str] = None
    can_auto_fix: bool = False


def load_rules(rules_path: Optional[Path] = None) -> List[Rule]:
    """Load rules from the bundled rules/enforce.yaml, or from a custom path."""
    if rules_path is None:
        # Bundled default — sits next to this module at modctl/rules/enforce.yaml
        rules_path = Path(__file__).parent / "rules" / "enforce.yaml"

    data = yaml.safe_load(rules_path.read_text(encoding="utf-8"))
    raw_rules = data.get("rules", [])
    rules: List[Rule] = []
    for raw in raw_rules:
        rules.append(Rule(
            id=raw["id"],
            match=raw["match"],
            category=ErrorCategory(raw["category"]),
            severity=raw["severity"],
            confidence=raw["confidence"],
            diagnosis=raw["diagnosis"],
            fix_template=raw.get("fix_template"),
            fix_action=raw.get("fix_action"),
            can_auto_fix=raw.get("can_auto_fix", False),
        ))
    return rules


def diagnose_line(line: str, rules: List[Rule], line_num: int = 0) -> Optional[DiagnosedError]:
    """Match a single log line against rules. Returns the first match, or None."""
    for rule in rules:
        m = rule.pattern.search(line)
        if m is None:
            continue
        diagnosis = rule.diagnosis
        # Substitute {capture.N} references with match groups (1-indexed)
        for idx, group in enumerate(m.groups(), start=1):
            diagnosis = diagnosis.replace(f"{{capture.{idx}}}", group or "")
        return DiagnosedError(
            rule_id=rule.id,
            category=rule.category,
            severity=rule.severity,
            confidence=rule.confidence,
            raw_line=line.rstrip("\n"),
            line_num=line_num,
            diagnosis=diagnosis,
            fix_template=rule.fix_template,
            fix_action=rule.fix_action,
            can_auto_fix=rule.can_auto_fix,
        )
    return None

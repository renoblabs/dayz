"""Tests for diagnosis data model + rule loader."""
from pathlib import Path

import pytest

from modctl.diagnosis import (
    DiagnosedError,
    Rule,
    diagnose_line,
    load_rules,
)
from modctl.errors import ErrorCategory


def test_load_rules_parses_default_library():
    rules = load_rules()  # loads bundled enforce.yaml
    assert len(rules) >= 5, f"Expected at least 5 seed rules, got {len(rules)}"
    ids = [r.id for r in rules]
    assert "rpt.null_identity_dereference" in ids
    assert "rpt.http_connection_refused" in ids


def test_rule_has_required_fields():
    rules = load_rules()
    r = rules[0]
    assert isinstance(r, Rule)
    assert r.id
    assert r.match
    assert isinstance(r.category, ErrorCategory)
    assert r.severity in ("critical", "warning", "info")
    assert r.confidence in ("high", "medium", "low")


def test_diagnose_line_matches_null_identity():
    rules = load_rules()
    line = "[ERROR] NULL pointer to instance in BossSignalEmitter::OnBossKilled (killer.GetIdentity())"
    diag = diagnose_line(line, rules)
    assert diag is not None
    assert diag.rule_id == "rpt.null_identity_dereference"
    assert diag.category == ErrorCategory.BUILD_ERROR
    assert diag.severity == "critical"


def test_diagnose_line_captures_backend_port():
    rules = load_rules()
    line = "[WARN]  [BossSignal] HTTP request failed: Connection refused 127.0.0.1:8080"
    diag = diagnose_line(line, rules)
    assert diag is not None
    assert diag.rule_id == "rpt.http_connection_refused"
    # Capture group substitution should resolve {capture.1} + {capture.2}
    assert "127.0.0.1" in diag.diagnosis
    assert "8080" in diag.diagnosis


def test_diagnose_line_returns_none_for_info_messages():
    rules = load_rules()
    line = "[INFO] Mission initialized."
    diag = diagnose_line(line, rules)
    assert diag is None


def test_diagnose_line_extracts_compile_file_and_line():
    rules = load_rules()
    line = "[ERROR] Script compilation failed: bosssignal-mod/scripts/5_mission/BossSignalEmitter.c @ line 78"
    diag = diagnose_line(line, rules)
    assert diag is not None
    assert diag.rule_id == "rpt.script_compile_failed"
    assert "BossSignalEmitter.c" in diag.diagnosis
    assert "78" in diag.diagnosis


def test_rule_can_auto_fix_flag_preserved():
    rules = load_rules()
    by_id = {r.id: r for r in rules}
    assert by_id["rpt.null_identity_dereference"].can_auto_fix is True
    assert by_id["rpt.http_connection_refused"].can_auto_fix is False

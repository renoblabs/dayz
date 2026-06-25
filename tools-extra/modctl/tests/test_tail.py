"""Tests for tail orchestration — RPT log coloring."""
from pathlib import Path

import pytest

from modctl.orchestration.tail import classify_line, colorize_line


def test_classify_line_error():
    assert classify_line("[ERROR] Script compilation failed") == "error"


def test_classify_line_warn():
    assert classify_line("[WARN] Deprecated API call") == "warn"


def test_classify_line_bosssignal():
    assert classify_line("[BossSignal] Config loaded | Server=server_01") == "mod"


def test_classify_line_trophyhunter():
    assert classify_line("[TrophyHunter] Awarded trophy to DarkHunter99") == "mod"


def test_classify_line_info():
    assert classify_line("Mission initialized.") == "info"


def test_classify_line_fatal():
    assert classify_line("[FATAL] Mission shutdown requested") == "error"


def test_colorize_line_produces_ansi_or_plain():
    # Just verifies it returns a string (Rich output may be plain in non-TTY)
    out = colorize_line("[ERROR] something", "error", use_color=False)
    assert "[ERROR]" in out
    assert "something" in out


def test_colorize_line_preserves_content_without_color():
    original = "[BossSignal] Emitter ready."
    out = colorize_line(original, "mod", use_color=False)
    assert "Emitter ready" in out
    assert "[BossSignal]" in out

"""Tests for file-system watcher action."""
import threading
import time
from pathlib import Path

import pytest

from modctl.actions.watcher import DebouncedWatcher


def test_watcher_fires_callback_on_file_modify(tmp_path):
    target = tmp_path / "foo.c"
    target.write_text("v1")

    fired = threading.Event()
    call_count = {"n": 0}

    def on_change(paths):
        call_count["n"] += 1
        fired.set()

    watcher = DebouncedWatcher(
        path=tmp_path,
        globs=["*.c"],
        callback=on_change,
        debounce_ms=100,
    )
    watcher.start()
    try:
        time.sleep(0.2)  # let watcher spin up
        target.write_text("v2")
        fired.wait(timeout=3.0)
        assert call_count["n"] >= 1
    finally:
        watcher.stop()


def test_watcher_debounces_rapid_saves(tmp_path):
    target = tmp_path / "bar.c"
    target.write_text("v1")

    events = []

    def on_change(paths):
        events.append(time.time())

    watcher = DebouncedWatcher(
        path=tmp_path,
        globs=["*.c"],
        callback=on_change,
        debounce_ms=200,
    )
    watcher.start()
    try:
        time.sleep(0.2)
        # Fire 5 saves within 100ms — should debounce into 1 callback
        for i in range(5):
            target.write_text(f"v{i}")
            time.sleep(0.02)
        time.sleep(0.5)  # wait past debounce window
        assert len(events) == 1, f"Expected 1 event after debounce, got {len(events)}"
    finally:
        watcher.stop()


def test_watcher_ignores_non_matching_globs(tmp_path):
    # Only *.c watched; .txt should not fire
    events = []

    def on_change(paths):
        events.append(paths)

    watcher = DebouncedWatcher(
        path=tmp_path,
        globs=["*.c"],
        callback=on_change,
        debounce_ms=100,
    )
    watcher.start()
    try:
        time.sleep(0.2)
        (tmp_path / "notes.txt").write_text("hi")
        time.sleep(0.4)
        assert events == []
    finally:
        watcher.stop()

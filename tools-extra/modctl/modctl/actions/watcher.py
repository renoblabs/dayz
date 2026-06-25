"""File-system watcher with debounce.

Wraps watchdog. Debounces rapid change bursts (editors often save + emit
multiple fs events) into a single callback. Filters by glob patterns.
"""
from __future__ import annotations

import fnmatch
import threading
import time
from pathlib import Path
from typing import Callable, List, Optional, Set

from watchdog.events import FileSystemEvent, FileSystemEventHandler
from watchdog.observers import Observer


class _Handler(FileSystemEventHandler):
    def __init__(self, parent: "DebouncedWatcher") -> None:
        self._parent = parent

    def on_any_event(self, event: FileSystemEvent) -> None:
        if event.is_directory:
            return
        self._parent._on_event(Path(event.src_path))


class DebouncedWatcher:
    """Watch `path` recursively, call `callback(list_of_paths)` after
    `debounce_ms` of quiet following any matching change.

    Matching files: any change whose path matches ANY of `globs`
    (fnmatch style, matched against the filename only).
    """

    def __init__(
        self,
        path: Path,
        globs: List[str],
        callback: Callable[[List[Path]], None],
        debounce_ms: int = 500,
    ) -> None:
        self._path = path
        self._globs = globs
        self._callback = callback
        self._debounce_s = debounce_ms / 1000.0
        self._observer: Optional[Observer] = None
        self._pending: Set[Path] = set()
        self._lock = threading.Lock()
        self._timer: Optional[threading.Timer] = None

    def _matches(self, path: Path) -> bool:
        return any(fnmatch.fnmatch(path.name, g) for g in self._globs)

    def _fire(self) -> None:
        with self._lock:
            paths = list(self._pending)
            self._pending.clear()
            self._timer = None
        if paths:
            self._callback(paths)

    def _on_event(self, path: Path) -> None:
        if not self._matches(path):
            return
        with self._lock:
            self._pending.add(path)
            if self._timer is not None:
                self._timer.cancel()
            self._timer = threading.Timer(self._debounce_s, self._fire)
            self._timer.daemon = True
            self._timer.start()

    def start(self) -> None:
        if self._observer is not None:
            return
        self._observer = Observer()
        self._observer.schedule(_Handler(self), str(self._path), recursive=True)
        self._observer.start()

    def stop(self) -> None:
        if self._observer is None:
            return
        # Cancel any pending debounce timer
        with self._lock:
            if self._timer is not None:
                self._timer.cancel()
                self._timer = None
        self._observer.stop()
        self._observer.join(timeout=2.0)
        self._observer = None

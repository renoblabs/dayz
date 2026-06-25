"""Watch orchestration — auto-ship on file change.

Observes a mod's source tree, debounces changes, and invokes ship().
Long-running (CLI layer handles Ctrl+C). Ship failures don't kill the
watcher — the user sees the failure and can fix + save again.
"""
from __future__ import annotations

from pathlib import Path
from typing import Callable, List, Optional

from modctl.actions.watcher import DebouncedWatcher
from modctl.config import Mod, ModsConfig
from modctl.errors import ErrorCategory, ModctlError
from modctl.output import CommandResult


ShipCallable = Callable[[str], CommandResult]


class WatchOrchestrator:
    def __init__(
        self,
        config: ModsConfig,
        ship_callable: ShipCallable,
        debounce_ms: int = 500,
    ) -> None:
        self.config = config
        self._ship = ship_callable
        self._debounce_ms = debounce_ms
        self._watcher: Optional[DebouncedWatcher] = None
        self._mod: Optional[Mod] = None

    def _find_mod(self, name: str) -> Mod:
        for m in self.config.mods:
            if m.name == name:
                return m
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"Mod '{name}' not found in mods.yaml",
        )

    def start(self, mod_name: str) -> None:
        """Begin watching. Blocks only during setup — the watcher runs in its
        own thread. Caller is expected to sleep / wait for Ctrl+C then call stop().
        """
        self._mod = self._find_mod(mod_name)
        source_path = Path(self._mod.source)
        globs = self._mod.watch or ["*.c", "config.cpp"]
        # Flatten glob patterns — fnmatch uses filename-only matching in DebouncedWatcher
        flat_globs = [self._flatten_glob(g) for g in globs]

        def _on_change(paths: List[Path]) -> None:
            result = self._ship(mod_name)
            # Watcher survives ship failures — the output already streamed to user.
            # No re-raise.

        self._watcher = DebouncedWatcher(
            path=source_path,
            globs=flat_globs,
            callback=_on_change,
            debounce_ms=self._debounce_ms,
        )
        self._watcher.start()

    def stop(self) -> None:
        if self._watcher is not None:
            self._watcher.stop()
            self._watcher = None

    @staticmethod
    def _flatten_glob(glob: str) -> str:
        """Turn a recursive glob like `scripts/**/*.c` into a filename pattern
        (`*.c`). DebouncedWatcher observes recursively — we filter by filename.
        """
        # Take everything after the last slash
        if "/" in glob:
            return glob.rsplit("/", 1)[1]
        return glob

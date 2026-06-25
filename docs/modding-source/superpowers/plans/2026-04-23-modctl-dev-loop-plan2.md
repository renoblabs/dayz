# Plan 2: modctl Dev Loop (watch / serve / tail / restart)

> Historical implementation plan. Check `tools-extra/modctl/modctl/cli.py` and `tools-extra/modctl/README.md` for current command behavior. In particular, verify real DayZ Tools/server behavior locally before relying on the full watch/serve loop.

**Goal:** Turn modctl into the fast-iteration tool. After Plan 2, saving a `.c` file triggers automatic rebuild + redeploy + server restart in <20 seconds, and RPT log streams live to the terminal.

**Architecture:** Adds orchestration/ + actions/ modules for long-running processes (DayZ Server lifecycle, RPT log tailing, file watching). Uses `watchdog` for file-system events. Subprocess management for DayZ Server.

**Tech stack additions:** `watchdog>=3.0.0` as a new dep.

**Spec reference:** `docs/superpowers/specs/2026-04-23-modctl-design.md` - Sections 2 (runtime commands) and 4 (long-running commands).

## Non-goals

- Server-side smoke test assertions (Plan 3 adds diagnose)
- Auto-detection of RPT log path across DayZ versions (use default paths + config override)
- Multi-server serve (one local server at a time)
- Cross-platform (Windows-only for now)

## File structure

New files:
```
tools-extra/modctl/modctl/
|-- actions/
|   |-- dayz_server.py      # DayZServer_x64.exe launch/stop wrapper
|   `-- watcher.py          # watchdog file-system observer wrapper
`-- orchestration/
    |-- serve.py            # ServeOrchestrator - boot server, stream logs
    |-- restart.py          # RestartOrchestrator - graceful stop + start
    |-- tail.py             # TailOrchestrator - RPT log streaming w/ color
    `-- watch.py            # WatchOrchestrator - file-change -> ship

tools-extra/modctl/tests/
|-- test_dayz_server.py
|-- test_watcher.py
|-- test_serve.py
|-- test_tail.py
`-- test_watch.py
```

Modified:
- `tools-extra/modctl/pyproject.toml` - add watchdog dep
- `tools-extra/modctl/modctl/cli.py` - wire 4 new commands
- `tools-extra/modctl/README.md` - document new commands
- `tools-extra/modctl/mods.yaml` - add `dayz_server.{rpt_log_dir, profile_dir, port, startup_params}` to defaults

## Tasks

### Task 1: Add watchdog dep + reinstall
- Update `pyproject.toml` dependencies
- `pip install -e ".[dev]"`
- Commit

### Task 2: DayZ Server action layer
- Create `actions/dayz_server.py` with `start_server(config) -> subprocess.Popen` and `stop_server(pid)` + `find_rpt_log(profile_dir) -> Path`
- TDD: mock subprocess.Popen, test command construction + RPT log path finder
- Commit

### Task 3: File watcher action layer
- Create `actions/watcher.py` with `watch_directory(path, callback, globs, debounce_ms)` - wraps watchdog
- TDD: write a test that creates a file, watches it, modifies it, verifies callback fires once after debounce
- Commit

### Task 4: Config schema - dayz_server block
- Extend `Defaults` Pydantic model with `dayz_server_profile_dir`, `dayz_server_port`, `dayz_server_startup_params` (Optional, with sensible Windows defaults)
- Update `mods.yaml` with explicit values
- Tests verify loading
- Commit

### Task 5: Serve orchestration
- `orchestration/serve.py` - `ServeOrchestrator.serve(detached=False, include_keys=True)` - starts DayZ Server, streams stdout + RPT, handles Ctrl+C
- Uses `dayz_server.start_server()` + Python threading for stream merging
- Tests with mocks
- Commit

### Task 6: Tail orchestration
- `orchestration/tail.py` - `TailOrchestrator.tail()` - finds latest RPT, streams with colored prefixes (`[SERVER]`, `[ERROR]`, `[BossSignal]`, etc.)
- Uses Python `rich` library for coloring
- Tests feed fixture RPT content, verify output
- Commit

### Task 7: Restart orchestration
- `orchestration/restart.py` - `RestartOrchestrator.restart()` - stop_server(pid) from state -> start_server -> wait for ready signal
- Uses `.modctl/state.json` for PID tracking
- Tests with mocks
- Commit

### Task 8: Watch orchestration
- `orchestration/watch.py` - `WatchOrchestrator.watch(mod_name)` - watchdog on mod.watch globs -> debounce 500ms -> invoke ShipOrchestrator
- Graceful Ctrl+C
- Tests: simulate save events, verify ship triggers
- Commit

### Task 9: CLI wiring
- Add `modctl serve`, `modctl restart`, `modctl tail`, `modctl watch <mod>` to cli.py
- Support `--detached` on serve
- Tests
- Commit

### Task 10: Update README + mods.yaml documentation
- Document new commands
- Update mods.yaml with new defaults keys
- Commit

## Validation

After Task 10:
- `pytest -v` -> all tests pass (Plan 1 + Plan 2)
- `modctl --help` shows 9 commands (version, doctor, build, deploy, ship, serve, restart, tail, watch)
- Manual: `modctl watch bosssignal` listens on mods/BossSignal/scripts/, modifies a .c file, verifies auto-ship (requires DayZ Tools installed for full loop; logic-only validation OK without)

## Checkpoint (Approach B)

After Plan 2 commits are pushed, **pause and run `modctl doctor` + `modctl ship bosssignal` against real DayZ Tools** (if installed). If fails, diagnose and fix in-place before starting Plan 3. If DayZ Tools not yet installed, defer to when it is.

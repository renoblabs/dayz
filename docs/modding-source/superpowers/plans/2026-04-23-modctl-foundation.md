# modctl Foundation - Implementation Plan (Plan 1 of 4)

> Historical implementation plan. Current modctl source lives under `tools-extra/modctl`, current source paths in examples may differ, and current `ship` means build + deploy only. Treat future release/catalog/smoke-test language as design intent unless the code in `tools-extra/modctl` implements it.

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build the `modctl` CLI foundation - config loader, CLI skeleton, action layer, and the first four commands (`doctor`, `build`, `deploy`, `ship`) - so the developer can run `modctl ship bosssignal` end-to-end to produce a signed PBO deployed to his local DayZ Server.

**Architecture:** Three-layer Python CLI at `tools-extra/modctl/`. Typer for command parsing -> Pydantic for config -> thin subprocess wrappers around AddonBuilder/DSSignFile/DayZ Server. All state in `mods.yaml`. JSON output mode for Claude Code orchestration.

**Tech Stack:** Python 3.11+, Typer (CLI), Pydantic 2 (config), Rich (output), PyYAML, pytest (testing), stdlib `subprocess` for tool invocation.

**Spec reference:** `docs/superpowers/specs/2026-04-23-modctl-design.md` - Sections 1, 2 (subset), 3, 4, and acceptance criteria 1-3, 8-10.

---

## Scope & Non-goals

### In scope for Plan 1
- Python project skeleton at `tools-extra/modctl/`
- `mods.yaml` parsing + Pydantic validation + env-var substitution + path resolution
- CLI skeleton (Typer) + entry point
- Error categories + exit-code mapping
- Human output + JSON output modes
- Action layer: subprocess runner, AddonBuilder wrapper, filesystem ops
- Enforce config substitution (sed-style replacement of SERVER_ID etc. at build time)
- Commands: `doctor`, `build`, `deploy`, `ship`
- Unit tests for every module
- README for `tools-extra/modctl/`

### Out of scope (future plans)
- `watch` / `serve` / `tail` - Plan 2
- `diagnose` / `fix` / rule library - Plan 3
- `release` / `docs` / `catalog` / `announce` - Plan 4
- Market research commands (`scout`, `rank`) - M4+
- Production server commands (`prod *`) - M3+
- TUI - M4+
- HiveAPI support - comes through naturally once `mods.yaml` entry is added, but `branch` hint check is Plan 2

## Prerequisites

Before starting this plan:
1. Python 3.11+ installed (the  rig likely has this via backend work)
2. Working directory: on `bosssignal` branch of `dayzAPI` repo
3. DayZ Tools installed (for later end-to-end validation, not required for writing code)
4. DayZ Server installed (same - needed for end-to-end only)
5. Signing keypair generated via `build-pipeline/sign-keygen.bat` (can defer to end-to-end)

**Historical branch note:** this plan originally executed on the old `bosssignal` branch. In the consolidated repo, work from `~/Dayz/dayz` unless explicitly creating a throwaway worktree.

---

## File Structure

Files created by this plan:

```
tools-extra/modctl/
|-- pyproject.toml                      # Package metadata, deps, entry point
|-- README.md                           # Usage + command reference
|-- mods.yaml                           # Config for this repo's mods
|-- .gitignore                          # Ignore .modctl/ state dir
|-- modctl/
|   |-- __init__.py                     # Version string
|   |-- __main__.py                     # `python -m modctl` entry
|   |-- cli.py                          # Typer app + command registrations
|   |-- config.py                       # Pydantic models + loading
|   |-- errors.py                       # Error categories, ModctlError
|   |-- output.py                       # Human + JSON formatters
|   |-- orchestration/
|   |   |-- __init__.py
|   |   |-- build.py                    # Build plan + execution
|   |   |-- deploy.py                   # Deploy plan + execution
|   |   |-- ship.py                     # build + deploy + minimal smoke
|   |   `-- doctor.py                   # Toolchain health check
|   `-- actions/
|       |-- __init__.py
|       |-- runner.py                   # Subprocess wrapper with timeout
|       |-- addon_builder.py            # AddonBuilder.exe wrapper
|       `-- filesystem.py               # PBO copy, path verification
`-- tests/
    |-- __init__.py
    |-- conftest.py                     # pytest fixtures
    |-- fixtures/
    |   |-- mods.example.yaml           # Valid config
    |   |-- mods.invalid.yaml           # Missing required fields
    |   |-- mock_mod/                   # Fake mod for build tests
    |   |   |-- config.cpp
    |   |   `-- scripts/3_game/FakeConfig.c
    |   `-- keys/
    |       `-- .gitkeep
    |-- test_config.py
    |-- test_errors.py
    |-- test_output.py
    |-- test_doctor.py
    |-- test_build.py
    |-- test_deploy.py
    |-- test_ship.py
    |-- test_addon_builder.py
    `-- test_runner.py
```

Each file has one clear responsibility. Action layer is swappable (DayZ 2 migration = replace `actions/` only). Orchestration holds the domain logic. CLI is thin glue.

---

## Task 1: Project skeleton

**Files:**
- Create: `tools-extra/modctl/pyproject.toml`
- Create: `tools-extra/modctl/README.md` (stub)
- Create: `tools-extra/modctl/.gitignore`
- Create: `tools-extra/modctl/modctl/__init__.py`
- Create: `tools-extra/modctl/modctl/__main__.py`
- Create: `tools-extra/modctl/modctl/cli.py` (minimal)
- Create: `tools-extra/modctl/tests/__init__.py`
- Create: `tools-extra/modctl/tests/conftest.py` (empty)

- [ ] **Step 1: Create directory structure**

```bash
mkdir -p tools-extra/modctl/modctl/orchestration
mkdir -p tools-extra/modctl/modctl/actions
mkdir -p tools-extra/modctl/tests/fixtures/mock_mod/scripts/3_game
mkdir -p tools-extra/modctl/tests/fixtures/keys
touch tools-extra/modctl/tests/fixtures/keys/.gitkeep
```

- [ ] **Step 2: Write `tools-extra/modctl/pyproject.toml`**

```toml
[project]
name = "modctl"
version = "0.1.0"
description = "DayZ mod development workflow CLI"
requires-python = ">=3.11"
dependencies = [
    "typer[all]>=0.9.0",
    "pydantic>=2.0.0",
    "pyyaml>=6.0",
    "rich>=13.0.0",
]

[project.optional-dependencies]
dev = [
    "pytest>=7.4.0",
    "pytest-asyncio>=0.21.1",
    "mypy>=1.5.0",
]

[project.scripts]
modctl = "modctl.cli:app"

[build-system]
requires = ["setuptools>=61.0"]
build-backend = "setuptools.build_meta"

[tool.setuptools.packages.find]
where = ["."]
include = ["modctl*"]

[tool.pytest.ini_options]
testpaths = ["tests"]
python_files = ["test_*.py"]
```

- [ ] **Step 3: Write `tools-extra/modctl/.gitignore`**

```
.modctl/
__pycache__/
*.pyc
.pytest_cache/
*.egg-info/
dist/
build/
.mypy_cache/
```

- [ ] **Step 4: Write `tools-extra/modctl/modctl/__init__.py`**

```python
"""modctl - DayZ mod development workflow CLI."""
__version__ = "0.1.0"
```

- [ ] **Step 5: Write `tools-extra/modctl/modctl/__main__.py`**

```python
"""Entry point: `python -m modctl`."""
from modctl.cli import app

if __name__ == "__main__":
    app()
```

- [ ] **Step 6: Write `tools-extra/modctl/modctl/cli.py` (minimal stub)**

```python
"""modctl CLI - Typer app and command registrations."""
import typer

app = typer.Typer(
    name="modctl",
    help="DayZ mod development workflow CLI.",
    no_args_is_help=True,
)


@app.command()
def version() -> None:
    """Print modctl version."""
    from modctl import __version__
    typer.echo(f"modctl {__version__}")
```

- [ ] **Step 7: Write `tools-extra/modctl/README.md` stub**

```markdown
# modctl

DayZ mod development workflow CLI.

See `docs/superpowers/specs/2026-04-23-modctl-design.md` for design.

## Install (development)

```bash
cd tools-extra/modctl
pip install -e ".[dev]"
```

## Commands

Run `modctl --help` for the full command list.

Documentation will be filled in as commands ship.
```

- [ ] **Step 8: Create empty `__init__.py` files**

```bash
touch tools-extra/modctl/tests/__init__.py
touch tools-extra/modctl/modctl/orchestration/__init__.py
touch tools-extra/modctl/modctl/actions/__init__.py
echo "" > tools-extra/modctl/tests/conftest.py
```

- [ ] **Step 9: Install the package in dev mode and verify**

```bash
cd tools-extra/modctl && pip install -e ".[dev]" && modctl version
```

Expected: `modctl 0.1.0`

- [ ] **Step 10: Commit**

```bash
git add tools-extra/modctl/
git commit -m "feat(modctl): project skeleton + Typer CLI stub"
```

---

## Task 2: Error categories + exit codes

**Files:**
- Create: `tools-extra/modctl/modctl/errors.py`
- Create: `tools-extra/modctl/tests/test_errors.py`

- [ ] **Step 1: Write the failing test `tests/test_errors.py`**

```python
"""Tests for error categories and ModctlError."""
import pytest

from modctl.errors import ErrorCategory, ModctlError, exit_code_for


def test_error_categories_have_expected_exit_codes():
    assert exit_code_for(ErrorCategory.CONFIG_ERROR) == 10
    assert exit_code_for(ErrorCategory.BUILD_ERROR) == 20
    assert exit_code_for(ErrorCategory.SIGN_ERROR) == 21
    assert exit_code_for(ErrorCategory.DEPLOY_ERROR) == 30
    assert exit_code_for(ErrorCategory.SERVER_ERROR) == 40
    assert exit_code_for(ErrorCategory.TEST_ERROR) == 50
    assert exit_code_for(ErrorCategory.IO_ERROR) == 60
    assert exit_code_for(ErrorCategory.DEPENDENCY_ERROR) == 70
    assert exit_code_for(ErrorCategory.CONFLICT_ERROR) == 80
    assert exit_code_for(ErrorCategory.UNKNOWN) == 90


def test_modctl_error_captures_category_and_message():
    err = ModctlError(
        ErrorCategory.CONFIG_ERROR,
        "Missing env var: BOSSSIGNAL_SECRET",
        details="env var not found in environment",
        suggested_fix="export BOSSSIGNAL_SECRET=...",
    )
    assert err.category == ErrorCategory.CONFIG_ERROR
    assert "BOSSSIGNAL_SECRET" in str(err)
    assert err.suggested_fix.startswith("export")


def test_modctl_error_is_raisable():
    with pytest.raises(ModctlError) as exc_info:
        raise ModctlError(ErrorCategory.IO_ERROR, "file not found")
    assert exc_info.value.category == ErrorCategory.IO_ERROR
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_errors.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.errors'`

- [ ] **Step 3: Write `tools-extra/modctl/modctl/errors.py`**

```python
"""Error categories and ModctlError - structured errors across the CLI."""
from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorCategory(str, Enum):
    CONFIG_ERROR = "CONFIG_ERROR"
    BUILD_ERROR = "BUILD_ERROR"
    SIGN_ERROR = "SIGN_ERROR"
    DEPLOY_ERROR = "DEPLOY_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    TEST_ERROR = "TEST_ERROR"
    IO_ERROR = "IO_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    CONFLICT_ERROR = "CONFLICT_ERROR"
    UNKNOWN = "UNKNOWN"


_EXIT_CODES = {
    ErrorCategory.CONFIG_ERROR: 10,
    ErrorCategory.BUILD_ERROR: 20,
    ErrorCategory.SIGN_ERROR: 21,
    ErrorCategory.DEPLOY_ERROR: 30,
    ErrorCategory.SERVER_ERROR: 40,
    ErrorCategory.TEST_ERROR: 50,
    ErrorCategory.IO_ERROR: 60,
    ErrorCategory.DEPENDENCY_ERROR: 70,
    ErrorCategory.CONFLICT_ERROR: 80,
    ErrorCategory.UNKNOWN: 90,
}


def exit_code_for(category: ErrorCategory) -> int:
    return _EXIT_CODES[category]


class ModctlError(Exception):
    """Base exception for all modctl-raised errors.

    Carries a category (for exit codes + JSON output), a human message,
    optional details (stderr excerpt, context), and an optional suggested fix.
    """

    def __init__(
        self,
        category: ErrorCategory,
        message: str,
        details: Optional[str] = None,
        suggested_fix: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.details = details
        self.suggested_fix = suggested_fix

    def __str__(self) -> str:
        return f"[{self.category.value}] {self.message}"
```

- [ ] **Step 4: Run test and verify it passes**

```bash
cd tools-extra/modctl && pytest tests/test_errors.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/errors.py tools-extra/modctl/tests/test_errors.py
git commit -m "feat(modctl): error categories + exit code mapping"
```

---

## Task 3: Config models (Pydantic) - basic loading

**Files:**
- Create: `tools-extra/modctl/modctl/config.py`
- Create: `tools-extra/modctl/tests/fixtures/mods.example.yaml`
- Create: `tools-extra/modctl/tests/test_config.py`

- [ ] **Step 1: Write the test fixture `tests/fixtures/mods.example.yaml`**

```yaml
version: 1

defaults:
  dayz_tools_path: "/tmp/fake-dayz-tools"
  dayz_server_path: "/tmp/fake-dayz-server"
  signing_keys_dir: "build-pipeline/keys"
  output_dir: "output"
  pack_only: true
  pbo_prefix_matches_name: true

backends:
  bosssignal:
    kind: fastapi
    dir: "bosssignal-backend"
    tests: "pytest tests/ -q"
    compose_file: null
    health_url: "http://127.0.0.1:6700/health"

mods:
  - name: bosssignal
    source: "../../mods/BossSignal"
    pbo_name: "BossSignal"
    mod_folder: "@BossSignal"
    depends_on: [cf]
    backend: bosssignal
    enforce_config:
      file: "scripts/3_game/BossSignalConfig.c"
      vars:
        SERVER_ID: "server_01"
        BACKEND_URL: "http://127.0.0.1:6700"
        SHARED_SECRET: "${TEST_SECRET}"
    watch: ["scripts/**/*.c", "config.cpp"]

dependencies:
  cf:
    name: "Community Framework"
    workshop_id: "1559212036"
    mod_folder: "@CommunityFramework"
    required: true
```

- [ ] **Step 2: Write the failing test `tests/test_config.py`**

```python
"""Tests for mods.yaml loading and Pydantic validation."""
from pathlib import Path

import pytest

from modctl.config import load_mods_yaml, ModsConfig

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_valid_mods_yaml_returns_mods_config():
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    assert isinstance(config, ModsConfig)
    assert config.version == 1


def test_mods_config_has_bosssignal_mod():
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    names = [m.name for m in config.mods]
    assert "bosssignal" in names


def test_mod_has_pbo_name_and_source():
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    bs = next(m for m in config.mods if m.name == "bosssignal")
    assert bs.pbo_name == "BossSignal"
    assert bs.source == "../../mods/BossSignal"


def test_mod_backend_reference_resolvable():
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    bs = next(m for m in config.mods if m.name == "bosssignal")
    assert bs.backend == "bosssignal"
    assert "bosssignal" in config.backends
    assert config.backends["bosssignal"].kind == "fastapi"


def test_dependencies_block_parses():
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    assert "cf" in config.dependencies
    assert config.dependencies["cf"].workshop_id == "1559212036"
```

- [ ] **Step 3: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_config.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.config'`

- [ ] **Step 4: Write `tools-extra/modctl/modctl/config.py`**

```python
"""mods.yaml loader + Pydantic models.

Loaded once at the start of every command invocation. Validates the config
fails fast on typos, missing required fields, wrong types.
"""
from __future__ import annotations

from pathlib import Path
from typing import Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field

from modctl.errors import ErrorCategory, ModctlError


class Defaults(BaseModel):
    dayz_tools_path: str
    dayz_server_path: str
    signing_keys_dir: str
    output_dir: str
    pack_only: bool = True
    pbo_prefix_matches_name: bool = True


class Backend(BaseModel):
    kind: Literal["fastapi", "custom"]
    dir: str
    tests: Optional[str] = None
    compose_file: Optional[str] = None
    health_url: Optional[str] = None


class EnforceConfig(BaseModel):
    file: str
    vars: Dict[str, str] = Field(default_factory=dict)


class Mod(BaseModel):
    name: str
    source: str
    pbo_name: str
    mod_folder: str
    depends_on: List[str] = Field(default_factory=list)
    backend: Optional[str] = None
    branch: Optional[str] = None
    enforce_config: Optional[EnforceConfig] = None
    watch: List[str] = Field(default_factory=list)


class Dependency(BaseModel):
    name: str
    workshop_id: Optional[str] = None
    mod_folder: str
    required: bool = True


class ModsConfig(BaseModel):
    version: int = 1
    defaults: Defaults
    backends: Dict[str, Backend] = Field(default_factory=dict)
    mods: List[Mod] = Field(default_factory=list)
    dependencies: Dict[str, Dependency] = Field(default_factory=dict)


def load_mods_yaml(path: Path) -> ModsConfig:
    """Load and validate a mods.yaml file. Raises ModctlError on any problem."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"mods.yaml not found at {path}",
            suggested_fix=f"Create {path} or pass --config <path>",
        )
    except yaml.YAMLError as e:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"Invalid YAML in {path}",
            details=str(e),
        )

    try:
        return ModsConfig.model_validate(data)
    except Exception as e:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"mods.yaml validation failed",
            details=str(e),
        )
```

- [ ] **Step 5: Run tests and verify they pass**

```bash
cd tools-extra/modctl && pytest tests/test_config.py -v
```

Expected: `5 passed`

- [ ] **Step 6: Commit**

```bash
git add tools-extra/modctl/modctl/config.py tools-extra/modctl/tests/fixtures/mods.example.yaml tools-extra/modctl/tests/test_config.py
git commit -m "feat(modctl): mods.yaml Pydantic models + loader"
```

---

## Task 4: Config - env var substitution

**Files:**
- Modify: `tools-extra/modctl/modctl/config.py` (add `resolve_env_vars()`)
- Modify: `tools-extra/modctl/tests/test_config.py` (add tests)

- [ ] **Step 1: Add the failing test to `tests/test_config.py`**

Append to the file:

```python
import os


def test_env_var_substitution_resolves_shared_secret(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "actual-secret-value")
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    bs = next(m for m in config.mods if m.name == "bosssignal")
    assert bs.enforce_config.vars["SHARED_SECRET"] == "actual-secret-value"


def test_env_var_substitution_fails_loud_on_missing(monkeypatch):
    monkeypatch.delenv("TEST_SECRET", raising=False)
    with pytest.raises(Exception) as exc_info:
        load_mods_yaml(FIXTURES / "mods.example.yaml")
    assert "TEST_SECRET" in str(exc_info.value)
```

- [ ] **Step 2: Run tests and verify new tests fail**

```bash
cd tools-extra/modctl && pytest tests/test_config.py -v
```

Expected: the 2 new tests fail; the others still pass. The new tests fail because `SHARED_SECRET` still equals `${TEST_SECRET}` literal.

- [ ] **Step 3: Add `_resolve_env_vars()` to `config.py`**

Insert before `load_mods_yaml()`:

```python
import os
import re

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _resolve_env_vars(value):
    """Recursively substitute ${VAR} references in strings inside nested data.

    Raises ModctlError if any referenced var is not set in the environment.
    """
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name not in os.environ:
                raise ModctlError(
                    ErrorCategory.CONFIG_ERROR,
                    f"Missing env var: {var_name}",
                    details=f"Referenced in mods.yaml as ${{{var_name}}}",
                    suggested_fix=f"export {var_name}=<value>",
                )
            return os.environ[var_name]

        return _ENV_VAR_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value
```

- [ ] **Step 4: Wire `_resolve_env_vars()` into `load_mods_yaml()`**

In `load_mods_yaml`, between `yaml.safe_load` and `ModsConfig.model_validate`, add:

```python
    data = _resolve_env_vars(data)
```

So the function looks like:

```python
def load_mods_yaml(path: Path) -> ModsConfig:
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"mods.yaml not found at {path}",
            suggested_fix=f"Create {path} or pass --config <path>",
        )
    except yaml.YAMLError as e:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"Invalid YAML in {path}",
            details=str(e),
        )

    data = _resolve_env_vars(data)

    try:
        return ModsConfig.model_validate(data)
    except Exception as e:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"mods.yaml validation failed",
            details=str(e),
        )
```

- [ ] **Step 5: Run tests and verify all pass**

```bash
cd tools-extra/modctl && pytest tests/test_config.py -v
```

Expected: `7 passed`

- [ ] **Step 6: Commit**

```bash
git add tools-extra/modctl/modctl/config.py tools-extra/modctl/tests/test_config.py
git commit -m "feat(modctl): env var substitution in mods.yaml (fail loud on missing)"
```

---

## Task 5: Output formatting - human + JSON modes

**Files:**
- Create: `tools-extra/modctl/modctl/output.py`
- Create: `tools-extra/modctl/tests/test_output.py`

- [ ] **Step 1: Write the failing test `tests/test_output.py`**

```python
"""Tests for OutputFormatter - human and JSON output modes."""
import json
from io import StringIO

from modctl.output import CommandResult, OutputFormatter, StepResult


def test_human_output_prints_steps():
    buf = StringIO()
    fmt = OutputFormatter(mode="human", stream=buf)
    result = CommandResult(command="build", mod="bosssignal", status="ok", duration_s=5.3)
    result.steps.append(StepResult(name="resolve_config", status="ok", duration_s=0.1))
    result.steps.append(StepResult(name="addon_builder", status="ok", duration_s=4.2))
    fmt.emit(result)
    out = buf.getvalue()
    assert "resolve_config" in out
    assert "addon_builder" in out
    assert "bosssignal" in out


def test_json_output_produces_valid_json():
    buf = StringIO()
    fmt = OutputFormatter(mode="json", stream=buf)
    result = CommandResult(command="build", mod="bosssignal", status="ok", duration_s=5.3)
    result.steps.append(StepResult(name="resolve_config", status="ok", duration_s=0.1))
    fmt.emit(result)
    parsed = json.loads(buf.getvalue())
    assert parsed["command"] == "build"
    assert parsed["mod"] == "bosssignal"
    assert parsed["status"] == "ok"
    assert parsed["duration_s"] == 5.3
    assert parsed["steps"][0]["name"] == "resolve_config"


def test_command_result_error_status_propagates():
    result = CommandResult(command="build", mod="bosssignal", status="error", duration_s=2.1)
    result.failing_step = "addon_builder"
    result.errors.append({"category": "BUILD_ERROR", "message": "Missing ;"})

    buf = StringIO()
    fmt = OutputFormatter(mode="json", stream=buf)
    fmt.emit(result)
    parsed = json.loads(buf.getvalue())
    assert parsed["status"] == "error"
    assert parsed["failing_step"] == "addon_builder"
    assert parsed["errors"][0]["category"] == "BUILD_ERROR"
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_output.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.output'`

- [ ] **Step 3: Write `tools-extra/modctl/modctl/output.py`**

```python
"""Output formatting - human (Rich) and JSON modes."""
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
        for i, step in enumerate(result.steps, start=1):
            icon = {"ok": "ok", "skipped": "[skipped]", "error": "FAIL"}[step.status]
            stream.write(f"[{i}/{total}] {step.name} {icon}")
            if step.duration_s:
                stream.write(f" ({step.duration_s:.1f}s)")
            stream.write("\n")
        if result.status == "ok":
            target = f" {result.mod}" if result.mod else ""
            stream.write(f"[done]  {result.command}{target} completed in {result.duration_s:.1f}s\n")
        else:
            target = f" {result.mod}" if result.mod else ""
            stream.write(f"FAIL  {result.command}{target} failed")
            if result.failing_step:
                stream.write(f" at step: {result.failing_step}")
            stream.write("\n")
            for err in result.errors:
                stream.write(f"   [{err.get('category', 'UNKNOWN')}] {err.get('message', '')}\n")
```

- [ ] **Step 4: Run tests and verify all pass**

```bash
cd tools-extra/modctl && pytest tests/test_output.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/output.py tools-extra/modctl/tests/test_output.py
git commit -m "feat(modctl): CommandResult + OutputFormatter (human + json)"
```

---

## Task 6: Action layer - subprocess runner

**Files:**
- Create: `tools-extra/modctl/modctl/actions/runner.py`
- Create: `tools-extra/modctl/tests/test_runner.py`

- [ ] **Step 1: Write the failing test `tests/test_runner.py`**

```python
"""Tests for subprocess runner."""
import pytest

from modctl.actions.runner import run_command, CommandOutput
from modctl.errors import ModctlError, ErrorCategory


def test_run_command_returns_output_on_success():
    result = run_command(["python", "-c", "print('hello')"], timeout_s=10)
    assert isinstance(result, CommandOutput)
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_run_command_captures_nonzero_returncode():
    result = run_command(["python", "-c", "import sys; sys.exit(7)"], timeout_s=10)
    assert result.returncode == 7


def test_run_command_raises_modctl_error_on_timeout():
    with pytest.raises(ModctlError) as exc_info:
        run_command(
            ["python", "-c", "import time; time.sleep(10)"],
            timeout_s=1,
        )
    assert exc_info.value.category == ErrorCategory.IO_ERROR
    assert "timed out" in exc_info.value.message.lower()


def test_run_command_captures_stderr():
    result = run_command(
        ["python", "-c", "import sys; print('oops', file=sys.stderr); sys.exit(1)"],
        timeout_s=10,
    )
    assert result.returncode == 1
    assert "oops" in result.stderr
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_runner.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.actions.runner'`

- [ ] **Step 3: Write `tools-extra/modctl/modctl/actions/runner.py`**

```python
"""Subprocess runner - unified interface for external tool invocation.

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

    Does NOT raise on non-zero exit - caller inspects returncode + stderr.
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
```

- [ ] **Step 4: Run tests and verify all pass**

```bash
cd tools-extra/modctl && pytest tests/test_runner.py -v
```

Expected: `4 passed`

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/actions/runner.py tools-extra/modctl/tests/test_runner.py
git commit -m "feat(modctl): subprocess runner with timeout + output capture"
```

---

## Task 7: Action layer - AddonBuilder wrapper

**Files:**
- Create: `tools-extra/modctl/modctl/actions/addon_builder.py`
- Create: `tools-extra/modctl/tests/test_addon_builder.py`

- [ ] **Step 1: Write the failing test**

```python
"""Tests for AddonBuilder wrapper."""
from pathlib import Path
from unittest.mock import patch

import pytest

from modctl.actions.addon_builder import AddonBuilderResult, build_pbo
from modctl.actions.runner import CommandOutput
from modctl.errors import ErrorCategory, ModctlError


def _fake_cmd_output(returncode: int = 0, stdout: str = "", stderr: str = "") -> CommandOutput:
    return CommandOutput(
        returncode=returncode, stdout=stdout, stderr=stderr,
        duration_s=1.0, command=["fake"],
    )


def test_build_pbo_success(tmp_path):
    output_dir = tmp_path / "addons"
    output_dir.mkdir()
    # simulate AddonBuilder creating the pbo
    (output_dir / "FakeMod.pbo").write_text("fake pbo content")

    with patch("modctl.actions.addon_builder.run_command") as mock_run:
        mock_run.return_value = _fake_cmd_output(returncode=0, stdout="Packed successfully.")

        result = build_pbo(
            addon_builder_path=tmp_path / "AddonBuilder.exe",
            source_dir=tmp_path / "mod_source",
            output_dir=output_dir,
            signing_key=tmp_path / "key.biprivatekey",
            prefix="FakeMod",
            pack_only=True,
        )

    assert isinstance(result, AddonBuilderResult)
    assert result.pbo_path == output_dir / "FakeMod.pbo"
    assert result.duration_s > 0


def test_build_pbo_failure_raises_build_error(tmp_path):
    with patch("modctl.actions.addon_builder.run_command") as mock_run:
        mock_run.return_value = _fake_cmd_output(
            returncode=1,
            stderr="[ERROR] Missing ';' at line 51 in config.cpp",
        )

        with pytest.raises(ModctlError) as exc_info:
            build_pbo(
                addon_builder_path=tmp_path / "AddonBuilder.exe",
                source_dir=tmp_path / "mod_source",
                output_dir=tmp_path / "out",
                signing_key=tmp_path / "key.biprivatekey",
                prefix="FakeMod",
                pack_only=True,
            )

    assert exc_info.value.category == ErrorCategory.BUILD_ERROR
    assert "Missing" in exc_info.value.details


def test_build_pbo_missing_output_raises_io_error(tmp_path):
    # Simulate AddonBuilder returning success but no PBO produced
    output_dir = tmp_path / "addons"
    output_dir.mkdir()
    # (intentionally NOT creating the pbo file)

    with patch("modctl.actions.addon_builder.run_command") as mock_run:
        mock_run.return_value = _fake_cmd_output(returncode=0, stdout="OK")

        with pytest.raises(ModctlError) as exc_info:
            build_pbo(
                addon_builder_path=tmp_path / "AddonBuilder.exe",
                source_dir=tmp_path / "mod_source",
                output_dir=output_dir,
                signing_key=tmp_path / "key.biprivatekey",
                prefix="FakeMod",
                pack_only=True,
            )

    assert exc_info.value.category == ErrorCategory.IO_ERROR
    assert "FakeMod.pbo" in exc_info.value.message
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_addon_builder.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.actions.addon_builder'`

- [ ] **Step 3: Write `tools-extra/modctl/modctl/actions/addon_builder.py`**

```python
"""AddonBuilder.exe wrapper.

Encapsulates the DayZ Tools Addon Builder invocation. Parses stderr for
common Enforce compile errors and produces structured results.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List

from modctl.actions.runner import run_command
from modctl.errors import ErrorCategory, ModctlError


@dataclass
class AddonBuilderResult:
    pbo_path: Path
    duration_s: float
    stdout: str
    stderr: str


def build_pbo(
    addon_builder_path: Path,
    source_dir: Path,
    output_dir: Path,
    signing_key: Path,
    prefix: str,
    pack_only: bool = True,
    project_file: Path | None = None,
    timeout_s: float = 180.0,
) -> AddonBuilderResult:
    """Invoke AddonBuilder.exe to pack + sign a mod into a PBO.

    Raises ModctlError (category=BUILD_ERROR) if the tool reports failure,
    or (category=IO_ERROR) if the expected PBO didn't appear.
    """
    cmd: List[str] = [
        str(addon_builder_path),
        str(source_dir),
        str(output_dir),
    ]
    if pack_only:
        cmd.append("-packonly")
    cmd.append(f"-sign={signing_key}")
    cmd.append(f"-prefix={prefix}")
    if project_file:
        cmd.append(f'-project={project_file}')

    out = run_command(cmd, timeout_s=timeout_s)

    if out.returncode != 0:
        raise ModctlError(
            ErrorCategory.BUILD_ERROR,
            f"AddonBuilder exited with code {out.returncode}",
            details=(out.stderr or out.stdout or "").strip(),
            suggested_fix="Review the error output above. Common causes: missing ';' in config.cpp, "
                          "unmatched braces, or referenced classes that don't exist.",
        )

    expected_pbo = output_dir / f"{prefix}.pbo"
    if not expected_pbo.exists():
        raise ModctlError(
            ErrorCategory.IO_ERROR,
            f"AddonBuilder succeeded but {expected_pbo.name} was not produced",
            details=f"Looked for: {expected_pbo}. Stdout:\n{out.stdout}",
            suggested_fix="Check the -prefix argument matches your expected PBO name, "
                          "and that the source directory contains the required files.",
        )

    return AddonBuilderResult(
        pbo_path=expected_pbo,
        duration_s=out.duration_s,
        stdout=out.stdout,
        stderr=out.stderr,
    )
```

- [ ] **Step 4: Run tests and verify all pass**

```bash
cd tools-extra/modctl && pytest tests/test_addon_builder.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/actions/addon_builder.py tools-extra/modctl/tests/test_addon_builder.py
git commit -m "feat(modctl): AddonBuilder.exe wrapper with structured errors"
```

---

## Task 8: Action layer - filesystem helpers

**Files:**
- Create: `tools-extra/modctl/modctl/actions/filesystem.py`
- Create: `tools-extra/modctl/tests/test_filesystem.py`

- [ ] **Step 1: Write the failing test `tests/test_filesystem.py`**

```python
"""Tests for filesystem action helpers."""
import pytest

from modctl.actions.filesystem import (
    copy_pbo_to_server,
    substitute_enforce_vars,
    verify_path_exists,
)
from modctl.errors import ErrorCategory, ModctlError


def test_verify_path_exists_passes_when_present(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("hi")
    verify_path_exists(f, "test file")


def test_verify_path_exists_raises_dep_error_when_missing(tmp_path):
    with pytest.raises(ModctlError) as exc_info:
        verify_path_exists(tmp_path / "does-not-exist", "DayZ Tools")
    assert exc_info.value.category == ErrorCategory.DEPENDENCY_ERROR
    assert "DayZ Tools" in exc_info.value.message


def test_copy_pbo_to_server_copies_pbo_and_bikey(tmp_path):
    pbo = tmp_path / "Foo.pbo"
    pbo.write_text("fake pbo")
    bisign = tmp_path / "Foo.pbo.Foo.bisign"
    bisign.write_text("fake sig")
    bikey = tmp_path / "Foo.bikey"
    bikey.write_text("fake public key")

    server_root = tmp_path / "server"
    server_root.mkdir()

    copy_pbo_to_server(
        pbo_path=pbo,
        bisign_path=bisign,
        bikey_path=bikey,
        server_root=server_root,
        mod_folder="@Foo",
    )

    assert (server_root / "@Foo" / "addons" / "Foo.pbo").exists()
    assert (server_root / "@Foo" / "addons" / "Foo.pbo.Foo.bisign").exists()
    assert (server_root / "keys" / "Foo.bikey").exists()


def test_substitute_enforce_vars_replaces_string_constants(tmp_path):
    source = tmp_path / "Cfg.c"
    source.write_text(
        'class BossSignalConfig {\n'
        '    static string SERVER_ID = "server_01";\n'
        '    static string BACKEND_URL = "http://127.0.0.1:6700";\n'
        '};\n'
    )

    substitute_enforce_vars(source, {
        "SERVER_ID": "reno_pvp",
        "BACKEND_URL": "http://prod.example.com",
    })

    result = source.read_text()
    assert '"reno_pvp"' in result
    assert '"http://prod.example.com"' in result
    # Unchanged vars stay intact
    assert 'BossSignalConfig' in result


def test_substitute_enforce_vars_raises_on_missing_var(tmp_path):
    source = tmp_path / "Cfg.c"
    source.write_text('static string SERVER_ID = "default";\n')

    with pytest.raises(ModctlError) as exc_info:
        substitute_enforce_vars(source, {"NONEXISTENT_VAR": "foo"})
    assert exc_info.value.category == ErrorCategory.CONFIG_ERROR
    assert "NONEXISTENT_VAR" in exc_info.value.message
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_filesystem.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.actions.filesystem'`

- [ ] **Step 3: Write `tools-extra/modctl/modctl/actions/filesystem.py`**

```python
"""Filesystem helpers - copy, verify, substitute."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict

from modctl.errors import ErrorCategory, ModctlError


def verify_path_exists(path: Path, label: str) -> None:
    """Raise DEPENDENCY_ERROR if the path doesn't exist."""
    if not path.exists():
        raise ModctlError(
            ErrorCategory.DEPENDENCY_ERROR,
            f"{label} not found at {path}",
            suggested_fix=f"Install {label} or correct the path in mods.yaml.",
        )


def copy_pbo_to_server(
    pbo_path: Path,
    bisign_path: Path,
    bikey_path: Path,
    server_root: Path,
    mod_folder: str,
) -> None:
    """Copy a signed PBO (+ .bisign + .bikey) into a DayZ Server install.

    Layout produced:
      <server_root>/<mod_folder>/addons/<pbo>
      <server_root>/<mod_folder>/addons/<bisign>
      <server_root>/keys/<bikey>
    """
    mod_dir = server_root / mod_folder / "addons"
    mod_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(pbo_path, mod_dir / pbo_path.name)
    shutil.copy2(bisign_path, mod_dir / bisign_path.name)

    keys_dir = server_root / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    shutil.copy2(bikey_path, keys_dir / bikey_path.name)


_ENFORCE_STRING_ASSIGN = re.compile(
    r'(static\s+string\s+(\w+)\s*=\s*)"[^"]*"(\s*;)',
    re.MULTILINE,
)


def substitute_enforce_vars(source_file: Path, vars: Dict[str, str]) -> None:
    """Replace `static string VAR = "..."` assignments in an Enforce .c file.

    Only rewrites variables in `vars`. Raises CONFIG_ERROR if any var in
    `vars` doesn't appear as a `static string` constant in the file.
    """
    content = source_file.read_text(encoding="utf-8")
    found: Dict[str, bool] = {k: False for k in vars}

    def _sub(match: re.Match) -> str:
        prefix = match.group(1)
        name = match.group(2)
        suffix = match.group(3)
        if name in vars:
            found[name] = True
            return f'{prefix}"{vars[name]}"{suffix}'
        return match.group(0)

    new_content = _ENFORCE_STRING_ASSIGN.sub(_sub, content)

    missing = [k for k, seen in found.items() if not seen]
    if missing:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"Enforce config vars not found in source: {', '.join(missing)}",
            details=f"File: {source_file}\nSearched for: static string <NAME> = ...",
            suggested_fix="Check mods.yaml enforce_config.vars matches actual constants in the .c file.",
        )

    source_file.write_text(new_content, encoding="utf-8")
```

- [ ] **Step 4: Run tests and verify all pass**

```bash
cd tools-extra/modctl && pytest tests/test_filesystem.py -v
```

Expected: `5 passed`

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/actions/filesystem.py tools-extra/modctl/tests/test_filesystem.py
git commit -m "feat(modctl): filesystem helpers - copy, verify, substitute enforce vars"
```

---

## Task 9: Orchestration - `modctl doctor`

**Files:**
- Create: `tools-extra/modctl/modctl/orchestration/doctor.py`
- Create: `tools-extra/modctl/tests/test_doctor.py`

- [ ] **Step 1: Write the failing test `tests/test_doctor.py`**

```python
"""Tests for the doctor orchestration."""
from pathlib import Path
from unittest.mock import patch

import pytest

from modctl.config import load_mods_yaml
from modctl.orchestration.doctor import DoctorReport, run_doctor

FIXTURES = Path(__file__).parent / "fixtures"


def test_doctor_all_green(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "value")
    # Create fake DayZ Tools + DayZ Server + signing key
    tools_path = tmp_path / "dayz-tools"
    (tools_path / "Bin" / "AddonBuilder").mkdir(parents=True)
    (tools_path / "Bin" / "AddonBuilder" / "AddonBuilder.exe").write_text("fake")
    (tools_path / "Bin" / "DSSignFile").mkdir(parents=True)
    (tools_path / "Bin" / "DSSignFile" / "DSCreateKey.exe").write_text("fake")

    server_path = tmp_path / "dayz-server"
    server_path.mkdir()

    keys_path = tmp_path / "keys"
    keys_path.mkdir()
    (keys_path / "BossSignal.biprivatekey").write_text("fake")
    (keys_path / "BossSignal.bikey").write_text("fake")

    # Write a mods.yaml pointing at these
    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tools_path}"
  dayz_server_path: "{server_path}"
  signing_keys_dir: "{keys_path}"
  output_dir: "{tmp_path / 'output'}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods:
  - name: bosssignal
    source: "../../mods/BossSignal"
    pbo_name: "BossSignal"
    mod_folder: "@BossSignal"
    depends_on: []
""")

    config = load_mods_yaml(mods_yaml)
    report = run_doctor(config)

    assert isinstance(report, DoctorReport)
    assert report.overall_ok is True
    assert all(c.ok for c in report.checks)


def test_doctor_flags_missing_addon_builder(tmp_path):
    # Tools path exists but missing AddonBuilder.exe
    tools_path = tmp_path / "dayz-tools"
    tools_path.mkdir()

    server_path = tmp_path / "dayz-server"
    server_path.mkdir()

    keys_path = tmp_path / "keys"
    keys_path.mkdir()

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tools_path}"
  dayz_server_path: "{server_path}"
  signing_keys_dir: "{keys_path}"
  output_dir: "{tmp_path / 'output'}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods: []
""")

    config = load_mods_yaml(mods_yaml)
    report = run_doctor(config)

    assert report.overall_ok is False
    failed = [c for c in report.checks if not c.ok]
    assert any("AddonBuilder" in c.name for c in failed)
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_doctor.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.orchestration.doctor'`

- [ ] **Step 3: Write `tools-extra/modctl/modctl/orchestration/doctor.py`**

```python
"""Toolchain health check orchestration."""
from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import List

from modctl.config import ModsConfig


@dataclass
class DoctorCheck:
    name: str
    ok: bool
    detail: str = ""


@dataclass
class DoctorReport:
    checks: List[DoctorCheck] = field(default_factory=list)

    @property
    def overall_ok(self) -> bool:
        return all(c.ok for c in self.checks)


def _check_path(name: str, path: Path, what: str) -> DoctorCheck:
    if path.exists():
        return DoctorCheck(name=name, ok=True, detail=f"Found at {path}")
    return DoctorCheck(name=name, ok=False, detail=f"Missing: {path} ({what})")


def run_doctor(config: ModsConfig) -> DoctorReport:
    """Verify the toolchain health: DayZ Tools, DayZ Server, signing keys."""
    report = DoctorReport()

    tools = Path(config.defaults.dayz_tools_path)
    report.checks.append(_check_path(
        "DayZ Tools installed", tools, "DayZ Tools root directory",
    ))
    report.checks.append(_check_path(
        "AddonBuilder.exe",
        tools / "Bin" / "AddonBuilder" / "AddonBuilder.exe",
        "AddonBuilder binary",
    ))
    report.checks.append(_check_path(
        "DSCreateKey.exe",
        tools / "Bin" / "DSSignFile" / "DSCreateKey.exe",
        "Key generation tool",
    ))

    server = Path(config.defaults.dayz_server_path)
    report.checks.append(_check_path(
        "DayZ Server installed", server, "DayZ Server root directory",
    ))

    keys_dir = Path(config.defaults.signing_keys_dir)
    report.checks.append(_check_path(
        "Signing keys directory", keys_dir, "Directory containing .biprivatekey files",
    ))

    # Per-mod key check (only if the directory exists)
    if keys_dir.exists():
        for mod in config.mods:
            priv = keys_dir / f"{mod.pbo_name}.biprivatekey"
            report.checks.append(_check_path(
                f"Signing key for {mod.name}",
                priv,
                f"Private key for {mod.pbo_name}",
            ))

    return report
```

- [ ] **Step 4: Run tests and verify all pass**

```bash
cd tools-extra/modctl && pytest tests/test_doctor.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/orchestration/doctor.py tools-extra/modctl/tests/test_doctor.py
git commit -m "feat(modctl): doctor orchestration - toolchain health check"
```

---

## Task 10: Orchestration - `modctl build`

**Files:**
- Create: `tools-extra/modctl/modctl/orchestration/build.py`
- Create: `tools-extra/modctl/tests/test_build.py`

- [ ] **Step 1: Write the failing test `tests/test_build.py`**

```python
"""Tests for the build orchestration."""
from pathlib import Path
from unittest.mock import patch

import pytest

from modctl.actions.addon_builder import AddonBuilderResult
from modctl.config import load_mods_yaml
from modctl.orchestration.build import BuildOrchestrator
from modctl.errors import ErrorCategory, ModctlError


def _make_config(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "secret-value")
    tools_path = tmp_path / "dayz-tools"
    (tools_path / "Bin" / "AddonBuilder").mkdir(parents=True)
    (tools_path / "Bin" / "AddonBuilder" / "AddonBuilder.exe").write_text("fake")
    (tools_path / "Bin" / "DSSignFile").mkdir(parents=True)

    keys_path = tmp_path / "keys"
    keys_path.mkdir()
    (keys_path / "FakeMod.biprivatekey").write_text("fake")
    (keys_path / "FakeMod.bikey").write_text("fake")

    mod_source = tmp_path / "fake-mod"
    (mod_source / "scripts" / "3_game").mkdir(parents=True)
    (mod_source / "config.cpp").write_text("// fake\n")
    (mod_source / "scripts" / "3_game" / "FakeConfig.c").write_text(
        'class FakeConfig {\n'
        '    static string SERVER_ID = "server_01";\n'
        '    static string BACKEND_URL = "http://127.0.0.1:6700";\n'
        '    static string SHARED_SECRET = "changeme";\n'
        '};\n'
    )

    output_dir = tmp_path / "output"

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tools_path}"
  dayz_server_path: "{tmp_path / 'dayz-server'}"
  signing_keys_dir: "{keys_path}"
  output_dir: "{output_dir}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods:
  - name: fakemod
    source: "{mod_source}"
    pbo_name: "FakeMod"
    mod_folder: "@FakeMod"
    depends_on: []
    enforce_config:
      file: "scripts/3_game/FakeConfig.c"
      vars:
        SERVER_ID: "test_server"
        BACKEND_URL: "http://test.example.com"
        SHARED_SECRET: "${{TEST_SECRET}}"
""")
    return load_mods_yaml(mods_yaml), output_dir


def test_build_runs_substitute_then_addon_builder(tmp_path, monkeypatch):
    config, output_dir = _make_config(tmp_path, monkeypatch)

    output_mod_dir = output_dir / "@FakeMod" / "addons"

    def fake_build_pbo(**kwargs):
        # Simulate AddonBuilder creating the pbo + bisign
        output_mod_dir.mkdir(parents=True, exist_ok=True)
        pbo = output_mod_dir / "FakeMod.pbo"
        pbo.write_text("fake pbo")
        (output_mod_dir / "FakeMod.pbo.FakeMod.bisign").write_text("fake sig")
        return AddonBuilderResult(
            pbo_path=pbo, duration_s=1.0, stdout="ok", stderr="",
        )

    with patch("modctl.orchestration.build.build_pbo", side_effect=fake_build_pbo):
        orch = BuildOrchestrator(config)
        result = orch.build("fakemod")

    assert result.status == "ok"
    assert result.mod == "fakemod"
    # verify enforce vars were substituted in source
    source_cfg = Path(config.mods[0].source) / "scripts/3_game/FakeConfig.c"
    content = source_cfg.read_text()
    assert '"test_server"' in content
    assert '"http://test.example.com"' in content
    assert '"secret-value"' in content


def test_build_missing_mod_raises_config_error(tmp_path, monkeypatch):
    config, _ = _make_config(tmp_path, monkeypatch)
    orch = BuildOrchestrator(config)

    with pytest.raises(ModctlError) as exc_info:
        orch.build("nonexistent")
    assert exc_info.value.category == ErrorCategory.CONFIG_ERROR
    assert "nonexistent" in exc_info.value.message


def test_build_propagates_addon_builder_error(tmp_path, monkeypatch):
    config, _ = _make_config(tmp_path, monkeypatch)

    def raise_build_error(**kwargs):
        raise ModctlError(ErrorCategory.BUILD_ERROR, "Syntax error in config.cpp")

    with patch("modctl.orchestration.build.build_pbo", side_effect=raise_build_error):
        orch = BuildOrchestrator(config)
        result = orch.build("fakemod")

    assert result.status == "error"
    assert result.failing_step == "addon_builder"
    assert any("Syntax error" in e.get("message", "") for e in result.errors)
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_build.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.orchestration.build'`

- [ ] **Step 3: Write `tools-extra/modctl/modctl/orchestration/build.py`**

```python
"""Build orchestration - compile + sign a mod into a signed PBO."""
from __future__ import annotations

import shutil
import time
from pathlib import Path
from typing import Optional

from modctl.actions.addon_builder import AddonBuilderResult, build_pbo
from modctl.actions.filesystem import substitute_enforce_vars, verify_path_exists
from modctl.config import Mod, ModsConfig
from modctl.errors import ErrorCategory, ModctlError
from modctl.output import CommandResult, StepResult


class BuildOrchestrator:
    def __init__(self, config: ModsConfig) -> None:
        self.config = config

    def _find_mod(self, name: str) -> Mod:
        for m in self.config.mods:
            if m.name == name:
                return m
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"Mod '{name}' not found in mods.yaml",
            suggested_fix=f"Check the mod name or add an entry to mods.yaml.",
        )

    def build(self, mod_name: str) -> CommandResult:
        started = time.monotonic()
        result = CommandResult(command="build", mod=mod_name, status="ok")

        try:
            mod = self._find_mod(mod_name)
        except ModctlError as e:
            result.status = "error"
            result.failing_step = "resolve_mod"
            result.errors.append(_err_dict(e))
            result.duration_s = time.monotonic() - started
            return result

        defaults = self.config.defaults

        # Step: substitute enforce vars
        step_start = time.monotonic()
        try:
            if mod.enforce_config:
                source_file = Path(mod.source) / mod.enforce_config.file
                verify_path_exists(source_file, f"Enforce config for {mod.name}")
                substitute_enforce_vars(source_file, mod.enforce_config.vars)
            result.steps.append(StepResult(
                name="substitute_enforce_vars",
                status="ok",
                duration_s=time.monotonic() - step_start,
            ))
        except ModctlError as e:
            result.steps.append(StepResult(
                name="substitute_enforce_vars",
                status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "substitute_enforce_vars"
            result.errors.append(_err_dict(e))
            result.duration_s = time.monotonic() - started
            return result

        # Step: AddonBuilder
        step_start = time.monotonic()
        try:
            addon_builder_exe = Path(defaults.dayz_tools_path) / "Bin" / "AddonBuilder" / "AddonBuilder.exe"
            output_dir = Path(defaults.output_dir) / mod.mod_folder / "addons"
            output_dir.mkdir(parents=True, exist_ok=True)
            signing_key = Path(defaults.signing_keys_dir) / f"{mod.pbo_name}.biprivatekey"

            ab_result = build_pbo(
                addon_builder_path=addon_builder_exe,
                source_dir=Path(mod.source),
                output_dir=output_dir,
                signing_key=signing_key,
                prefix=mod.pbo_name,
                pack_only=defaults.pack_only,
            )
            result.steps.append(StepResult(
                name="addon_builder",
                status="ok",
                duration_s=ab_result.duration_s,
            ))
            result.result["pbo_path"] = str(ab_result.pbo_path)
            result.result["pbo_size_kb"] = ab_result.pbo_path.stat().st_size // 1024
        except ModctlError as e:
            result.steps.append(StepResult(
                name="addon_builder",
                status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "addon_builder"
            result.errors.append(_err_dict(e))
            result.duration_s = time.monotonic() - started
            return result

        # Step: copy .bikey alongside output
        step_start = time.monotonic()
        try:
            bikey_src = Path(defaults.signing_keys_dir) / f"{mod.pbo_name}.bikey"
            bikey_dst_dir = Path(defaults.output_dir) / mod.mod_folder / "keys"
            bikey_dst_dir.mkdir(parents=True, exist_ok=True)
            if bikey_src.exists():
                shutil.copy2(bikey_src, bikey_dst_dir / bikey_src.name)
            result.steps.append(StepResult(
                name="copy_bikey",
                status="ok",
                duration_s=time.monotonic() - step_start,
            ))
            result.result["bikey_path"] = str(bikey_dst_dir / bikey_src.name)
        except OSError as e:
            result.steps.append(StepResult(
                name="copy_bikey",
                status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "copy_bikey"
            result.errors.append({
                "category": ErrorCategory.IO_ERROR.value,
                "message": str(e),
            })
            result.duration_s = time.monotonic() - started
            return result

        result.duration_s = time.monotonic() - started
        return result


def _err_dict(err: ModctlError) -> dict:
    return {
        "category": err.category.value,
        "message": err.message,
        "details": err.details,
        "suggested_fix": err.suggested_fix,
    }
```

- [ ] **Step 4: Run tests and verify all pass**

```bash
cd tools-extra/modctl && pytest tests/test_build.py -v
```

Expected: `3 passed`

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/orchestration/build.py tools-extra/modctl/tests/test_build.py
git commit -m "feat(modctl): build orchestration - substitute vars + addon_builder + bikey copy"
```

---

## Task 11: Orchestration - `modctl deploy`

**Files:**
- Create: `tools-extra/modctl/modctl/orchestration/deploy.py`
- Create: `tools-extra/modctl/tests/test_deploy.py`

- [ ] **Step 1: Write the failing test `tests/test_deploy.py`**

```python
"""Tests for deploy orchestration."""
from pathlib import Path

import pytest

from modctl.config import load_mods_yaml
from modctl.orchestration.deploy import DeployOrchestrator
from modctl.errors import ErrorCategory, ModctlError


def _write_config(tmp_path, output_mod_folder):
    """Build a config + a fake already-built PBO for testing deploy."""
    dayz_server = tmp_path / "dayz-server"
    dayz_server.mkdir()

    output_dir = tmp_path / "output"
    addons = output_dir / output_mod_folder / "addons"
    addons.mkdir(parents=True)
    (addons / "FakeMod.pbo").write_text("fake pbo")
    (addons / "FakeMod.pbo.FakeMod.bisign").write_text("fake sig")

    keys_out = output_dir / output_mod_folder / "keys"
    keys_out.mkdir(parents=True)
    (keys_out / "FakeMod.bikey").write_text("fake public key")

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tmp_path / 'tools'}"
  dayz_server_path: "{dayz_server}"
  signing_keys_dir: "{tmp_path / 'keys'}"
  output_dir: "{output_dir}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods:
  - name: fakemod
    source: "fake-mod"
    pbo_name: "FakeMod"
    mod_folder: "{output_mod_folder}"
    depends_on: []
""")
    return load_mods_yaml(mods_yaml), dayz_server, output_dir


def test_deploy_copies_pbo_bisign_and_bikey(tmp_path):
    config, server_root, _ = _write_config(tmp_path, "@FakeMod")

    orch = DeployOrchestrator(config)
    result = orch.deploy("fakemod")

    assert result.status == "ok"
    assert (server_root / "@FakeMod" / "addons" / "FakeMod.pbo").exists()
    assert (server_root / "@FakeMod" / "addons" / "FakeMod.pbo.FakeMod.bisign").exists()
    assert (server_root / "keys" / "FakeMod.bikey").exists()


def test_deploy_raises_when_pbo_not_built(tmp_path):
    # Build config but skip creating the PBO
    dayz_server = tmp_path / "dayz-server"
    dayz_server.mkdir()
    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tmp_path / 'tools'}"
  dayz_server_path: "{dayz_server}"
  signing_keys_dir: "{tmp_path / 'keys'}"
  output_dir: "{tmp_path / 'output'}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods:
  - name: fakemod
    source: "fake-mod"
    pbo_name: "FakeMod"
    mod_folder: "@FakeMod"
    depends_on: []
""")
    config = load_mods_yaml(mods_yaml)
    orch = DeployOrchestrator(config)

    result = orch.deploy("fakemod")
    assert result.status == "error"
    assert result.failing_step == "verify_pbo"
    assert any("FakeMod.pbo" in e.get("message", "") for e in result.errors)
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_deploy.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.orchestration.deploy'`

- [ ] **Step 3: Write `tools-extra/modctl/modctl/orchestration/deploy.py`**

```python
"""Deploy orchestration - copy a built PBO to the local DayZ Server."""
from __future__ import annotations

import time
from pathlib import Path

from modctl.actions.filesystem import copy_pbo_to_server, verify_path_exists
from modctl.config import Mod, ModsConfig
from modctl.errors import ErrorCategory, ModctlError
from modctl.output import CommandResult, StepResult


class DeployOrchestrator:
    def __init__(self, config: ModsConfig) -> None:
        self.config = config

    def _find_mod(self, name: str) -> Mod:
        for m in self.config.mods:
            if m.name == name:
                return m
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"Mod '{name}' not found in mods.yaml",
        )

    def deploy(self, mod_name: str) -> CommandResult:
        started = time.monotonic()
        result = CommandResult(command="deploy", mod=mod_name, status="ok")

        try:
            mod = self._find_mod(mod_name)
        except ModctlError as e:
            result.status = "error"
            result.failing_step = "resolve_mod"
            result.errors.append(_err_dict(e))
            result.duration_s = time.monotonic() - started
            return result

        defaults = self.config.defaults
        output_mod_dir = Path(defaults.output_dir) / mod.mod_folder
        pbo_path = output_mod_dir / "addons" / f"{mod.pbo_name}.pbo"
        bisign_path = output_mod_dir / "addons" / f"{mod.pbo_name}.pbo.{mod.pbo_name}.bisign"
        bikey_path = output_mod_dir / "keys" / f"{mod.pbo_name}.bikey"

        # Step: verify the artifacts exist
        step_start = time.monotonic()
        try:
            verify_path_exists(pbo_path, f"{mod.pbo_name}.pbo")
            verify_path_exists(bisign_path, f"{mod.pbo_name}.pbo.bisign")
            verify_path_exists(bikey_path, f"{mod.pbo_name}.bikey")
            result.steps.append(StepResult(
                name="verify_pbo",
                status="ok",
                duration_s=time.monotonic() - step_start,
            ))
        except ModctlError as e:
            result.steps.append(StepResult(
                name="verify_pbo",
                status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "verify_pbo"
            result.errors.append({
                "category": e.category.value,
                "message": e.message,
                "details": e.details,
                "suggested_fix": "Run `modctl build {}` first.".format(mod_name),
            })
            result.duration_s = time.monotonic() - started
            return result

        # Step: copy to DayZ Server
        step_start = time.monotonic()
        try:
            server_root = Path(defaults.dayz_server_path)
            verify_path_exists(server_root, "DayZ Server install")
            copy_pbo_to_server(
                pbo_path=pbo_path,
                bisign_path=bisign_path,
                bikey_path=bikey_path,
                server_root=server_root,
                mod_folder=mod.mod_folder,
            )
            result.steps.append(StepResult(
                name="copy_to_server",
                status="ok",
                duration_s=time.monotonic() - step_start,
            ))
            result.result["deployed_to"] = str(server_root / mod.mod_folder)
        except ModctlError as e:
            result.steps.append(StepResult(
                name="copy_to_server",
                status="error",
                duration_s=time.monotonic() - step_start,
            ))
            result.status = "error"
            result.failing_step = "copy_to_server"
            result.errors.append(_err_dict(e))
            result.duration_s = time.monotonic() - started
            return result

        result.duration_s = time.monotonic() - started
        return result


def _err_dict(err: ModctlError) -> dict:
    return {
        "category": err.category.value,
        "message": err.message,
        "details": err.details,
        "suggested_fix": err.suggested_fix,
    }
```

- [ ] **Step 4: Run tests and verify all pass**

```bash
cd tools-extra/modctl && pytest tests/test_deploy.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/orchestration/deploy.py tools-extra/modctl/tests/test_deploy.py
git commit -m "feat(modctl): deploy orchestration - copy PBO+bisign+bikey to DayZ Server"
```

---

## Task 12: Orchestration - `modctl ship`

**Files:**
- Create: `tools-extra/modctl/modctl/orchestration/ship.py`
- Create: `tools-extra/modctl/tests/test_ship.py`

- [ ] **Step 1: Write the failing test `tests/test_ship.py`**

```python
"""Tests for ship orchestration - composes build + deploy."""
from unittest.mock import patch

from modctl.output import CommandResult, StepResult


def test_ship_calls_build_then_deploy(tmp_path, monkeypatch):
    # Minimal config
    from modctl.config import load_mods_yaml

    monkeypatch.setenv("TEST_SECRET", "x")

    server = tmp_path / "server"
    server.mkdir()

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tmp_path / 'tools'}"
  dayz_server_path: "{server}"
  signing_keys_dir: "{tmp_path / 'keys'}"
  output_dir: "{tmp_path / 'out'}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods:
  - name: fakemod
    source: "fake-mod"
    pbo_name: "FakeMod"
    mod_folder: "@FakeMod"
    depends_on: []
""")

    config = load_mods_yaml(mods_yaml)

    from modctl.orchestration.ship import ShipOrchestrator

    ok_build = CommandResult(command="build", mod="fakemod", status="ok", duration_s=3.0)
    ok_build.steps.append(StepResult(name="addon_builder", status="ok", duration_s=2.9))

    ok_deploy = CommandResult(command="deploy", mod="fakemod", status="ok", duration_s=0.5)
    ok_deploy.steps.append(StepResult(name="copy_to_server", status="ok", duration_s=0.4))

    with patch("modctl.orchestration.ship.BuildOrchestrator") as MB:
        MB.return_value.build.return_value = ok_build
        with patch("modctl.orchestration.ship.DeployOrchestrator") as MD:
            MD.return_value.deploy.return_value = ok_deploy
            orch = ShipOrchestrator(config)
            result = orch.ship("fakemod")

    assert result.status == "ok"
    # Combined steps from both
    step_names = [s.name for s in result.steps]
    assert "addon_builder" in step_names
    assert "copy_to_server" in step_names


def test_ship_halts_on_build_error(tmp_path, monkeypatch):
    from modctl.config import load_mods_yaml

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tmp_path / 'tools'}"
  dayz_server_path: "{tmp_path / 'server'}"
  signing_keys_dir: "{tmp_path / 'keys'}"
  output_dir: "{tmp_path / 'out'}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods:
  - name: fakemod
    source: "fake-mod"
    pbo_name: "FakeMod"
    mod_folder: "@FakeMod"
    depends_on: []
""")
    config = load_mods_yaml(mods_yaml)

    from modctl.orchestration.ship import ShipOrchestrator

    fail_build = CommandResult(command="build", mod="fakemod", status="error", duration_s=1.0)
    fail_build.failing_step = "addon_builder"
    fail_build.errors.append({"category": "BUILD_ERROR", "message": "Syntax error"})

    with patch("modctl.orchestration.ship.BuildOrchestrator") as MB:
        MB.return_value.build.return_value = fail_build
        with patch("modctl.orchestration.ship.DeployOrchestrator") as MD:
            orch = ShipOrchestrator(config)
            result = orch.ship("fakemod")

    assert result.status == "error"
    assert result.failing_step == "addon_builder"
    MD.return_value.deploy.assert_not_called()
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_ship.py -v
```

Expected: `ModuleNotFoundError: No module named 'modctl.orchestration.ship'`

- [ ] **Step 3: Write `tools-extra/modctl/modctl/orchestration/ship.py`**

```python
"""Ship orchestration - build + deploy + (future: restart + smoke).

In Plan 1, ship = build + deploy. Server restart + in-game smoke test
land in Plan 2 with the serve command.
"""
from __future__ import annotations

import time

from modctl.config import ModsConfig
from modctl.orchestration.build import BuildOrchestrator
from modctl.orchestration.deploy import DeployOrchestrator
from modctl.output import CommandResult


class ShipOrchestrator:
    def __init__(self, config: ModsConfig) -> None:
        self.config = config

    def ship(self, mod_name: str) -> CommandResult:
        started = time.monotonic()
        result = CommandResult(command="ship", mod=mod_name, status="ok")

        # Phase 1: build
        build = BuildOrchestrator(self.config).build(mod_name)
        result.steps.extend(build.steps)
        if build.status == "error":
            result.status = "error"
            result.failing_step = build.failing_step
            result.errors.extend(build.errors)
            result.result.update(build.result)
            result.duration_s = time.monotonic() - started
            return result
        result.result.update(build.result)

        # Phase 2: deploy
        deploy = DeployOrchestrator(self.config).deploy(mod_name)
        result.steps.extend(deploy.steps)
        if deploy.status == "error":
            result.status = "error"
            result.failing_step = deploy.failing_step
            result.errors.extend(deploy.errors)
            result.result.update(deploy.result)
            result.duration_s = time.monotonic() - started
            return result
        result.result.update(deploy.result)

        result.duration_s = time.monotonic() - started
        return result
```

- [ ] **Step 4: Run tests and verify all pass**

```bash
cd tools-extra/modctl && pytest tests/test_ship.py -v
```

Expected: `2 passed`

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/orchestration/ship.py tools-extra/modctl/tests/test_ship.py
git commit -m "feat(modctl): ship orchestration (build + deploy; server restart deferred to Plan 2)"
```

---

## Task 13: CLI - wire doctor + build + deploy + ship + `--json` flag

**Files:**
- Modify: `tools-extra/modctl/modctl/cli.py`
- Create: `tools-extra/modctl/tests/test_cli.py`

- [ ] **Step 1: Write the failing test `tests/test_cli.py`**

```python
"""Tests for CLI - command wiring and exit codes."""
import json
from pathlib import Path

import pytest
from typer.testing import CliRunner

from modctl.cli import app

FIXTURES = Path(__file__).parent / "fixtures"
runner = CliRunner()


def test_version_command():
    result = runner.invoke(app, ["version"])
    assert result.exit_code == 0
    assert "modctl" in result.stdout


def test_help_shows_all_top_level_commands():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    for cmd in ["version", "doctor", "build", "deploy", "ship"]:
        assert cmd in result.stdout


def test_build_missing_mod_returns_config_error_exit_code(monkeypatch, tmp_path):
    monkeypatch.setenv("TEST_SECRET", "x")
    # Use the existing fixture
    result = runner.invoke(app, [
        "--config", str(FIXTURES / "mods.example.yaml"),
        "build", "nonexistent-mod",
    ])
    assert result.exit_code == 10  # CONFIG_ERROR


def test_build_json_mode_emits_valid_json(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "x")
    result = runner.invoke(app, [
        "--config", str(FIXTURES / "mods.example.yaml"),
        "--json",
        "build", "nonexistent-mod",
    ])
    # Even on error, JSON should be valid
    parsed = json.loads(result.stdout)
    assert parsed["command"] == "build"
    assert parsed["status"] == "error"
```

- [ ] **Step 2: Run and verify it fails**

```bash
cd tools-extra/modctl && pytest tests/test_cli.py -v
```

Expected: several failures - command not registered, `--config` flag unknown, `--json` unknown.

- [ ] **Step 3: Rewrite `tools-extra/modctl/modctl/cli.py`**

Replace the current file contents:

```python
"""modctl CLI - Typer app and command registrations."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from modctl.config import load_mods_yaml
from modctl.errors import ErrorCategory, ModctlError, exit_code_for
from modctl.output import CommandResult, OutputFormatter, StepResult

app = typer.Typer(
    name="modctl",
    help="DayZ mod development workflow CLI.",
    no_args_is_help=True,
)


# -- Global state (set by the main callback) ----------------------------
_STATE: dict = {"config_path": Path("tools-extra/modctl/mods.yaml"), "json": False}


@app.callback()
def _main(
    config: Path = typer.Option(
        Path("tools-extra/modctl/mods.yaml"),
        "--config",
        "-c",
        help="Path to mods.yaml",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit structured JSON output"
    ),
) -> None:
    _STATE["config_path"] = config
    _STATE["json"] = json_output


def _emit(result: CommandResult) -> None:
    fmt = OutputFormatter(mode="json" if _STATE["json"] else "human")
    fmt.emit(result)
    if result.status == "error" and result.errors:
        category_str = result.errors[0].get("category", "UNKNOWN")
        try:
            category = ErrorCategory(category_str)
        except ValueError:
            category = ErrorCategory.UNKNOWN
        raise typer.Exit(code=exit_code_for(category))


@app.command()
def version() -> None:
    """Print modctl version."""
    from modctl import __version__
    typer.echo(f"modctl {__version__}")


@app.command()
def doctor() -> None:
    """Verify toolchain health (DayZ Tools, DayZ Server, signing keys)."""
    from modctl.orchestration.doctor import run_doctor

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="doctor", mod=None, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    report = run_doctor(config)
    result = CommandResult(command="doctor", mod=None, status="ok" if report.overall_ok else "error")
    for check in report.checks:
        result.steps.append(StepResult(
            name=check.name,
            status="ok" if check.ok else "error",
            details=check.detail,
        ))
    if not report.overall_ok:
        result.failing_step = next(
            (c.name for c in report.checks if not c.ok),
            None,
        )
        result.errors.append({
            "category": ErrorCategory.DEPENDENCY_ERROR.value,
            "message": "Toolchain health check failed",
            "details": "One or more required components missing - see step details.",
        })
    _emit(result)


@app.command()
def build(
    mod: str = typer.Argument(..., help="Name of the mod to build"),
) -> None:
    """Compile + sign a mod into a signed PBO."""
    from modctl.orchestration.build import BuildOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="build", mod=mod, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = BuildOrchestrator(config)
    result = orch.build(mod)
    _emit(result)


@app.command()
def deploy(
    mod: str = typer.Argument(..., help="Name of the mod to deploy"),
) -> None:
    """Copy a built PBO to the local DayZ Server."""
    from modctl.orchestration.deploy import DeployOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="deploy", mod=mod, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = DeployOrchestrator(config)
    result = orch.deploy(mod)
    _emit(result)


@app.command()
def ship(
    mod: str = typer.Argument(..., help="Name of the mod to ship (build + deploy)"),
) -> None:
    """Full build + deploy cycle. Server restart + smoke test come in Plan 2."""
    from modctl.orchestration.ship import ShipOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="ship", mod=mod, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = ShipOrchestrator(config)
    result = orch.ship(mod)
    _emit(result)


def _err_to_dict(err: ModctlError) -> dict:
    return {
        "category": err.category.value,
        "message": err.message,
        "details": err.details,
        "suggested_fix": err.suggested_fix,
    }
```

- [ ] **Step 4: Run all tests**

```bash
cd tools-extra/modctl && pytest -v
```

Expected: all tests pass (count depends on earlier progress).

- [ ] **Step 5: Commit**

```bash
git add tools-extra/modctl/modctl/cli.py tools-extra/modctl/tests/test_cli.py
git commit -m "feat(modctl): CLI wiring for doctor/build/deploy/ship + --json mode"
```

---

## Task 14: Real `mods.yaml` for this repo + end-to-end dry run

**Files:**
- Create: `tools-extra/modctl/mods.yaml` (real one, not test fixture)

- [ ] **Step 1: Create the real `tools-extra/modctl/mods.yaml`**

```yaml
# modctl - source of truth for every mod in this repo.
# See docs/superpowers/specs/2026-04-23-modctl-design.md

version: 1

defaults:
  dayz_tools_path: "C:/Program Files (x86)/Steam/steamapps/common/DayZ Tools"
  dayz_server_path: "C:/Program Files (x86)/Steam/steamapps/common/DayZServer"
  signing_keys_dir: "build-pipeline/keys"
  output_dir: "output"
  pack_only: true
  pbo_prefix_matches_name: true

backends:
  bosssignal:
    kind: fastapi
    dir: "bosssignal-backend"
    tests: "pytest tests/ -q"
    compose_file: null
    health_url: "http://127.0.0.1:6700/health"

mods:
  - name: bosssignal
    source: "../../mods/BossSignal"
    pbo_name: "BossSignal"
    mod_folder: "@BossSignal"
    depends_on: [cf]
    backend: bosssignal
    enforce_config:
      file: "scripts/3_game/BossSignalConfig.c"
      vars:
        SERVER_ID: "server_01"
        BACKEND_URL: "http://127.0.0.1:6700"
        SHARED_SECRET: "${BOSSSIGNAL_SECRET}"
    watch: ["scripts/**/*.c", "config.cpp"]

  - name: trophyhunter
    source: "../../mods/TrophyHunter"
    pbo_name: "TrophyHunter"
    mod_folder: "@TrophyHunter"
    depends_on: [cf, bosssignal]
    backend: bosssignal
    enforce_config:
      file: "scripts/3_game/TrophyHunterConfig.c"
      vars:
        SERVER_ID: "server_01"
        BACKEND_URL: "http://127.0.0.1:6700"
        SHARED_SECRET: "${BOSSSIGNAL_SECRET}"
    watch: ["scripts/**/*.c", "config.cpp"]

dependencies:
  cf:
    name: "Community Framework"
    workshop_id: "1559212036"
    mod_folder: "@CommunityFramework"
    required: true
```

- [ ] **Step 2: Run `modctl doctor` against the real config**

```bash
cd ~/Dayz/dayz && BOSSSIGNAL_SECRET="$BOSSSIGNAL_SECRET" python -m modctl --config tools-extra/modctl/mods.yaml doctor
```

Expected: some checks pass (if DayZ Tools installed), some fail (if signing keys not generated yet). Exit code 70 if any dependency missing.

- [ ] **Step 3: Run `modctl doctor --json` and verify it's valid JSON**

```bash
BOSSSIGNAL_SECRET=x python -m modctl --config tools-extra/modctl/mods.yaml --json doctor | python -m json.tool
```

Expected: pretty-printed JSON with `command: "doctor"`, `steps: [...]`.

- [ ] **Step 4: Commit the real mods.yaml**

```bash
git add tools-extra/modctl/mods.yaml
git commit -m "feat(modctl): real mods.yaml for bosssignal + trophyhunter"
```

---

## Task 15: README documentation

**Files:**
- Modify: `tools-extra/modctl/README.md`

- [ ] **Step 1: Rewrite `tools-extra/modctl/README.md`**

```markdown
# modctl

DayZ mod development workflow CLI. Build, deploy, and ship mods end-to-end
from a single command. Designed for Claude Code orchestration.

See design: `docs/superpowers/specs/2026-04-23-modctl-design.md`

## Install (development)

```bash
cd tools-extra/modctl
pip install -e ".[dev]"
```

Then `modctl` is available on your PATH.

## Commands (Plan 1)

### `modctl version`
Print installed version.

### `modctl doctor`
Verify toolchain health: DayZ Tools, DayZ Server, signing keys.

```bash
modctl doctor                  # human output
modctl --json doctor           # structured output for Claude Code
```

### `modctl build <mod>`
Compile + sign a mod into a signed PBO.

```bash
modctl build bosssignal
modctl --json build bosssignal # structured output
```

Output lands at `output/<mod_folder>/addons/<PboName>.pbo`.

### `modctl deploy <mod>`
Copy a built PBO (+ .bisign + .bikey) to the local DayZ Server.

```bash
modctl deploy bosssignal
```

Requires `modctl build <mod>` to have run first.

### `modctl ship <mod>`
Full build + deploy cycle.

```bash
modctl ship bosssignal
```

Server restart + in-game smoke test come in Plan 2.

## Global flags

- `--config PATH` / `-c PATH` - point at a different `mods.yaml` (default: `tools-extra/modctl/mods.yaml`)
- `--json` - emit structured JSON output

## Configuration

Every mod is declared in `tools-extra/modctl/mods.yaml`. See that file for the
schema. Secrets (e.g. `SHARED_SECRET`) are referenced via `${ENV_VAR}`
and resolved from the environment at load time.

## Exit codes

| Code | Category |
|---|---|
| 0 | success |
| 10 | CONFIG_ERROR |
| 20 | BUILD_ERROR |
| 21 | SIGN_ERROR |
| 30 | DEPLOY_ERROR |
| 40 | SERVER_ERROR |
| 50 | TEST_ERROR |
| 60 | IO_ERROR |
| 70 | DEPENDENCY_ERROR |
| 80 | CONFLICT_ERROR |
| 90 | UNKNOWN |

Scripts + Claude Code can reason about failure type without parsing stdout.

## Testing

```bash
pytest -v
```

## What's next

Plan 2 (dev loop): `watch`, `serve`, `tail`.
Plan 3 (diagnosis): `diagnose`, `fix`, rule library.
Plan 4 (release): `release`, `docs`, `catalog`, `announce`.

See the design spec for the full roadmap.
```

- [ ] **Step 2: Commit**

```bash
git add tools-extra/modctl/README.md
git commit -m "docs(modctl): README - Plan 1 command reference"
```

---

## Task 16: End-to-end smoke test (optional, requires DayZ Tools installed)

Run only if DayZ Tools are + DayZ Server installed and `build-pipeline/sign-keygen.bat` has been run.

**Files:** none (manual validation)

- [ ] **Step 1: Generate signing key (one time, if not done)**

```bash
cd build-pipeline && cmd.exe /c sign-keygen.bat
```

Expected: `keys/BossSignal.biprivatekey` and `keys/BossSignal.bikey` appear.

- [ ] **Step 2: Run doctor against real toolchain**

```bash
BOSSSIGNAL_SECRET="$BOSSSIGNAL_SECRET" python -m modctl --config tools-extra/modctl/mods.yaml doctor
```

Expected: all checks green (or specific failures if something is missing).

- [ ] **Step 3: Run `modctl build bosssignal`**

```bash
BOSSSIGNAL_SECRET="$BOSSSIGNAL_SECRET" python -m modctl --config tools-extra/modctl/mods.yaml build bosssignal
```

Expected: a signed PBO appears at `output/@BossSignal/addons/BossSignal.pbo` within ~10 seconds.

- [ ] **Step 4: Run `modctl deploy bosssignal`**

```bash
BOSSSIGNAL_SECRET="$BOSSSIGNAL_SECRET" python -m modctl --config tools-extra/modctl/mods.yaml deploy bosssignal
```

Expected: PBO + bikey appear under `C:/Program Files (x86)/Steam/steamapps/common/DayZServer/@BossSignal/` and `.../keys/`.

- [ ] **Step 5: Run `modctl ship bosssignal` for the full cycle**

```bash
BOSSSIGNAL_SECRET="$BOSSSIGNAL_SECRET" python -m modctl --config tools-extra/modctl/mods.yaml ship bosssignal
```

Expected: both phases green in <20 seconds.

- [ ] **Step 6: Verify with `--json` output**

```bash
BOSSSIGNAL_SECRET=x python -m modctl --config tools-extra/modctl/mods.yaml --json ship bosssignal | python -m json.tool
```

Expected: valid JSON with `command: "ship"`, `status: "ok"`, `steps: [...]`, `result.pbo_path`, `result.deployed_to`.

- [ ] **Step 7: If any step fails, diagnose + fix + commit**

Likely early failures:
- Enforce syntax errors in `.c` files (`BUILD_ERROR`). Read the error, fix the file, re-run.
- Missing signing keys (`DEPENDENCY_ERROR`). Run `sign-keygen.bat`.
- DayZ Server path wrong (`DEPENDENCY_ERROR`). Correct `defaults.dayz_server_path` in `mods.yaml`.

Commit each fix separately with `fix(<mod>): <description>`.

---

## MVP acceptance verification

When Tasks 1-16 are complete, verify against spec acceptance criteria #1-3, 8-10:

- [ ] #1 `modctl build bosssignal` produces a signed PBO in <10s - **Task 16 Step 3**
- [ ] #2 `modctl deploy bosssignal` copies to local DayZ Server - **Task 16 Step 4**
- [ ] #3 `modctl ship bosssignal` runs full cycle in <60s (Plan 1 scope: build + deploy only; restart + smoke are Plan 2) - **Task 16 Step 5**
- [ ] #8 `modctl --json` output validates as JSON on every command - **Task 16 Step 6**
- [ ] #9 All MVP commands have human + json modes - **Tasks 13, 14**
- [ ] #10 Documentation exists in `tools-extra/modctl/README.md` - **Task 15**

Criteria #4 (watch), #5 (diagnose), #6 (fix), #7 (release) are out of scope for Plan 1 - they land in Plans 2, 3, 4.

---

## Self-review (completed inline)

**Spec coverage:** Plan 1 implements Sections 1, 2 (subset), 3, 4 of the spec. Specifically acceptance criteria 1-3, 8-10. Criteria 4-7 correctly deferred to Plans 2-4.

**Placeholder scan:** No "TBD", no "implement later", no references to undefined types. `CommandResult`, `StepResult`, `OutputFormatter`, `ModctlError`, `ErrorCategory`, `ModsConfig`, `Mod`, `Defaults`, `Backend`, `EnforceConfig`, `Dependency`, `run_command`, `CommandOutput`, `build_pbo`, `AddonBuilderResult`, `copy_pbo_to_server`, `substitute_enforce_vars`, `verify_path_exists`, `BuildOrchestrator`, `DeployOrchestrator`, `ShipOrchestrator`, `DoctorReport`, `DoctorCheck`, `run_doctor` - all defined in the tasks above.

**Type consistency:** `BuildOrchestrator.build(mod_name)`, `DeployOrchestrator.deploy(mod_name)`, `ShipOrchestrator.ship(mod_name)` all take `mod_name: str` and return `CommandResult`. Consistent naming, consistent signatures.

**Scope check:** ~16 tasks Ã- ~5 steps each = ~80 steps. Target <3 min per step = ~4 hours of focused work plus debugging. Appropriately sized for one plan.

**Ambiguity check:** Enforce var substitution overwrites the source file in-place (not a copy). That's explicit in `substitute_enforce_vars` signature. `ship` composes `build + deploy` and bails on first failure - explicit. Error categories are enum-backed - no string-matching fragility. Exit codes fixed in `_EXIT_CODES` dict - deterministic.

No gaps identified. Plan is implementation-ready.

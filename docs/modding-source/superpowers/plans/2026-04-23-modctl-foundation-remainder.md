# Plan: modctl Foundation - Remainder (Tasks 9-16)

> Historical implementation plan. Current repo root is `~/Dayz/dayz/`, current modctl source is `tools-extra/modctl`, and current `ship` means build + deploy only. Treat this file as implementation history, not current setup instructions.

Continuation of `docs/superpowers/plans/2026-04-23-modctl-foundation.md`. Tasks 1-8 already shipped (see git history). This file contains Tasks 9-16 formatted for ralphex autonomous execution.

## Project Context

- **Repo:** `~/Dayz/dayz/` (Windows, bash shell on win32)
- **Working dir for modctl:** `~/Dayz/dayz/tools-extra/modctl/`
- **Branch:** `bosssignal`
- **Python:** 3.11+
- **Stack:** Typer (CLI), Pydantic 2 (config), PyYAML, pytest, stdlib subprocess
- **TDD discipline:** write failing test first, verify it fails, implement minimally, verify it passes, commit

**Available modules (from Tasks 1-8, do NOT reimplement):**
- `modctl.errors.ErrorCategory` - enum with CONFIG_ERROR / BUILD_ERROR / SIGN_ERROR / DEPLOY_ERROR / SERVER_ERROR / TEST_ERROR / IO_ERROR / DEPENDENCY_ERROR / CONFLICT_ERROR / UNKNOWN
- `modctl.errors.ModctlError(category, message, details=None, suggested_fix=None)`
- `modctl.errors.exit_code_for(category) -> int`
- `modctl.config.{ModsConfig, Mod, Backend, Defaults, EnforceConfig, Dependency, load_mods_yaml}` - Pydantic models + loader with env var substitution
- `modctl.output.{CommandResult, StepResult, OutputFormatter}` - dataclasses + formatter supporting `mode="human"` or `mode="json"`, emits via stream; CommandResult fields: command, mod, status, duration_s, steps (List[StepResult]), result (Dict), warnings, errors, failing_step
- `modctl.actions.runner.{run_command, CommandOutput}` - subprocess wrapper, raises ModctlError(IO_ERROR) on timeout
- `modctl.actions.addon_builder.{build_pbo, AddonBuilderResult}` - AddonBuilder.exe wrapper
- `modctl.actions.filesystem.{verify_path_exists, copy_pbo_to_server, substitute_enforce_vars}` - filesystem helpers

**Spec reference:** `docs/superpowers/specs/2026-04-23-modctl-design.md`

**File structure (so far) - do not rearrange:**
```
tools-extra/modctl/
|-- pyproject.toml
|-- README.md                 # stub, replaced in Task 15
|-- .gitignore
|-- modctl/
|   |-- __init__.py
|   |-- __main__.py
|   |-- cli.py                # currently minimal (version cmd + callback), rewritten in Task 13
|   |-- errors.py             # Task 2
|   |-- config.py             # Task 3+4
|   |-- output.py             # Task 5
|   |-- orchestration/
|   |   `-- __init__.py
|   `-- actions/
|       |-- __init__.py
|       |-- runner.py         # Task 6
|       |-- addon_builder.py  # Task 7
|       `-- filesystem.py     # Task 8
|-- mods.yaml                 # created in Task 14
`-- tests/
    |-- __init__.py
    |-- conftest.py
    |-- fixtures/
    |   |-- mods.example.yaml
    |   |-- mock_mod/scripts/3_game/.gitkeep
    |   `-- keys/.gitkeep
    |-- test_errors.py
    |-- test_config.py
    |-- test_output.py
    |-- test_runner.py
    |-- test_addon_builder.py
    `-- test_filesystem.py
```

## Validation Commands

Run after EACH task completes to catch regressions:

- `cd ~/Dayz/dayz/tools-extra/modctl && pytest -v`

---

### Task 9: Doctor orchestration

First orchestration-layer module. Checks DayZ Tools, DayZ Server, signing keys presence.

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


def test_doctor_all_green(tmp_path, monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "value")
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

- [ ] **Step 2: Verify fails** - `cd ~/Dayz/dayz/tools-extra/modctl && pytest tests/test_doctor.py -v`. Expected: ModuleNotFoundError for `modctl.orchestration.doctor`.

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

- [ ] **Step 4: Verify pass** - `pytest tests/test_doctor.py -v`. Expected: 2 passed.

- [ ] **Step 5: Commit** - `cd ~/Dayz/dayz && git add tools-extra/modctl/modctl/orchestration/doctor.py tools-extra/modctl/tests/test_doctor.py && git commit -m "feat(modctl): doctor orchestration - toolchain health check"`

---

### Task 10: Build orchestration

Composes substitute_enforce_vars + addon_builder + bikey copy into one flow. Returns CommandResult.

**Files:**
- Create: `tools-extra/modctl/modctl/orchestration/build.py`
- Create: `tools-extra/modctl/tests/test_build.py`

- [ ] **Step 1: Write failing test `tests/test_build.py`**

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

- [ ] **Step 2: Verify fails** - `pytest tests/test_build.py -v`. Expected: ModuleNotFoundError.

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

- [ ] **Step 4: Verify pass** - `pytest tests/test_build.py -v`. Expected: 3 passed.

- [ ] **Step 5: Commit** - `git add tools-extra/modctl/modctl/orchestration/build.py tools-extra/modctl/tests/test_build.py && git commit -m "feat(modctl): build orchestration - substitute vars + addon_builder + bikey copy"`

---

### Task 11: Deploy orchestration

Verifies built PBO exists, then copies to local DayZ Server install.

**Files:**
- Create: `tools-extra/modctl/modctl/orchestration/deploy.py`
- Create: `tools-extra/modctl/tests/test_deploy.py`

- [ ] **Step 1: Write failing test `tests/test_deploy.py`**

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

- [ ] **Step 2: Verify fails** - `pytest tests/test_deploy.py -v`. Expected: ModuleNotFoundError.

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

- [ ] **Step 4: Verify pass** - `pytest tests/test_deploy.py -v`. Expected: 2 passed.

- [ ] **Step 5: Commit** - `git add tools-extra/modctl/modctl/orchestration/deploy.py tools-extra/modctl/tests/test_deploy.py && git commit -m "feat(modctl): deploy orchestration - copy PBO+bisign+bikey to DayZ Server"`

---

### Task 12: Ship orchestration

Composes build + deploy into one flow. Halts on first failure.

**Files:**
- Create: `tools-extra/modctl/modctl/orchestration/ship.py`
- Create: `tools-extra/modctl/tests/test_ship.py`

- [ ] **Step 1: Write failing test `tests/test_ship.py`**

```python
"""Tests for ship orchestration - composes build + deploy."""
from unittest.mock import patch

from modctl.output import CommandResult, StepResult


def test_ship_calls_build_then_deploy(tmp_path, monkeypatch):
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

- [ ] **Step 2: Verify fails** - `pytest tests/test_ship.py -v`. Expected: ModuleNotFoundError.

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

- [ ] **Step 4: Verify pass** - `pytest tests/test_ship.py -v`. Expected: 2 passed.

- [ ] **Step 5: Commit** - `git add tools-extra/modctl/modctl/orchestration/ship.py tools-extra/modctl/tests/test_ship.py && git commit -m "feat(modctl): ship orchestration (build + deploy; server restart deferred to Plan 2)"`

---

### Task 13: CLI wiring for doctor/build/deploy/ship + --json + --config

Rewrites the minimal cli.py stub from Task 1 with full command set + global flags.

**Files:**
- Modify: `tools-extra/modctl/modctl/cli.py` (replace the existing minimal file)
- Create: `tools-extra/modctl/tests/test_cli.py`

- [ ] **Step 1: Write failing test `tests/test_cli.py`**

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
    result = runner.invoke(app, [
        "--config", str(FIXTURES / "mods.example.yaml"),
        "build", "nonexistent-mod",
    ])
    assert result.exit_code == 10


def test_build_json_mode_emits_valid_json(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "x")
    result = runner.invoke(app, [
        "--config", str(FIXTURES / "mods.example.yaml"),
        "--json",
        "build", "nonexistent-mod",
    ])
    parsed = json.loads(result.stdout)
    assert parsed["command"] == "build"
    assert parsed["status"] == "error"
```

- [ ] **Step 2: Verify fails** - `pytest tests/test_cli.py -v`. Expected: several failures.

- [ ] **Step 3: REPLACE contents of `tools-extra/modctl/modctl/cli.py`**

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

- [ ] **Step 4: Verify pass** - `pytest -v` (ALL tests). Expected: all pass.

- [ ] **Step 5: Commit** - `git add tools-extra/modctl/modctl/cli.py tools-extra/modctl/tests/test_cli.py && git commit -m "feat(modctl): CLI wiring for doctor/build/deploy/ship + --json mode"`

---

### Task 14: Real mods.yaml for this repo

Create the actual config file modctl reads in production (not a test fixture).

**Files:**
- Create: `tools-extra/modctl/mods.yaml`

- [ ] **Step 1: Create `tools-extra/modctl/mods.yaml`**

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

- [ ] **Step 2: Verify it loads** - `cd ~/Dayz/dayz && BOSSSIGNAL_SECRET="$BOSSSIGNAL_SECRET" python -c "from modctl.config import load_mods_yaml; c = load_mods_yaml('tools-extra/modctl/mods.yaml'); print(f'Loaded {len(c.mods)} mods')"`. Expected: `Loaded 2 mods`.

- [ ] **Step 3: Commit** - `git add tools-extra/modctl/mods.yaml && git commit -m "feat(modctl): real mods.yaml for bosssignal + trophyhunter"`

---

### Task 15: README documentation

Replace the stub README from Task 1 with full Plan 1 command reference.

**Files:**
- Modify: `tools-extra/modctl/README.md`

- [ ] **Step 1: Replace `tools-extra/modctl/README.md` with this content**

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

- [ ] **Step 2: Commit** - `git add tools-extra/modctl/README.md && git commit -m "docs(modctl): README - Plan 1 command reference"`

---

### Task 16: End-to-end smoke test (manual - requires DayZ Tools installed)

**Not automated.** Skip if DayZ Tools / DayZ Server / signing keys aren't set up yet. the developer can run this manually later.

- [ ] **Step 1: Verify mods.yaml paths are correct for the  rig** (check `dayz_tools_path` and `dayz_server_path` point to actual Steam install locations)

- [ ] **Step 2: Generate signing keys** (if not already done) - `cd ~/Dayz/dayz/build-pipeline && cmd.exe /c sign-keygen.bat`

- [ ] **Step 3: Run `modctl doctor`** - `cd ~/Dayz/dayz && BOSSSIGNAL_SECRET="$BOSSSIGNAL_SECRET" python -m modctl --config tools-extra/modctl/mods.yaml doctor`

- [ ] **Step 4: Commit this task's checkbox completion only if all prior steps succeeded manually** - otherwise leave unchecked and flag as "pending DayZ Tools install."

If DayZ Tools aren't installed yet, skip all steps and leave this task's boxes unchecked. Ralphex will then mark the plan "complete with deferred task" - that's the expected outcome for Task 16 pre-DayZ-Tools-install.

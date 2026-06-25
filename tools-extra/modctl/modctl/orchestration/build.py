"""Build orchestration — compile + sign a mod into a signed PBO."""
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
        # Missing mod is a config-side programmer error — propagate, don't swallow.
        mod = self._find_mod(mod_name)
        result = CommandResult(command="build", mod=mod_name, status="ok")

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
            # AddonBuilder.exe requires ABSOLUTE paths for source, output, and signing key.
            # Relative paths silently fail (exit 0 + no output file).
            addon_builder_exe = Path(defaults.dayz_tools_path) / "Bin" / "AddonBuilder" / "AddonBuilder.exe"
            output_dir = (Path(defaults.output_dir) / mod.mod_folder / "addons").resolve()
            output_dir.mkdir(parents=True, exist_ok=True)
            source_dir = Path(mod.source).resolve()
            signing_key = (Path(defaults.signing_keys_dir) / f"{mod.pbo_name}.biprivatekey").resolve()

            ab_result = build_pbo(
                addon_builder_path=addon_builder_exe,
                source_dir=source_dir,
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

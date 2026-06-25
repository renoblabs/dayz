"""Deploy orchestration — copy a built PBO to the local DayZ Server."""
from __future__ import annotations

import time
from pathlib import Path

from modctl.actions.filesystem import copy_pbo_to_server, sync_mod_to_client_workshop, verify_path_exists
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
        # Missing mod is a config-side programmer error — propagate, don't swallow.
        mod = self._find_mod(mod_name)
        result = CommandResult(command="deploy", mod=mod_name, status="ok")

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

        if defaults.deploy_client_workshop:
            step_start = time.monotonic()
            try:
                if not defaults.dayz_client_path:
                    raise ModctlError(
                        ErrorCategory.CONFIG_ERROR,
                        "deploy_client_workshop is enabled but dayz_client_path is not set",
                        suggested_fix="Set defaults.dayz_client_path in mods.yaml or disable deploy_client_workshop.",
                    )
                client_root = Path(defaults.dayz_client_path)
                verify_path_exists(client_root, "DayZ client install")
                workshop_path = sync_mod_to_client_workshop(
                    server_mod_root=server_root / mod.mod_folder,
                    client_root=client_root,
                    mod_folder=mod.mod_folder,
                    display_name=mod.mod_folder.lstrip("@"),
                )
                result.steps.append(StepResult(
                    name="sync_client_workshop",
                    status="ok",
                    duration_s=time.monotonic() - step_start,
                ))
                result.result["client_workshop_path"] = str(workshop_path)
            except ModctlError as e:
                result.steps.append(StepResult(
                    name="sync_client_workshop",
                    status="error",
                    duration_s=time.monotonic() - step_start,
                ))
                result.status = "error"
                result.failing_step = "sync_client_workshop"
                result.errors.append(_err_dict(e))
                result.duration_s = time.monotonic() - started
                return result
            except OSError as e:
                result.steps.append(StepResult(
                    name="sync_client_workshop",
                    status="error",
                    duration_s=time.monotonic() - step_start,
                ))
                result.status = "error"
                result.failing_step = "sync_client_workshop"
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

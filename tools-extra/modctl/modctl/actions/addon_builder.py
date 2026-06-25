"""PBO build + sign using DayZ Tools.

Uses FileBank (`Bin/PboUtils/FileBank.exe`) + DSSignFile
(`Bin/DsUtils/DSSignFile.exe`) rather than AddonBuilder.exe. Reasons:

1. FileBank has no P: drive requirement (AddonBuilder hangs without one).
2. Splitting pack + sign makes each step's errors easier to diagnose.
3. Pure CLI, fully scriptable, no GUI fallback.

Tradeoff: FileBank names the output by source directory (e.g. source
`bosssignal-mod/` -> `bosssignal-mod.pbo`). We rename to `<prefix>.pbo`
post-pack to match the mod's declared pbo_name.
"""
from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import List, Optional

from modctl.actions.runner import run_command
from modctl.errors import ErrorCategory, ModctlError


@dataclass
class AddonBuilderResult:
    pbo_path: Path
    duration_s: float
    stdout: str
    stderr: str


def _file_bank_exe(dayz_tools_root: Path) -> Path:
    return dayz_tools_root / "Bin" / "PboUtils" / "FileBank.exe"


def _dssign_exe(dayz_tools_root: Path) -> Path:
    return dayz_tools_root / "Bin" / "DsUtils" / "DSSignFile.exe"


def build_pbo(
    addon_builder_path: Path,
    source_dir: Path,
    output_dir: Path,
    signing_key: Path,
    prefix: str,
    pack_only: bool = True,
    project_file: Optional[Path] = None,
    timeout_s: float = 180.0,
) -> AddonBuilderResult:
    """Pack + sign a mod into a signed PBO.

    `addon_builder_path` is kept in the signature for backward compat --
    the caller typically passes `<tools>/Bin/AddonBuilder/AddonBuilder.exe`.
    We walk up to the DayZ Tools root and invoke FileBank + DSSignFile.

    Raises ModctlError (BUILD_ERROR) if FileBank fails.
    Raises ModctlError (SIGN_ERROR) if DSSignFile fails.
    Raises ModctlError (IO_ERROR) if the expected PBO didn't appear.
    """
    # Walk up from AddonBuilder.exe to DayZ Tools root:
    #   .../Bin/AddonBuilder/AddonBuilder.exe
    tools_root = addon_builder_path.parent.parent.parent
    file_bank = _file_bank_exe(tools_root)
    dssign = _dssign_exe(tools_root)

    if not file_bank.exists():
        raise ModctlError(
            ErrorCategory.DEPENDENCY_ERROR,
            f"FileBank.exe not found at {file_bank}",
            suggested_fix="Install DayZ Tools (the PboUtils subfolder contains FileBank.exe).",
        )
    if not dssign.exists():
        raise ModctlError(
            ErrorCategory.DEPENDENCY_ERROR,
            f"DSSignFile.exe not found at {dssign}",
            suggested_fix="Install DayZ Tools (the DsUtils subfolder contains DSSignFile.exe).",
        )

    output_dir.mkdir(parents=True, exist_ok=True)

    # -- Pack with FileBank --
    # Usage: FileBank [options] <source>   (options before source path)
    cmd: List[str] = [
        str(file_bank),
        "-property", f"prefix={prefix}",
        "-dst", str(output_dir),
        str(source_dir),
    ]
    out = run_command(cmd, timeout_s=timeout_s)

    if out.returncode != 0:
        raise ModctlError(
            ErrorCategory.BUILD_ERROR,
            f"FileBank exited with code {out.returncode}",
            details=(out.stderr or out.stdout or "").strip(),
            suggested_fix="Review the error above. Common causes: source dir doesn't exist, "
                          "prefix conflict with existing .pbo, missing config.cpp in source.",
        )

    # FileBank produces `<output_dir>/<source_basename>.pbo`. Rename to
    # `<prefix>.pbo` to match the mod's declared pbo_name.
    source_basename = source_dir.name
    packed_pbo = output_dir / f"{source_basename}.pbo"
    expected_pbo = output_dir / f"{prefix}.pbo"

    if not packed_pbo.exists():
        if expected_pbo.exists():
            pass  # Already has the right name (some FileBank versions)
        else:
            raise ModctlError(
                ErrorCategory.IO_ERROR,
                f"FileBank succeeded but no .pbo was produced in {output_dir}",
                details=f"Looked for: {packed_pbo.name} or {expected_pbo.name}. Stdout:\n{out.stdout}",
            )
    elif packed_pbo != expected_pbo:
        if expected_pbo.exists():
            expected_pbo.unlink()
        packed_pbo.rename(expected_pbo)

    # -- Sign with DSSignFile --
    sign_cmd: List[str] = [str(dssign), str(signing_key), str(expected_pbo)]
    sign_out = run_command(sign_cmd, timeout_s=60.0)
    if sign_out.returncode != 0:
        raise ModctlError(
            ErrorCategory.SIGN_ERROR,
            f"DSSignFile exited with code {sign_out.returncode}",
            details=(sign_out.stderr or sign_out.stdout or "").strip(),
            suggested_fix="Verify the signing key path is correct and the .biprivatekey exists.",
        )

    return AddonBuilderResult(
        pbo_path=expected_pbo,
        duration_s=out.duration_s + sign_out.duration_s,
        stdout=out.stdout + "\n" + sign_out.stdout,
        stderr=out.stderr + "\n" + sign_out.stderr,
    )

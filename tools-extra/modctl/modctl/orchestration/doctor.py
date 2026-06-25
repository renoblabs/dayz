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
        tools / "Bin" / "DsUtils" / "DSCreateKey.exe",
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

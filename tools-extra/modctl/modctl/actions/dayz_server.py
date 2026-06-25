"""DayZ Server subprocess + RPT log helpers.

Windows-focused. Server is DayZServer_x64.exe. RPT logs rotate per run, the
newest file in the profile directory is the live one.
"""
from __future__ import annotations

import subprocess
from pathlib import Path
from typing import List, Optional


def build_server_command(
    server_exe: Path,
    mods: List[str],
    config_file: str,
    port: int,
    profile_dir: str,
    extra_params: Optional[List[str]] = None,
) -> List[str]:
    """Assemble DayZServer_x64.exe command line with typical flags.

    The `-mod=` flag takes a semicolon-separated list of mod folder names
    (e.g. `-mod=@CommunityFramework;@BossSignal;@TrophyHunter`). Passing an
    empty list produces `-mod=` (valid — server runs vanilla).
    """
    cmd: List[str] = [str(server_exe)]
    cmd.append(f"-mod={';'.join(mods)}")
    cmd.append(f"-config={config_file}")
    cmd.append(f"-port={port}")
    cmd.append(f"-profiles={profile_dir}")
    if extra_params:
        cmd.extend(extra_params)
    return cmd


def start_server(
    server_exe: Path,
    mods: List[str],
    config_file: str,
    port: int,
    profile_dir: str,
    extra_params: Optional[List[str]] = None,
    cwd: Optional[Path] = None,
) -> subprocess.Popen:
    """Spawn DayZ Server as a background process. Returns the Popen handle."""
    cmd = build_server_command(
        server_exe=server_exe,
        mods=mods,
        config_file=config_file,
        port=port,
        profile_dir=profile_dir,
        extra_params=extra_params,
    )
    # Run without capturing — serve orchestration streams via its own threads.
    return subprocess.Popen(
        cmd,
        cwd=cwd or server_exe.parent,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,  # line-buffered
    )


def stop_server(proc: subprocess.Popen, timeout_s: float = 10.0) -> None:
    """Terminate a running DayZ Server. Escalates to kill on timeout."""
    proc.terminate()
    try:
        proc.wait(timeout=timeout_s)
    except subprocess.TimeoutExpired:
        proc.kill()
        proc.wait(timeout=5.0)


def find_rpt_log(profile_dir: Path) -> Optional[Path]:
    """Return the newest .RPT file in profile_dir, or None if absent.

    DayZ Server rotates RPT logs per run; the most-recently modified one
    is the active session's log.
    """
    if not profile_dir.exists() or not profile_dir.is_dir():
        return None
    rpts = sorted(
        profile_dir.glob("*.RPT"),
        key=lambda p: p.stat().st_mtime,
        reverse=True,
    )
    return rpts[0] if rpts else None

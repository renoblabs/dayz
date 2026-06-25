"""Tests for DayZ Server action wrapper."""
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from modctl.actions.dayz_server import (
    build_server_command,
    find_rpt_log,
    start_server,
    stop_server,
)


def test_build_server_command_includes_mods_and_port():
    server_exe = Path("C:/DayZServer/DayZServer_x64.exe")
    cmd = build_server_command(
        server_exe=server_exe,
        mods=["@CommunityFramework", "@BossSignal"],
        config_file="serverDZ.cfg",
        port=2302,
        profile_dir="profiles",
    )
    assert str(server_exe) in cmd[0]
    joined = " ".join(cmd)
    assert "-mod=@CommunityFramework;@BossSignal" in joined
    assert "-config=serverDZ.cfg" in joined
    assert "-port=2302" in joined
    assert "-profiles=profiles" in joined


def test_build_server_command_with_extra_params():
    cmd = build_server_command(
        server_exe=Path("/tmp/DayZServer.exe"),
        mods=[],
        config_file="serverDZ.cfg",
        port=2302,
        profile_dir="profiles",
        extra_params=["-doLogs", "-adminLog"],
    )
    assert "-doLogs" in cmd
    assert "-adminLog" in cmd


def test_start_server_returns_popen():
    with patch("modctl.actions.dayz_server.subprocess.Popen") as MockPopen:
        fake_proc = MagicMock()
        fake_proc.pid = 12345
        MockPopen.return_value = fake_proc

        proc = start_server(
            server_exe=Path("/tmp/DayZServer.exe"),
            mods=["@BossSignal"],
            config_file="serverDZ.cfg",
            port=2302,
            profile_dir="profiles",
        )

        assert proc.pid == 12345
        MockPopen.assert_called_once()


def test_stop_server_calls_terminate_and_waits():
    fake_proc = MagicMock()
    fake_proc.wait.return_value = 0

    stop_server(fake_proc, timeout_s=5.0)

    fake_proc.terminate.assert_called_once()
    fake_proc.wait.assert_called_once_with(timeout=5.0)


def test_stop_server_force_kills_on_timeout():
    import subprocess
    fake_proc = MagicMock()
    fake_proc.wait.side_effect = [subprocess.TimeoutExpired(cmd="x", timeout=5.0), 0]

    stop_server(fake_proc, timeout_s=5.0)

    fake_proc.terminate.assert_called_once()
    fake_proc.kill.assert_called_once()


def test_find_rpt_log_returns_newest_rpt(tmp_path):
    import time
    (tmp_path / "DayZServer_x64_2025-01-01_12-00-00.RPT").write_text("old")
    time.sleep(0.01)
    newest = tmp_path / "DayZServer_x64_2026-04-23_18-00-00.RPT"
    newest.write_text("newest")

    result = find_rpt_log(tmp_path)
    assert result == newest


def test_find_rpt_log_returns_none_when_no_rpt(tmp_path):
    (tmp_path / "not-an-rpt.txt").write_text("x")
    result = find_rpt_log(tmp_path)
    assert result is None


def test_find_rpt_log_returns_none_when_dir_missing(tmp_path):
    result = find_rpt_log(tmp_path / "does-not-exist")
    assert result is None

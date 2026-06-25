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


def _make_tools_root(tmp_path: Path) -> Path:
    tools_root = tmp_path / "tools"
    (tools_root / "Bin" / "PboUtils").mkdir(parents=True, exist_ok=True)
    (tools_root / "Bin" / "DsUtils").mkdir(parents=True, exist_ok=True)
    (tools_root / "Bin" / "AddonBuilder").mkdir(parents=True, exist_ok=True)
    (tools_root / "Bin" / "PboUtils" / "FileBank.exe").write_text("fake")
    (tools_root / "Bin" / "DsUtils" / "DSSignFile.exe").write_text("fake")
    addon_builder = tools_root / "Bin" / "AddonBuilder" / "AddonBuilder.exe"
    addon_builder.write_text("fake")
    return addon_builder


def test_build_pbo_success(tmp_path):
    addon_builder_path = _make_tools_root(tmp_path)
    output_dir = tmp_path / "addons"
    output_dir.mkdir()
    (output_dir / "FakeMod.pbo").write_text("fake pbo content")

    with patch("modctl.actions.addon_builder.run_command") as mock_run:
        mock_run.return_value = _fake_cmd_output(returncode=0, stdout="Packed successfully.")

        result = build_pbo(
            addon_builder_path=addon_builder_path,
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
    addon_builder_path = _make_tools_root(tmp_path)
    with patch("modctl.actions.addon_builder.run_command") as mock_run:
        mock_run.return_value = _fake_cmd_output(
            returncode=1,
            stderr="[ERROR] Missing ';' at line 51 in config.cpp",
        )

        with pytest.raises(ModctlError) as exc_info:
            build_pbo(
                addon_builder_path=addon_builder_path,
                source_dir=tmp_path / "mod_source",
                output_dir=tmp_path / "out",
                signing_key=tmp_path / "key.biprivatekey",
                prefix="FakeMod",
                pack_only=True,
            )

    assert exc_info.value.category == ErrorCategory.BUILD_ERROR
    assert "Missing" in exc_info.value.details


def test_build_pbo_missing_output_raises_io_error(tmp_path):
    addon_builder_path = _make_tools_root(tmp_path)
    output_dir = tmp_path / "addons"
    output_dir.mkdir()

    with patch("modctl.actions.addon_builder.run_command") as mock_run:
        mock_run.return_value = _fake_cmd_output(returncode=0, stdout="OK")

        with pytest.raises(ModctlError) as exc_info:
            build_pbo(
                addon_builder_path=addon_builder_path,
                source_dir=tmp_path / "mod_source",
                output_dir=output_dir,
                signing_key=tmp_path / "key.biprivatekey",
                prefix="FakeMod",
                pack_only=True,
            )

    assert exc_info.value.category == ErrorCategory.IO_ERROR
    assert "no .pbo was produced" in exc_info.value.message

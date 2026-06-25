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
        '    static string BACKEND_URL = "http://127.0.0.1:8080";\n'
        '    static string SHARED_SECRET = "changeme";\n'
        '};\n'
    )

    output_dir = tmp_path / "output"

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{tools_path.as_posix()}"
  dayz_server_path: "{(tmp_path / 'dayz-server').as_posix()}"
  signing_keys_dir: "{keys_path.as_posix()}"
  output_dir: "{output_dir.as_posix()}"
  pack_only: true
  pbo_prefix_matches_name: true
backends: {{}}
mods:
  - name: fakemod
    source: "{mod_source.as_posix()}"
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

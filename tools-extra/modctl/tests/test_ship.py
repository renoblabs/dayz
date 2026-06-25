"""Tests for ship orchestration — composes build + deploy."""
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
  dayz_tools_path: "{(tmp_path / 'tools').as_posix()}"
  dayz_server_path: "{server.as_posix()}"
  signing_keys_dir: "{(tmp_path / 'keys').as_posix()}"
  output_dir: "{(tmp_path / 'out').as_posix()}"
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
  dayz_tools_path: "{(tmp_path / 'tools').as_posix()}"
  dayz_server_path: "{(tmp_path / 'server').as_posix()}"
  signing_keys_dir: "{(tmp_path / 'keys').as_posix()}"
  output_dir: "{(tmp_path / 'out').as_posix()}"
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

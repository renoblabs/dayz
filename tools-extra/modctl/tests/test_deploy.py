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
  dayz_tools_path: "{(tmp_path / 'tools').as_posix()}"
  dayz_server_path: "{dayz_server.as_posix()}"
  signing_keys_dir: "{(tmp_path / 'keys').as_posix()}"
  output_dir: "{output_dir.as_posix()}"
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
    assert (server_root / "@FakeMod" / "keys" / "FakeMod.bikey").exists()
    assert (server_root / "keys" / "FakeMod.bikey").exists()


def test_deploy_can_sync_client_workshop_entry(tmp_path):
    dayz_server = tmp_path / "dayz-server"
    dayz_server.mkdir()
    dayz_client = tmp_path / "dayz-client"
    dayz_client.mkdir()

    output_dir = tmp_path / "output"
    addons = output_dir / "@FakeMod" / "addons"
    addons.mkdir(parents=True)
    (addons / "FakeMod.pbo").write_text("fake pbo")
    (addons / "FakeMod.pbo.FakeMod.bisign").write_text("fake sig")

    keys_out = output_dir / "@FakeMod" / "keys"
    keys_out.mkdir(parents=True)
    (keys_out / "FakeMod.bikey").write_text("fake public key")

    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{(tmp_path / 'tools').as_posix()}"
  dayz_server_path: "{dayz_server.as_posix()}"
  dayz_client_path: "{dayz_client.as_posix()}"
  signing_keys_dir: "{(tmp_path / 'keys').as_posix()}"
  output_dir: "{output_dir.as_posix()}"
  deploy_client_workshop: true
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

    result = DeployOrchestrator(config).deploy("fakemod")

    workshop_mod = dayz_client / "!Workshop" / "@FakeMod"
    assert result.status == "ok"
    assert (workshop_mod / "addons" / "FakeMod.pbo").exists()
    assert (workshop_mod / "keys" / "FakeMod.bikey").exists()
    assert (workshop_mod / "meta.cpp").read_text() == (
        "protocol = 1;\n"
        "publishedid = 0;\n"
        'name = "FakeMod";\n'
        "timestamp = 0;\n"
    )


def test_deploy_raises_when_pbo_not_built(tmp_path):
    dayz_server = tmp_path / "dayz-server"
    dayz_server.mkdir()
    mods_yaml = tmp_path / "mods.yaml"
    mods_yaml.write_text(f"""
version: 1
defaults:
  dayz_tools_path: "{(tmp_path / 'tools').as_posix()}"
  dayz_server_path: "{dayz_server.as_posix()}"
  signing_keys_dir: "{(tmp_path / 'keys').as_posix()}"
  output_dir: "{(tmp_path / 'output').as_posix()}"
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

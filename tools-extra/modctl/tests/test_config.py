"""Tests for mods.yaml loading and Pydantic validation."""
from pathlib import Path

import pytest

from modctl.config import load_mods_yaml, ModsConfig

FIXTURES = Path(__file__).parent / "fixtures"


def test_load_valid_mods_yaml_returns_mods_config(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "dummy-secret")
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    assert isinstance(config, ModsConfig)
    assert config.version == 1


def test_mods_config_has_bosssignal_mod(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "dummy-secret")
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    names = [m.name for m in config.mods]
    assert "bosssignal" in names


def test_mod_has_pbo_name_and_source(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "dummy-secret")
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    bs = next(m for m in config.mods if m.name == "bosssignal")
    assert bs.pbo_name == "BossSignal"
    assert bs.source == "bosssignal-mod"


def test_mod_backend_reference_resolvable(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "dummy-secret")
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    bs = next(m for m in config.mods if m.name == "bosssignal")
    assert bs.backend == "bosssignal"
    assert "bosssignal" in config.backends
    assert config.backends["bosssignal"].kind == "fastapi"


def test_dependencies_block_parses(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "dummy-secret")
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    assert "cf" in config.dependencies
    assert config.dependencies["cf"].workshop_id == "1559212036"


def test_env_var_substitution_resolves_shared_secret(monkeypatch):
    monkeypatch.setenv("TEST_SECRET", "actual-secret-value")
    config = load_mods_yaml(FIXTURES / "mods.example.yaml")
    bs = next(m for m in config.mods if m.name == "bosssignal")
    assert bs.enforce_config.vars["SHARED_SECRET"] == "actual-secret-value"


def test_env_var_substitution_fails_loud_on_missing(monkeypatch):
    monkeypatch.delenv("TEST_SECRET", raising=False)
    with pytest.raises(Exception) as exc_info:
        load_mods_yaml(FIXTURES / "mods.example.yaml")
    assert "TEST_SECRET" in str(exc_info.value)

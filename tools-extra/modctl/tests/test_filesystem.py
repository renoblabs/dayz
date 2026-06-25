"""Tests for filesystem action helpers."""
import pytest

from modctl.actions.filesystem import (
    copy_pbo_to_server,
    substitute_enforce_vars,
    verify_path_exists,
)
from modctl.errors import ErrorCategory, ModctlError


def test_verify_path_exists_passes_when_present(tmp_path):
    f = tmp_path / "hello.txt"
    f.write_text("hi")
    verify_path_exists(f, "test file")


def test_verify_path_exists_raises_dep_error_when_missing(tmp_path):
    with pytest.raises(ModctlError) as exc_info:
        verify_path_exists(tmp_path / "does-not-exist", "DayZ Tools")
    assert exc_info.value.category == ErrorCategory.DEPENDENCY_ERROR
    assert "DayZ Tools" in exc_info.value.message


def test_copy_pbo_to_server_copies_pbo_and_bikey(tmp_path):
    pbo = tmp_path / "Foo.pbo"
    pbo.write_text("fake pbo")
    bisign = tmp_path / "Foo.pbo.Foo.bisign"
    bisign.write_text("fake sig")
    bikey = tmp_path / "Foo.bikey"
    bikey.write_text("fake public key")

    server_root = tmp_path / "server"
    server_root.mkdir()

    copy_pbo_to_server(
        pbo_path=pbo,
        bisign_path=bisign,
        bikey_path=bikey,
        server_root=server_root,
        mod_folder="@Foo",
    )

    assert (server_root / "@Foo" / "addons" / "Foo.pbo").exists()
    assert (server_root / "@Foo" / "addons" / "Foo.pbo.Foo.bisign").exists()
    assert (server_root / "keys" / "Foo.bikey").exists()


def test_substitute_enforce_vars_replaces_string_constants(tmp_path):
    source = tmp_path / "Cfg.c"
    source.write_text(
        'class BossSignalConfig {\n'
        '    static string SERVER_ID = "server_01";\n'
        '    static string BACKEND_URL = "http://127.0.0.1:8080";\n'
        '};\n'
    )

    substitute_enforce_vars(source, {
        "SERVER_ID": "reno_pvp",
        "BACKEND_URL": "http://prod.example.com",
    })

    result = source.read_text()
    assert '"reno_pvp"' in result
    assert '"http://prod.example.com"' in result
    assert 'BossSignalConfig' in result


def test_substitute_enforce_vars_raises_on_missing_var(tmp_path):
    source = tmp_path / "Cfg.c"
    source.write_text('static string SERVER_ID = "default";\n')

    with pytest.raises(ModctlError) as exc_info:
        substitute_enforce_vars(source, {"NONEXISTENT_VAR": "foo"})
    assert exc_info.value.category == ErrorCategory.CONFIG_ERROR
    assert "NONEXISTENT_VAR" in exc_info.value.message

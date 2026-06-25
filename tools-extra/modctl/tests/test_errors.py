"""Tests for error categories and ModctlError."""
import pytest

from modctl.errors import ErrorCategory, ModctlError, exit_code_for


def test_error_categories_have_expected_exit_codes():
    assert exit_code_for(ErrorCategory.CONFIG_ERROR) == 10
    assert exit_code_for(ErrorCategory.BUILD_ERROR) == 20
    assert exit_code_for(ErrorCategory.SIGN_ERROR) == 21
    assert exit_code_for(ErrorCategory.DEPLOY_ERROR) == 30
    assert exit_code_for(ErrorCategory.SERVER_ERROR) == 40
    assert exit_code_for(ErrorCategory.TEST_ERROR) == 50
    assert exit_code_for(ErrorCategory.IO_ERROR) == 60
    assert exit_code_for(ErrorCategory.DEPENDENCY_ERROR) == 70
    assert exit_code_for(ErrorCategory.CONFLICT_ERROR) == 80
    assert exit_code_for(ErrorCategory.UNKNOWN) == 90


def test_modctl_error_captures_category_and_message():
    err = ModctlError(
        ErrorCategory.CONFIG_ERROR,
        "Missing env var: BOSSSIGNAL_SECRET",
        details="env var not found in environment",
        suggested_fix="export BOSSSIGNAL_SECRET=...",
    )
    assert err.category == ErrorCategory.CONFIG_ERROR
    assert "BOSSSIGNAL_SECRET" in str(err)
    assert err.suggested_fix.startswith("export")


def test_modctl_error_is_raisable():
    with pytest.raises(ModctlError) as exc_info:
        raise ModctlError(ErrorCategory.IO_ERROR, "file not found")
    assert exc_info.value.category == ErrorCategory.IO_ERROR

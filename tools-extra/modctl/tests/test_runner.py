"""Tests for subprocess runner."""
import pytest

from modctl.actions.runner import run_command, CommandOutput
from modctl.errors import ModctlError, ErrorCategory


def test_run_command_returns_output_on_success():
    result = run_command(["python", "-c", "print('hello')"], timeout_s=10)
    assert isinstance(result, CommandOutput)
    assert result.returncode == 0
    assert "hello" in result.stdout


def test_run_command_captures_nonzero_returncode():
    result = run_command(["python", "-c", "import sys; sys.exit(7)"], timeout_s=10)
    assert result.returncode == 7


def test_run_command_raises_modctl_error_on_timeout():
    with pytest.raises(ModctlError) as exc_info:
        run_command(
            ["python", "-c", "import time; time.sleep(10)"],
            timeout_s=1,
        )
    assert exc_info.value.category == ErrorCategory.IO_ERROR
    assert "timed out" in exc_info.value.message.lower()


def test_run_command_captures_stderr():
    result = run_command(
        ["python", "-c", "import sys; print('oops', file=sys.stderr); sys.exit(1)"],
        timeout_s=10,
    )
    assert result.returncode == 1
    assert "oops" in result.stderr

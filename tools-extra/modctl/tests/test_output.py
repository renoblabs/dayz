"""Tests for OutputFormatter — human and JSON output modes."""
import json
from io import StringIO

from modctl.output import CommandResult, OutputFormatter, StepResult


def test_human_output_prints_steps():
    buf = StringIO()
    fmt = OutputFormatter(mode="human", stream=buf)
    result = CommandResult(command="build", mod="bosssignal", status="ok", duration_s=5.3)
    result.steps.append(StepResult(name="resolve_config", status="ok", duration_s=0.1))
    result.steps.append(StepResult(name="addon_builder", status="ok", duration_s=4.2))
    fmt.emit(result)
    out = buf.getvalue()
    assert "resolve_config" in out
    assert "addon_builder" in out
    assert "bosssignal" in out


def test_json_output_produces_valid_json():
    buf = StringIO()
    fmt = OutputFormatter(mode="json", stream=buf)
    result = CommandResult(command="build", mod="bosssignal", status="ok", duration_s=5.3)
    result.steps.append(StepResult(name="resolve_config", status="ok", duration_s=0.1))
    fmt.emit(result)
    parsed = json.loads(buf.getvalue())
    assert parsed["command"] == "build"
    assert parsed["mod"] == "bosssignal"
    assert parsed["status"] == "ok"
    assert parsed["duration_s"] == 5.3
    assert parsed["steps"][0]["name"] == "resolve_config"


def test_command_result_error_status_propagates():
    result = CommandResult(command="build", mod="bosssignal", status="error", duration_s=2.1)
    result.failing_step = "addon_builder"
    result.errors.append({"category": "BUILD_ERROR", "message": "Missing ;"})

    buf = StringIO()
    fmt = OutputFormatter(mode="json", stream=buf)
    fmt.emit(result)
    parsed = json.loads(buf.getvalue())
    assert parsed["status"] == "error"
    assert parsed["failing_step"] == "addon_builder"
    assert parsed["errors"][0]["category"] == "BUILD_ERROR"

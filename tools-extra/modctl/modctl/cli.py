"""modctl CLI — Typer app and command registrations."""
from __future__ import annotations

from pathlib import Path
from typing import Optional

import typer

from modctl.config import load_mods_yaml
from modctl.errors import ErrorCategory, ModctlError, exit_code_for
from modctl.output import CommandResult, OutputFormatter, StepResult

app = typer.Typer(
    name="modctl",
    help="DayZ mod development workflow CLI.",
    no_args_is_help=True,
)


_STATE: dict = {"config_path": Path("tools/modctl/mods.yaml"), "json": False}


@app.callback()
def _main(
    config: Path = typer.Option(
        Path("tools/modctl/mods.yaml"),
        "--config",
        "-c",
        help="Path to mods.yaml",
    ),
    json_output: bool = typer.Option(
        False, "--json", help="Emit structured JSON output"
    ),
) -> None:
    _STATE["config_path"] = config
    _STATE["json"] = json_output


def _emit(result: CommandResult) -> None:
    fmt = OutputFormatter(mode="json" if _STATE["json"] else "human")
    fmt.emit(result)
    if result.status == "error" and result.errors:
        category_str = result.errors[0].get("category", "UNKNOWN")
        try:
            category = ErrorCategory(category_str)
        except ValueError:
            category = ErrorCategory.UNKNOWN
        raise typer.Exit(code=exit_code_for(category))


@app.command()
def version() -> None:
    """Print modctl version."""
    from modctl import __version__
    typer.echo(f"modctl {__version__}")


@app.command()
def doctor() -> None:
    """Verify toolchain health (DayZ Tools, DayZ Server, signing keys)."""
    from modctl.orchestration.doctor import run_doctor

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="doctor", mod=None, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    report = run_doctor(config)
    result = CommandResult(command="doctor", mod=None, status="ok" if report.overall_ok else "error")
    for check in report.checks:
        result.steps.append(StepResult(
            name=check.name,
            status="ok" if check.ok else "error",
            details=check.detail,
        ))
    if not report.overall_ok:
        result.failing_step = next(
            (c.name for c in report.checks if not c.ok),
            None,
        )
        result.errors.append({
            "category": ErrorCategory.DEPENDENCY_ERROR.value,
            "message": "Toolchain health check failed",
            "details": "One or more required components missing — see step details.",
        })
    _emit(result)


@app.command()
def build(
    mod: str = typer.Argument(..., help="Name of the mod to build"),
) -> None:
    """Compile + sign a mod into a signed PBO."""
    from modctl.orchestration.build import BuildOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="build", mod=mod, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = BuildOrchestrator(config)
    try:
        result = orch.build(mod)
    except ModctlError as e:
        result = CommandResult(command="build", mod=mod, status="error")
        result.failing_step = "resolve_mod"
        result.errors.append(_err_to_dict(e))
    _emit(result)


@app.command()
def deploy(
    mod: str = typer.Argument(..., help="Name of the mod to deploy"),
) -> None:
    """Copy a built PBO to the local DayZ Server."""
    from modctl.orchestration.deploy import DeployOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="deploy", mod=mod, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = DeployOrchestrator(config)
    try:
        result = orch.deploy(mod)
    except ModctlError as e:
        result = CommandResult(command="deploy", mod=mod, status="error")
        result.failing_step = "resolve_mod"
        result.errors.append(_err_to_dict(e))
    _emit(result)


@app.command()
def ship(
    mod: str = typer.Argument(..., help="Name of the mod to ship (build + deploy)"),
) -> None:
    """Full build + deploy cycle. Server restart + smoke test come in Plan 2."""
    from modctl.orchestration.ship import ShipOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="ship", mod=mod, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = ShipOrchestrator(config)
    try:
        result = orch.ship(mod)
    except ModctlError as e:
        result = CommandResult(command="ship", mod=mod, status="error")
        result.failing_step = "resolve_mod"
        result.errors.append(_err_to_dict(e))
    _emit(result)


@app.command()
def serve(
    detached: bool = typer.Option(False, "--detached", "-d", help="Start server in background + return immediately"),
) -> None:
    """Start local DayZ Server with deployed mods."""
    from modctl.orchestration.serve import ServeOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="serve", mod=None, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = ServeOrchestrator(config)
    result = orch.start()
    _emit(result)
    # Note: when --detached, server runs in the background and we return now.
    # Foreground streaming mode is Plan-2-MVP deferred (needs proper stdio pump).


@app.command()
def restart() -> None:
    """Stop the running DayZ Server (by PID from state) and start fresh."""
    from modctl.orchestration.restart import RestartOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="restart", mod=None, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = RestartOrchestrator(config)
    result = orch.restart()
    _emit(result)


@app.command()
def tail() -> None:
    """Find + report the latest RPT log path. (Streaming mode: call Python directly for now.)"""
    from modctl.orchestration.tail import TailOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="tail", mod=None, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = TailOrchestrator(config)
    result = orch.find()
    _emit(result)


@app.command()
def diagnose(
    rpt: Optional[Path] = typer.Option(None, "--rpt", help="Explicit RPT file path (default: newest in profile dir)"),
) -> None:
    """Parse the latest RPT log for known error patterns + suggest fixes."""
    from modctl.orchestration.diagnose import DiagnoseOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="diagnose", mod=None, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    orch = DiagnoseOrchestrator(config)
    result = orch.diagnose(rpt_path=rpt)

    # In human mode, add the diagnoses as readable lines after the steps.
    if not _STATE["json"] and result.status == "ok":
        diagnoses = result.result.get("diagnoses", [])
        if diagnoses:
            typer.echo(f"\nFound {len(diagnoses)} error(s):")
            for d in diagnoses:
                sev = d["severity"].upper()
                typer.echo(f"\n  [{sev}] {d['rule_id']} (line {d['line_num']})")
                typer.echo(f"    Raw: {d['raw_line'][:120]}")
                typer.echo(f"    Diagnosis: {d['diagnosis']}")
                if d["fix_template"]:
                    typer.echo(f"    Fix: {d['fix_template']}")
                if d["fix_action"]:
                    typer.echo(f"    Run: {d['fix_action']}")
        else:
            typer.echo("\nNo matched errors. RPT looks clean (for the rules we know).")

    _emit(result)


@app.command()
def fix(
    rpt: Optional[Path] = typer.Option(None, "--rpt", help="Explicit RPT file path"),
    auto_apply: bool = typer.Option(False, "--auto-apply", help="Apply fixes without prompting (can_auto_fix rules only)"),
) -> None:
    """Run diagnose, then prompt-and-apply fixes for each diagnosed error."""
    from modctl.orchestration.diagnose import DiagnoseOrchestrator
    from modctl.orchestration.fix import FixOrchestrator
    from modctl.diagnosis import DiagnosedError

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="fix", mod=None, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    diagnose_result = DiagnoseOrchestrator(config).diagnose(rpt_path=rpt)
    if diagnose_result.status == "error":
        _emit(diagnose_result)
        return

    diagnoses = diagnose_result.result.get("diagnoses", [])
    if not diagnoses:
        typer.echo("No diagnosed errors. Nothing to fix.")
        result = CommandResult(command="fix", mod=None, status="ok")
        _emit(result)
        return

    # Rehydrate dicts into DiagnosedError objects for FixOrchestrator
    def _to_diag(d: dict) -> DiagnosedError:
        return DiagnosedError(
            rule_id=d["rule_id"],
            category=ErrorCategory(d["category"]),
            severity=d["severity"],
            confidence=d["confidence"],
            raw_line=d["raw_line"],
            line_num=d["line_num"],
            diagnosis=d["diagnosis"],
            fix_template=d.get("fix_template"),
            fix_action=d.get("fix_action"),
            can_auto_fix=d.get("can_auto_fix", False),
        )

    def _approve(diag: DiagnosedError) -> bool:
        if auto_apply and diag.can_auto_fix:
            return True
        typer.echo(f"\n[{diag.severity.upper()}] {diag.rule_id}")
        typer.echo(f"  Diagnosis: {diag.diagnosis}")
        if diag.fix_action:
            typer.echo(f"  Will run: {diag.fix_action}")
        response = typer.prompt("  Apply? [y/N]", default="n", show_default=False)
        return response.lower().startswith("y")

    applied = 0
    skipped = 0
    failed = 0
    for d_dict in diagnoses:
        diag = _to_diag(d_dict)
        res = FixOrchestrator(config, approve_callback=_approve).fix(diag)
        if res.status == "error":
            failed += 1
        elif any(s.name == "run_fix_action" and s.status == "ok" for s in res.steps):
            applied += 1
        else:
            skipped += 1

    summary = CommandResult(command="fix", mod=None, status="ok")
    summary.result = {"applied": applied, "skipped": skipped, "failed": failed}
    if not _STATE["json"]:
        typer.echo(f"\nFix summary: {applied} applied, {skipped} skipped, {failed} failed.")
    _emit(summary)


@app.command()
def watch(
    mod: str = typer.Argument(..., help="Name of the mod to watch"),
) -> None:
    """Auto-rebuild + redeploy on file change (Ctrl+C to stop)."""
    import time as _time
    from modctl.orchestration.ship import ShipOrchestrator
    from modctl.orchestration.watch import WatchOrchestrator

    try:
        config = load_mods_yaml(_STATE["config_path"])
    except ModctlError as e:
        result = CommandResult(command="watch", mod=mod, status="error")
        result.failing_step = "load_config"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    def _ship(name: str) -> CommandResult:
        r = ShipOrchestrator(config).ship(name)
        fmt = OutputFormatter(mode="json" if _STATE["json"] else "human")
        fmt.emit(r)
        return r

    orch = WatchOrchestrator(config, ship_callable=_ship)
    try:
        orch.start(mod)
    except ModctlError as e:
        result = CommandResult(command="watch", mod=mod, status="error")
        result.failing_step = "resolve_mod"
        result.errors.append(_err_to_dict(e))
        _emit(result)
        return

    typer.echo(f"👀 Watching {mod}... (Ctrl+C to stop)")
    try:
        while True:
            _time.sleep(1)
    except KeyboardInterrupt:
        pass
    finally:
        orch.stop()
        typer.echo("\n✓ Watcher stopped.")


def _err_to_dict(err: ModctlError) -> dict:
    return {
        "category": err.category.value,
        "message": err.message,
        "details": err.details,
        "suggested_fix": err.suggested_fix,
    }

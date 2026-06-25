"""Ship orchestration — build + deploy + (future: restart + smoke).

In Plan 1, ship = build + deploy. Server restart + in-game smoke test
land in Plan 2 with the serve command.
"""
from __future__ import annotations

import time

from modctl.config import ModsConfig
from modctl.orchestration.build import BuildOrchestrator
from modctl.orchestration.deploy import DeployOrchestrator
from modctl.output import CommandResult


class ShipOrchestrator:
    def __init__(self, config: ModsConfig) -> None:
        self.config = config

    def ship(self, mod_name: str) -> CommandResult:
        started = time.monotonic()
        result = CommandResult(command="ship", mod=mod_name, status="ok")

        build = BuildOrchestrator(self.config).build(mod_name)
        result.steps.extend(build.steps)
        if build.status == "error":
            result.status = "error"
            result.failing_step = build.failing_step
            result.errors.extend(build.errors)
            result.result.update(build.result)
            result.duration_s = time.monotonic() - started
            return result
        result.result.update(build.result)

        deploy = DeployOrchestrator(self.config).deploy(mod_name)
        result.steps.extend(deploy.steps)
        if deploy.status == "error":
            result.status = "error"
            result.failing_step = deploy.failing_step
            result.errors.extend(deploy.errors)
            result.result.update(deploy.result)
            result.duration_s = time.monotonic() - started
            return result
        result.result.update(deploy.result)

        result.duration_s = time.monotonic() - started
        return result

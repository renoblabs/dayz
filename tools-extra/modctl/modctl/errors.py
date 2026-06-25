"""Error categories and ModctlError — structured errors across the CLI."""
from __future__ import annotations

from enum import Enum
from typing import Optional


class ErrorCategory(str, Enum):
    CONFIG_ERROR = "CONFIG_ERROR"
    BUILD_ERROR = "BUILD_ERROR"
    SIGN_ERROR = "SIGN_ERROR"
    DEPLOY_ERROR = "DEPLOY_ERROR"
    SERVER_ERROR = "SERVER_ERROR"
    TEST_ERROR = "TEST_ERROR"
    IO_ERROR = "IO_ERROR"
    DEPENDENCY_ERROR = "DEPENDENCY_ERROR"
    CONFLICT_ERROR = "CONFLICT_ERROR"
    UNKNOWN = "UNKNOWN"


_EXIT_CODES = {
    ErrorCategory.CONFIG_ERROR: 10,
    ErrorCategory.BUILD_ERROR: 20,
    ErrorCategory.SIGN_ERROR: 21,
    ErrorCategory.DEPLOY_ERROR: 30,
    ErrorCategory.SERVER_ERROR: 40,
    ErrorCategory.TEST_ERROR: 50,
    ErrorCategory.IO_ERROR: 60,
    ErrorCategory.DEPENDENCY_ERROR: 70,
    ErrorCategory.CONFLICT_ERROR: 80,
    ErrorCategory.UNKNOWN: 90,
}


def exit_code_for(category: ErrorCategory) -> int:
    return _EXIT_CODES[category]


class ModctlError(Exception):
    """Base exception for all modctl-raised errors.

    Carries a category (for exit codes + JSON output), a human message,
    optional details (stderr excerpt, context), and an optional suggested fix.
    """

    def __init__(
        self,
        category: ErrorCategory,
        message: str,
        details: Optional[str] = None,
        suggested_fix: Optional[str] = None,
    ) -> None:
        super().__init__(message)
        self.category = category
        self.message = message
        self.details = details
        self.suggested_fix = suggested_fix

    def __str__(self) -> str:
        return f"[{self.category.value}] {self.message}"

"""mods.yaml loader + Pydantic models.

Loaded once at the start of every command invocation. Validates the config
and fails fast on typos, missing required fields, wrong types.
"""
from __future__ import annotations

import os
import re
from pathlib import Path
from typing import Dict, List, Literal, Optional

import yaml
from pydantic import BaseModel, Field

from modctl.errors import ErrorCategory, ModctlError

_ENV_VAR_PATTERN = re.compile(r"\$\{([A-Z_][A-Z0-9_]*)\}")


def _resolve_env_vars(value):
    """Recursively substitute ${VAR} references in strings inside nested data.

    Raises ModctlError if any referenced var is not set in the environment.
    """
    if isinstance(value, str):
        def replace(match: re.Match) -> str:
            var_name = match.group(1)
            if var_name not in os.environ:
                raise ModctlError(
                    ErrorCategory.CONFIG_ERROR,
                    f"Missing env var: {var_name}",
                    details=f"Referenced in mods.yaml as ${{{var_name}}}",
                    suggested_fix=f"export {var_name}=<value>",
                )
            return os.environ[var_name]

        return _ENV_VAR_PATTERN.sub(replace, value)
    if isinstance(value, dict):
        return {k: _resolve_env_vars(v) for k, v in value.items()}
    if isinstance(value, list):
        return [_resolve_env_vars(v) for v in value]
    return value


class Defaults(BaseModel):
    dayz_tools_path: str
    dayz_server_path: str
    dayz_client_path: Optional[str] = None
    signing_keys_dir: str
    output_dir: str
    deploy_client_workshop: bool = False
    pack_only: bool = True
    pbo_prefix_matches_name: bool = True
    # Plan 2: server runtime config
    dayz_server_exe: str = "DayZServer_x64.exe"  # relative to dayz_server_path
    dayz_server_config: str = "serverDZ.cfg"
    dayz_server_port: int = 2302
    dayz_server_profile_dir: str = "profiles"
    dayz_server_startup_params: List[str] = Field(default_factory=list)


class Backend(BaseModel):
    kind: Literal["fastapi", "custom"]
    dir: str
    tests: Optional[str] = None
    compose_file: Optional[str] = None
    health_url: Optional[str] = None


class EnforceConfig(BaseModel):
    file: str
    vars: Dict[str, str] = Field(default_factory=dict)


class Mod(BaseModel):
    name: str
    source: str
    pbo_name: str
    mod_folder: str
    depends_on: List[str] = Field(default_factory=list)
    backend: Optional[str] = None
    branch: Optional[str] = None
    enforce_config: Optional[EnforceConfig] = None
    watch: List[str] = Field(default_factory=list)


class Dependency(BaseModel):
    name: str
    workshop_id: Optional[str] = None
    mod_folder: str
    required: bool = True


class ModsConfig(BaseModel):
    version: int = 1
    defaults: Defaults
    backends: Dict[str, Backend] = Field(default_factory=dict)
    mods: List[Mod] = Field(default_factory=list)
    dependencies: Dict[str, Dependency] = Field(default_factory=dict)


def load_mods_yaml(path: Path) -> ModsConfig:
    """Load and validate a mods.yaml file. Raises ModctlError on any problem."""
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = yaml.safe_load(f)
    except FileNotFoundError:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"mods.yaml not found at {path}",
            suggested_fix=f"Create {path} or pass --config <path>",
        )
    except yaml.YAMLError as e:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"Invalid YAML in {path}",
            details=str(e),
        )

    data = _resolve_env_vars(data)

    try:
        return ModsConfig.model_validate(data)
    except Exception as e:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"mods.yaml validation failed",
            details=str(e),
        )

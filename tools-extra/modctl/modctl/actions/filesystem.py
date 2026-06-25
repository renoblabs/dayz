"""Filesystem helpers — copy, verify, substitute."""
from __future__ import annotations

import re
import shutil
from pathlib import Path
from typing import Dict

from modctl.errors import ErrorCategory, ModctlError


def _safe_copy(src: Path, dst: Path) -> None:
    """shutil.copy2 that no-ops when source and destination resolve to the same file.

    DayZ workflows commonly junction the server mod folder straight at the
    build output dir; a literal copy in that case raises SameFileError. We treat
    that as an already-up-to-date state.
    """
    try:
        if dst.exists() and src.resolve() == dst.resolve():
            return
    except OSError:
        pass
    try:
        shutil.copy2(src, dst)
    except shutil.SameFileError:
        return


def verify_path_exists(path: Path, label: str) -> None:
    """Raise DEPENDENCY_ERROR if the path doesn't exist."""
    if not path.exists():
        raise ModctlError(
            ErrorCategory.DEPENDENCY_ERROR,
            f"{label} not found at {path}",
            suggested_fix=f"Install {label} or correct the path in mods.yaml.",
        )


def copy_pbo_to_server(
    pbo_path: Path,
    bisign_path: Path,
    bikey_path: Path,
    server_root: Path,
    mod_folder: str,
) -> None:
    """Copy a signed PBO (+ .bisign + .bikey) into a DayZ Server install.

    Layout produced:
      <server_root>/<mod_folder>/addons/<pbo>
      <server_root>/<mod_folder>/addons/<bisign>
      <server_root>/<mod_folder>/keys/<bikey>
      <server_root>/keys/<bikey>
    """
    mod_addons_dir = server_root / mod_folder / "addons"
    mod_addons_dir.mkdir(parents=True, exist_ok=True)
    _safe_copy(pbo_path, mod_addons_dir / pbo_path.name)
    _safe_copy(bisign_path, mod_addons_dir / bisign_path.name)

    mod_keys_dir = server_root / mod_folder / "keys"
    mod_keys_dir.mkdir(parents=True, exist_ok=True)
    _safe_copy(bikey_path, mod_keys_dir / bikey_path.name)

    keys_dir = server_root / "keys"
    keys_dir.mkdir(parents=True, exist_ok=True)
    _safe_copy(bikey_path, keys_dir / bikey_path.name)


def sync_mod_to_client_workshop(
    server_mod_root: Path,
    client_root: Path,
    mod_folder: str,
    display_name: str,
) -> Path:
    """Expose a locally deployed server mod to the DayZ Launcher.

    Layout produced:
      <client_root>/!Workshop/<mod_folder>/addons -> <server_mod_root>/addons
      <client_root>/!Workshop/<mod_folder>/keys   -> <server_mod_root>/keys
      <client_root>/!Workshop/<mod_folder>/meta.cpp
    """
    verify_path_exists(server_mod_root / "addons", f"{mod_folder} server addons")

    workshop_mod_root = client_root / "!Workshop" / mod_folder
    workshop_mod_root.mkdir(parents=True, exist_ok=True)

    for child_name in ("addons", "keys"):
        source = server_mod_root / child_name
        if not source.exists():
            continue

        target = workshop_mod_root / child_name
        if target.exists():
            if target.is_symlink() or target.is_dir():
                try:
                    if target.resolve() == source.resolve():
                        continue
                except OSError:
                    pass
            if target.is_dir() and not target.is_symlink():
                shutil.rmtree(target)
            else:
                target.unlink()

        try:
            target.symlink_to(source, target_is_directory=True)
        except OSError:
            shutil.copytree(source, target)

    meta_text = (
        "protocol = 1;\n"
        "publishedid = 0;\n"
        f'name = "{display_name}";\n'
        "timestamp = 0;\n"
    )
    (workshop_mod_root / "meta.cpp").write_text(meta_text, encoding="utf-8")
    return workshop_mod_root


_ENFORCE_STRING_ASSIGN = re.compile(
    r'(static\s+string\s+(\w+)\s*=\s*)"[^"]*"(\s*;)',
    re.MULTILINE,
)


def substitute_enforce_vars(source_file: Path, vars: Dict[str, str]) -> None:
    """Replace `static string VAR = "..."` assignments in an Enforce .c file.

    Only rewrites variables in `vars`. Raises CONFIG_ERROR if any var in
    `vars` doesn't appear as a `static string` constant in the file.
    """
    content = source_file.read_text(encoding="utf-8")
    found: Dict[str, bool] = {k: False for k in vars}

    def _sub(match: re.Match) -> str:
        prefix = match.group(1)
        name = match.group(2)
        suffix = match.group(3)
        if name in vars:
            found[name] = True
            return f'{prefix}"{vars[name]}"{suffix}'
        return match.group(0)

    new_content = _ENFORCE_STRING_ASSIGN.sub(_sub, content)

    missing = [k for k, seen in found.items() if not seen]
    if missing:
        raise ModctlError(
            ErrorCategory.CONFIG_ERROR,
            f"Enforce config vars not found in source: {', '.join(missing)}",
            details=f"File: {source_file}\nSearched for: static string <NAME> = ...",
            suggested_fix="Check mods.yaml enforce_config.vars matches actual constants in the .c file.",
        )

    source_file.write_text(new_content, encoding="utf-8")

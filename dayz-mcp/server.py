"""
DayZ MCP Server - FastMCP wrapper for DayZ dev tools.

Provides tools for:
- Unpacking PBO files
- Validating Enforce script syntax
- Analyzing mod conflicts

Run with: python -m dayz_mcp.server
"""

import subprocess
import json
from pathlib import Path
from typing import Optional, List, Dict, Any

# FastMCP - install via: pip install fastmcp
try:
    from fastmcp import FastMCP
except ImportError:
    print("Install fastmcp: pip install fastmcp")
    raise


# Initialize the MCP server
mcp = FastMCP("dayz-dev-tools")


# Configuration - can be overridden via environment variables
import os

DAYZ_TOOLS_PATH = Path(os.environ.get(
    "DAYZ_TOOLS_PATH",
    "C:/Program Files (x86)/Steam/steamapps/common/DayZ Tools"
))
DAYZ_SERVER_PATH = Path(os.environ.get(
    "DAYZ_SERVER_PATH", 
    "C:/Program Files (x86)/Steam/steamapps/common/DayZServer"
))


def _filebank_exe() -> Path:
    """Get FileBank.exe path."""
    return DAYZ_TOOLS_PATH / "Bin" / "PboUtils" / "FileBank.exe"


def _bankrev_exe() -> Path:
    """Get BankRev.exe path for unpacking PBOs."""
    return DAYZ_TOOLS_PATH / "Bin" / "PboUtils" / "BankRev.exe"


# ============================================================================
# MCP Tools
# ============================================================================

@mcp.tool()
def unpack_pbo(pbo_path: str, output_dir: Optional[str] = None) -> Dict[str, Any]:
    """
    Unpack a DayZ PBO file to read its source contents.
    
    Uses BankRev.exe from DayZ Tools to extract PBO contents.
    
    Args:
        pbo_path: Absolute path to the .pbo file
        output_dir: Optional output directory (defaults to same location as PBO)
    
    Returns:
        Dict with status, output_path, and list of extracted files
    """
    pbo = Path(pbo_path)
    if not pbo.exists():
        return {"status": "error", "message": f"PBO not found: {pbo_path}"}
    
    bankrev = _bankrev_exe()
    if not bankrev.exists():
        return {"status": "error", "message": f"BankRev.exe not found at {bankrev}"}
    
    # BankRev outputs to folder next to PBO with same name (minus .pbo)
    try:
        result = subprocess.run(
            [str(bankrev), str(pbo)],
            capture_output=True,
            text=True,
            timeout=30
        )
        
        output_path = pbo.parent / pbo.stem  # PBO name without extension
        
        if output_path.exists():
            files = list(output_path.rglob("*"))
            return {
                "status": "success",
                "output_path": str(output_path),
                "file_count": len(files),
                "files": [str(f.relative_to(output_path)) for f in files if f.is_file()][:50]
            }
        else:
            return {
                "status": "error", 
                "message": "BankRev completed but output folder not created",
                "stderr": result.stderr
            }
            
    except subprocess.TimeoutExpired:
        return {"status": "error", "message": "BankRev timed out"}
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def validate_enforce_syntax(source_dir: str) -> Dict[str, Any]:
    """
    Validate Enforce script syntax by attempting a test compile.
    
    Uses FileBank.exe to pack the source and captures any compilation errors.
    
    Args:
        source_dir: Path to the mod source directory containing scripts/
    
    Returns:
        Dict with status, errors, and warnings
    """
    source = Path(source_dir)
    if not source.exists():
        return {"status": "error", "message": f"Source directory not found: {source_dir}"}
    
    scripts_dir = source / "scripts"
    if not scripts_dir.exists():
        return {"status": "error", "message": f"No scripts/ directory in {source_dir}"}
    
    filebank = _filebank_exe()
    if not filebank.exists():
        return {"status": "error", "message": f"FileBank.exe not found at {filebank}"}
    
    # Create temp output directory
    import tempfile
    with tempfile.TemporaryDirectory() as tmpdir:
        try:
            result = subprocess.run(
                [str(filebank), "-dst", tmpdir, str(source)],
                capture_output=True,
                text=True,
                timeout=60
            )
            
            # Check for PBO creation
            pbo_files = list(Path(tmpdir).glob("*.pbo"))
            
            errors = []
            warnings = []
            
            # Parse FileBank output for errors
            for line in (result.stdout + result.stderr).split("\n"):
                if "error" in line.lower():
                    errors.append(line.strip())
                elif "warning" in line.lower():
                    warnings.append(line.strip())
            
            return {
                "status": "success" if pbo_files else "error",
                "compiled": len(pbo_files) > 0,
                "pbo_size": pbo_files[0].stat().st_size if pbo_files else 0,
                "errors": errors,
                "warnings": warnings,
                "stdout": result.stdout[:500] if result.stdout else "",
                "stderr": result.stderr[:500] if result.stderr else ""
            }
            
        except subprocess.TimeoutExpired:
            return {"status": "error", "message": "FileBank timed out"}
        except Exception as e:
            return {"status": "error", "message": str(e)}


@mcp.tool()
def analyze_mod_conflicts(mod_dirs: List[str]) -> Dict[str, Any]:
    """
    Analyze multiple mods for class override conflicts.
    
    Scans for 'modded class' declarations across mods to identify
    potential load-order conflicts.
    
    Args:
        mod_dirs: List of mod source directories to analyze
    
    Returns:
        Dict with conflicts found and recommendations
    """
    import re
    
    conflicts = []
    class_map: Dict[str, List[str]] = {}  # class_name -> [mod_names]
    
    for mod_dir in mod_dirs:
        mod_path = Path(mod_dir)
        if not mod_path.exists():
            continue
            
        mod_name = mod_path.name
        
        # Find all .c files
        for c_file in mod_path.rglob("*.c"):
            content = c_file.read_text(encoding="utf-8", errors="ignore")
            
            # Find modded class declarations
            for match in re.finditer(r"modded\s+class\s+(\w+)", content):
                class_name = match.group(1)
                if class_name not in class_map:
                    class_map[class_name] = []
                class_map[class_name].append(mod_name)
    
    # Find conflicts (same class modded in multiple mods)
    for class_name, mods in class_map.items():
        if len(mods) > 1:
            conflicts.append({
                "class": class_name,
                "mods": mods,
                "recommendation": f"Ensure load order: {', '.join(reversed(mods))} (dependent mod last)"
            })
    
    return {
        "status": "success",
        "total_classes_checked": len(class_map),
        "conflicts_found": len(conflicts),
        "conflicts": conflicts
    }


@mcp.tool()
def read_server_log(log_type: str = "script", lines: int = 50) -> Dict[str, Any]:
    """
    Read the latest DayZ server log file.
    
    Args:
        log_type: One of "script", "rpt", or "crash"
        lines: Number of lines to read from the end
    
    Returns:
        Dict with log content and timestamp
    """
    profiles_dir = DAYZ_SERVER_PATH / "profiles"
    if not profiles_dir.exists():
        return {"status": "error", "message": f"Profiles directory not found: {profiles_dir}"}
    
    # Find the latest log of the requested type
    patterns = {
        "script": "script_*.log",
        "rpt": "*.RPT",
        "crash": "crash_*.log"
    }
    
    if log_type not in patterns:
        return {"status": "error", "message": f"Invalid log_type: {log_type}. Use: script, rpt, or crash"}
    
    log_files = sorted(
        profiles_dir.glob(patterns[log_type]),
        key=lambda f: f.stat().st_mtime,
        reverse=True
    )
    
    if not log_files:
        return {"status": "error", "message": f"No {log_type} logs found"}
    
    latest = log_files[0]
    
    try:
        content = latest.read_text(encoding="utf-8", errors="ignore")
        all_lines = content.split("\n")
        last_lines = all_lines[-lines:]
        
        return {
            "status": "success",
            "log_file": latest.name,
            "log_path": str(latest),
            "total_lines": len(all_lines),
            "content": "\n".join(last_lines)
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


@mcp.tool()
def get_known_issues() -> Dict[str, Any]:
    """
    Retrieve the top known DayZ modding issues from the skills database.
    
    Returns a structured list of known issues with fixes for quick reference.
    """
    skills_path = Path(__file__).parent.parent / ".claude" / "skills" / "dayz-modding.md"
    
    if not skills_path.exists():
        return {
            "status": "error",
            "message": f"Skills file not found at {skills_path}",
            "fallback": [
                {"issue": "GetStamina() removed in DayZ 1.29", "fix": "Comment out or use GetStaminaHandler()"},
                {"issue": "Param2 class incompatible", "fix": "Use alternative callback patterns"},
                {"issue": "$mission: vs $mpmissions: paths", "fix": "Use $mission: for current mission folder"},
            ]
        }
    
    try:
        content = skills_path.read_text(encoding="utf-8")
        return {
            "status": "success",
            "file": str(skills_path),
            "content": content
        }
    except Exception as e:
        return {"status": "error", "message": str(e)}


# ============================================================================
# Server Entry Point
# ============================================================================

if __name__ == "__main__":
    # Run the MCP server
    mcp.run()

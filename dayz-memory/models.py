"""
Data models for DayZ memory graph nodes.
"""

from dataclasses import dataclass, field, asdict
from typing import Optional, List, Dict, Any
from datetime import datetime
import uuid


def _new_id() -> str:
    return str(uuid.uuid4())


def _now() -> str:
    return datetime.utcnow().isoformat() + "Z"


@dataclass
class DayZError:
    """A captured DayZ error or crash."""
    message: str
    error_type: str  # compile, runtime, load, conflict, hang
    id: str = field(default_factory=_new_id)
    timestamp: str = field(default_factory=_now)
    file_location: Optional[str] = None
    line_number: Optional[int] = None
    stack_trace: str = ""
    raw_snippet: str = ""
    mod_name: Optional[str] = None
    dayz_version: str = "1.29"
    severity: str = "error"  # warning, error, fatal
    resolved: bool = False
    tags: List[str] = field(default_factory=list)

    def to_dict(self) -> Dict[str, Any]:
        d = asdict(self)
        d["tags"] = ",".join(self.tags)
        return d


@dataclass
class EnforceScript:
    """A code pattern that works or fails in Enforce scripting."""
    pattern: str
    description: str
    works: bool
    id: str = field(default_factory=_new_id)
    timestamp: str = field(default_factory=_now)
    file_path: Optional[str] = None
    dayz_version: str = "1.29"
    category: str = ""  # syntax, api, type, lifecycle

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class PBOConfig:
    """A PBO packing configuration."""
    mod_name: str
    prefix: str
    id: str = field(default_factory=_new_id)
    timestamp: str = field(default_factory=_now)
    source_dir: str = ""
    output_dir: str = ""
    compression: bool = False
    file_patching: bool = False
    notes: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Solution:
    """A fix or workaround for a DayZ error."""
    description: str
    code_change: str = ""
    id: str = field(default_factory=_new_id)
    timestamp: str = field(default_factory=_now)
    file_path: Optional[str] = None
    line_number: Optional[int] = None
    effectiveness: Optional[float] = None  # 0.0-1.0
    times_applied: int = 0
    times_succeeded: int = 0
    category: str = ""  # comment_out, replace, add, config

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


@dataclass
class Session:
    """A debugging/development session."""
    id: str = field(default_factory=_new_id)
    started_at: str = field(default_factory=_now)
    ended_at: Optional[str] = None
    summary: str = ""
    tool_used: str = ""  # droid, claude_code, cursor
    errors_encountered: int = 0
    errors_resolved: int = 0

    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)

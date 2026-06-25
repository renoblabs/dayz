#!/usr/bin/env python3
"""
analyze_errors.py - Parse DayZ error logs and extract structured data.

Reads from .claude/dayz-errors.jsonl and produces sanitized, structured output
suitable for embedding into a vector database or feeding to a diagnostic agent.

Usage:
    python analyze_errors.py [--input INPUT] [--output OUTPUT] [--format json|markdown]
"""

import json
import re
import argparse
import sys
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, field, asdict
from typing import List, Optional, Dict, Any


# Known DayZ noise patterns to filter out
NOISE_PATTERNS = [
    r"ENTITY\s*\(W\):.*Unknown object class 'pond'",
    r"ENTITY\s*\(W\):.*Door.*is missing geometry",
    r"\[CE\]\[Storage\].*valid:NO",
    r"ANIMATION\s*\(E\):.*Failed to open file",
    r"Inputs.*Cannot read inputs cfg",
    r"WARNING.*File.*was not closed",
]

# Critical error patterns to extract
ERROR_PATTERNS = [
    (r"SCRIPT\s*\(E\):.*Undefined function '(\w+)", "undefined_function"),
    (r"SCRIPT\s*\(E\):.*Can't find class (\w+)", "missing_class"),
    (r"SCRIPT\s*\(E\):.*Bad type '(\w+)'", "bad_type"),
    (r"SCRIPT\s*\(E\):.*Can't compile", "compile_error"),
    (r"SCRIPT\s*\(E\):.*(@[\w/]+\.c,\d+)", "script_error_with_location"),
    (r"crash", "crash_indicator"),
]


@dataclass
class SanitizedError:
    """Structured representation of a DayZ error."""
    timestamp: str
    error_type: str
    error_message: str
    file_location: Optional[str] = None
    function_name: Optional[str] = None
    class_name: Optional[str] = None
    stack_trace: List[str] = field(default_factory=list)
    raw_snippet: str = ""
    sanitized: bool = True


def filter_noise(lines: List[str]) -> List[str]:
    """Remove known DayZ engine noise from log lines."""
    filtered = []
    for line in lines:
        is_noise = any(re.search(pattern, line, re.IGNORECASE) for pattern in NOISE_PATTERNS)
        if not is_noise:
            filtered.append(line)
    return filtered


def extract_stack_trace(lines: List[str]) -> List[str]:
    """Extract meaningful stack trace from log lines."""
    stack = []
    in_trace = False
    
    for line in lines:
        # Look for script error indicators
        if re.search(r"SCRIPT\s*\(E\)", line) or "Error" in line or "error" in line:
            in_trace = True
        
        if in_trace:
            # Capture file references
            if re.search(r"\.c[,\)]", line) or "scripts/" in line.lower():
                stack.append(line.strip())
            # Capture function/class names
            elif re.search(r"class|function|method", line, re.IGNORECASE):
                stack.append(line.strip())
    
    return stack[:10]  # Limit stack depth


def classify_error(snippet: str) -> tuple[str, Dict[str, Any]]:
    """Classify the error type and extract relevant details."""
    for pattern, error_type in ERROR_PATTERNS:
        match = re.search(pattern, snippet, re.IGNORECASE)
        if match:
            details = {"matched_text": match.group(0)}
            if match.groups():
                details["capture"] = match.group(1)
            return error_type, details
    return "unknown", {}


def parse_error_entry(entry: Dict[str, Any]) -> SanitizedError:
    """Parse a single JSONL entry into structured error data."""
    snippet = entry.get("error_snippet", "")
    lines = snippet.split("\n")
    
    # Filter noise
    clean_lines = filter_noise(lines)
    
    # Extract stack trace
    stack = extract_stack_trace(clean_lines)
    
    # Classify error
    error_type, details = classify_error(snippet)
    
    # Extract file location if present
    file_match = re.search(r"@(\w+)/scripts/[\w/]+\.c,(\d+)", snippet)
    file_location = f"{file_match.group(1)}/scripts/... line {file_match.group(2)}" if file_match else None
    
    return SanitizedError(
        timestamp=entry.get("timestamp", ""),
        error_type=error_type,
        error_message=details.get("matched_text", clean_lines[0] if clean_lines else "Unknown error"),
        file_location=file_location,
        function_name=details.get("capture") if error_type == "undefined_function" else None,
        class_name=details.get("capture") if error_type in ("missing_class", "bad_type") else None,
        stack_trace=stack,
        raw_snippet=snippet[:500] if len(snippet) > 500 else snippet,
    )


def format_as_json(errors: List[SanitizedError]) -> str:
    """Format errors as JSON array."""
    return json.dumps([asdict(e) for e in errors], indent=2)


def format_as_markdown(errors: List[SanitizedError]) -> str:
    """Format errors as markdown report."""
    lines = ["# DayZ Error Analysis Report\n"]
    lines.append(f"Generated: {datetime.now().isoformat()}\n")
    lines.append(f"Total errors analyzed: {len(errors)}\n\n")
    lines.append("---\n\n")
    
    for i, err in enumerate(errors, 1):
        lines.append(f"## Error #{i}: {err.error_type}\n")
        lines.append(f"- **Timestamp:** {err.timestamp}\n")
        if err.file_location:
            lines.append(f"- **Location:** `{err.file_location}`\n")
        if err.function_name:
            lines.append(f"- **Missing Function:** `{err.function_name}`\n")
        if err.class_name:
            lines.append(f"- **Problem Class:** `{err.class_name}`\n")
        lines.append(f"- **Message:** {err.error_message}\n")
        
        if err.stack_trace:
            lines.append("\n**Stack Trace:**\n```\n")
            lines.extend(err.stack_trace)
            lines.append("\n```\n")
        
        lines.append("\n---\n\n")
    
    return "".join(lines)


def main():
    parser = argparse.ArgumentParser(description="Analyze DayZ error logs")
    parser.add_argument("--input", "-i", default=".claude/dayz-errors.jsonl",
                        help="Input JSONL file path")
    parser.add_argument("--output", "-o", default=None,
                        help="Output file path (default: stdout)")
    parser.add_argument("--format", "-f", choices=["json", "markdown"], default="json",
                        help="Output format")
    parser.add_argument("--last", "-n", type=int, default=None,
                        help="Process only the last N errors")
    
    args = parser.parse_args()
    
    input_path = Path(args.input)
    if not input_path.exists():
        print(f"Error: Input file not found: {input_path}", file=sys.stderr)
        sys.exit(1)
    
    # Read JSONL entries
    entries = []
    with open(input_path, "r", encoding="utf-8") as f:
        for line in f:
            line = line.strip()
            if line:
                try:
                    entries.append(json.loads(line))
                except json.JSONDecodeError:
                    print(f"Warning: Skipping invalid JSON line", file=sys.stderr)
    
    if args.last:
        entries = entries[-args.last:]
    
    # Parse entries
    errors = [parse_error_entry(e) for e in entries]
    
    # Format output
    if args.format == "json":
        output = format_as_json(errors)
    else:
        output = format_as_markdown(errors)
    
    # Write output
    if args.output:
        Path(args.output).write_text(output, encoding="utf-8")
        print(f"Wrote {len(errors)} errors to {args.output}")
    else:
        print(output)


if __name__ == "__main__":
    main()

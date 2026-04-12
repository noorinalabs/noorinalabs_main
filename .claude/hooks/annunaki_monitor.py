#!/usr/bin/env python3
"""PostToolUse hook: Annunaki error monitor.

Fires after every Bash tool call. Inspects the output for error signals
(non-zero exit code, stderr content, common error patterns) and appends
each error to .claude/annunaki/errors.jsonl for later analysis by
/annunaki-attack.

Exit codes:
  0 — always (advisory hook, never blocks)
"""

import json
import re
import sys
from datetime import datetime, timezone
from pathlib import Path

# Where we log errors — JSONL for easy dedup and processing
REPO_ROOT = Path(__file__).resolve().parent.parent.parent
ERRORS_FILE = REPO_ROOT / ".claude" / "annunaki" / "errors.jsonl"

# Patterns that indicate errors even when exit code is 0
ERROR_PATTERNS = [
    re.compile(r"^error\b", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^fatal:", re.IGNORECASE | re.MULTILINE),
    re.compile(r"^FAILED", re.MULTILINE),
    re.compile(r"Traceback \(most recent call last\)", re.MULTILINE),
    re.compile(r"^E\s+\w+Error:", re.MULTILINE),  # pytest-style
    re.compile(r"panic:", re.MULTILINE),
    re.compile(r"ENOENT|EACCES|EPERM", re.MULTILINE),
    re.compile(r"command not found", re.IGNORECASE | re.MULTILINE),
    re.compile(r"No such file or directory", re.MULTILINE),
    re.compile(r"Permission denied", re.MULTILINE),
    re.compile(r"ModuleNotFoundError:", re.MULTILINE),
    re.compile(r"ImportError:", re.MULTILINE),
    re.compile(r"SyntaxError:", re.MULTILINE),
    re.compile(r"TypeError:|ValueError:|KeyError:|AttributeError:", re.MULTILINE),
    re.compile(r"npm ERR!", re.MULTILINE),
    re.compile(r"exit status [1-9]", re.MULTILINE),
    re.compile(r"failed with exit code", re.IGNORECASE | re.MULTILINE),
]

# Patterns to IGNORE (not real errors)
IGNORE_PATTERNS = [
    re.compile(r"grep.*error", re.IGNORECASE),  # grep searching for "error"
    re.compile(r"--error", re.IGNORECASE),  # flags containing "error"
    re.compile(r"error_log|error\.log|errorhandl", re.IGNORECASE),  # filenames
]


def _extract_error_lines(text: str, max_lines: int = 10) -> list[str]:
    """Extract the most relevant error lines from output."""
    lines = text.strip().splitlines()
    error_lines = []
    for i, line in enumerate(lines):
        for pattern in ERROR_PATTERNS:
            if pattern.search(line):
                # Grab this line and up to 2 lines of context after
                context_end = min(i + 3, len(lines))
                error_lines.extend(lines[i:context_end])
                break
        if len(error_lines) >= max_lines:
            break
    return error_lines[:max_lines]


def _should_ignore(command: str, output: str) -> bool:
    """Return True if this looks like a false positive."""
    for pattern in IGNORE_PATTERNS:
        if pattern.search(command):
            return True
    return False


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")
    tool_output = input_data.get("tool_output", {})
    stdout = tool_output.get("stdout", "")
    stderr = tool_output.get("stderr", "")
    exit_code = tool_output.get("exit_code", 0)

    # Combine output for pattern matching
    combined_output = f"{stdout}\n{stderr}".strip()

    if not combined_output:
        sys.exit(0)

    # Check for false positives
    if _should_ignore(command, combined_output):
        sys.exit(0)

    # Determine if this is an error
    is_error = False
    matched_patterns = []

    # Non-zero exit code is always an error
    if exit_code and exit_code != 0:
        is_error = True
        matched_patterns.append(f"exit_code={exit_code}")

    # Check stderr
    if stderr and stderr.strip():
        # Some tools write to stderr normally (git, curl) — only flag if
        # there's also a pattern match or non-zero exit
        for pattern in ERROR_PATTERNS:
            if pattern.search(stderr):
                is_error = True
                matched_patterns.append(f"stderr:{pattern.pattern}")
                break

    # Check stdout for error patterns
    for pattern in ERROR_PATTERNS:
        if pattern.search(stdout):
            is_error = True
            matched_patterns.append(f"stdout:{pattern.pattern}")
            break

    if not is_error:
        sys.exit(0)

    # Build error record
    error_lines = _extract_error_lines(combined_output)
    record = {
        "timestamp": datetime.now(timezone.utc).isoformat(),
        "command": command[:500],  # Truncate very long commands
        "exit_code": exit_code,
        "matched_patterns": matched_patterns[:5],
        "error_lines": error_lines,
        "stderr_excerpt": stderr[:300] if stderr else "",
    }

    # Ensure directory exists and append
    ERRORS_FILE.parent.mkdir(parents=True, exist_ok=True)
    try:
        with open(ERRORS_FILE, "a", encoding="utf-8") as f:
            f.write(json.dumps(record) + "\n")
    except OSError:
        pass  # Never fail the hook

    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""PreToolUse hook: Validate branch freshness before PR creation.

Blocks `gh pr create` if the feature branch is behind the base branch.

Exit codes:
  0 — allow (not gh pr create, or branch is up to date)
  2 — block (branch is behind base)
"""

import json
import os
import re
import subprocess
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from annunaki_log import log_pretooluse_block


def get_base_branch(command: str) -> str:
    """Extract --base flag value, default to 'main'."""
    match = re.search(r"--base\s+[\"']?(\S+)[\"']?", command)
    if match:
        return match.group(1)
    return "main"


def get_working_dir(command: str) -> str | None:
    """Extract the target directory from a leading cd in the command.

    Agent commands in worktrees typically look like:
        cd /tmp/worktree-path && gh pr create ...
    The hook process itself runs from the main repo cwd, so we need to
    detect the worktree path from the command and pass it to git via -C.
    """
    match = re.match(r"cd\s+[\"']?([^\s\"';&]+)[\"']?\s*&&", command)
    if match:
        path = match.group(1)
        if os.path.isdir(path):
            return path
    return None


def _git(
    args: list[str],
    working_dir: str | None,
    timeout: int = 30,
) -> subprocess.CompletedProcess:
    """Run a git command, using -C <dir> when a worktree path is provided."""
    cmd = ["git"]
    if working_dir:
        cmd.extend(["-C", working_dir])
    cmd.extend(args)
    return subprocess.run(cmd, capture_output=True, text=True, timeout=timeout)


def is_branch_fresh(base: str, working_dir: str | None = None) -> bool:
    """Check if HEAD contains the latest commit from origin/base."""
    try:
        # Fetch latest from origin
        _git(["fetch", "origin", base], working_dir, timeout=30)
        # Check if origin/base is an ancestor of HEAD
        result = _git(
            ["merge-base", "--is-ancestor", f"origin/{base}", "HEAD"],
            working_dir,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # If we can't check, allow
        return True


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        sys.exit(0)

    command = input_data.get("tool_input", {}).get("command", "")

    if not re.search(r"\bgh\s+pr\s+create\b", command):
        sys.exit(0)

    base = get_base_branch(command)
    working_dir = get_working_dir(command)

    if is_branch_fresh(base, working_dir):
        sys.exit(0)

    result = {
        "decision": "block",
        "reason": (
            f"BLOCKED: Your branch is behind origin/{base}. "
            f"Merge or rebase before creating a PR.\n"
            f"Run: git fetch origin && git merge origin/{base}\n\n"
            "This prevents merge conflicts and ensures CI runs against current code."
        ),
    }
    log_pretooluse_block("validate_branch_freshness", command, result["reason"])
    print(json.dumps(result))
    sys.exit(2)


if __name__ == "__main__":
    main()

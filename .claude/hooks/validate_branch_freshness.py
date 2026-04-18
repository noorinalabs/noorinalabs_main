#!/usr/bin/env python3
"""PreToolUse hook: Validate branch freshness before PR creation.

Blocks `gh pr create` if the feature branch is behind the base branch.

Input Language:
  Fires on:      PreToolUse Bash
  Matches:       gh pr create [--repo {OWNER/REPO}] [--base {BRANCH}] [...]
  Does NOT match: gh pr list, gh pr view, gh pr merge, gh pr checks, git push
  Flag pass-through:
    --repo   → if present and differs from the cwd-resolved repo, skip the
               freshness check with a warning (the local git state belongs
               to a different repo, so origin/{base} cannot be checked
               meaningfully). GitHub's branch-protection still gates the
               actual merge.
    --base   → the base branch name used for origin/{base} ancestry check.
               Defaults to "main".

Negative-match verification:
  Running `gh pr create --repo noorinalabs/noorinalabs-user-service ...` from
  cwd=noorinalabs-main MUST emit only a non-blocking warning (cross-repo
  skip), never a false "behind base" block. See is_cross_repo_target().

Exit codes:
  0 — allow (not gh pr create, cross-repo skip, or branch is up to date)
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


def extract_repo_from_command(command: str) -> str | None:
    """Extract --repo value (OWNER/REPO) from a gh command."""
    match = re.search(r"--repo\s+[\"']?(\S+?)[\"']?(?:\s|$)", command)
    if match:
        return match.group(1)
    return None


def get_cwd_repo() -> str | None:
    """Return cwd's OWNER/REPO via `gh repo view`. None if unavailable."""
    try:
        result = subprocess.run(
            ["gh", "repo", "view", "--json", "nameWithOwner"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        if result.returncode != 0:
            return None
        data = json.loads(result.stdout)
        name = data.get("nameWithOwner")
        return name if isinstance(name, str) and name else None
    except (subprocess.TimeoutExpired, json.JSONDecodeError, FileNotFoundError):
        return None


def is_cross_repo_target(target_repo: str | None) -> bool:
    """True when --repo points to a different repo than cwd.

    Returns False when target_repo is None (no --repo flag), when cwd's repo
    cannot be resolved (be permissive — skip the cross-repo shortcut and fall
    through to the regular check), or when target_repo matches cwd's repo.
    """
    if not target_repo:
        return False
    cwd_repo = get_cwd_repo()
    if cwd_repo is None:
        return False
    return target_repo.lower() != cwd_repo.lower()


def is_branch_fresh(base: str) -> bool:
    """Check if HEAD contains the latest commit from origin/base."""
    try:
        # Fetch latest from origin
        subprocess.run(
            ["git", "fetch", "origin", base],
            capture_output=True,
            text=True,
            timeout=30,
        )
        # Check if origin/base is an ancestor of HEAD
        result = subprocess.run(
            ["git", "merge-base", "--is-ancestor", f"origin/{base}", "HEAD"],
            capture_output=True,
            text=True,
            timeout=10,
        )
        return result.returncode == 0
    except (subprocess.TimeoutExpired, FileNotFoundError):
        # If we can't check, allow
        return True


def check(input_data: dict) -> dict | None:
    """Check branch freshness. Returns result dict if blocking, None if allowed."""
    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        return None

    command = input_data.get("tool_input", {}).get("command", "")

    if not re.search(r"\bgh\s+pr\s+create\b", command):
        return None

    target_repo = extract_repo_from_command(command)
    if is_cross_repo_target(target_repo):
        return {
            "decision": "allow",
            "systemMessage": (
                f"NOTE: Skipping branch-freshness check — --repo {target_repo} "
                "differs from the current working directory's repo. Local git "
                "state cannot validate freshness against a different repo. "
                "GitHub's branch-protection will still gate the merge."
            ),
        }

    base = get_base_branch(command)

    if is_branch_fresh(base):
        return None

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
    return result


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    result = check(input_data)
    if result is None:
        sys.exit(0)
    print(json.dumps(result))
    if result.get("decision") == "block":
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()

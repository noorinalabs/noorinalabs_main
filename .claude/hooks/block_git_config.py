#!/usr/bin/env python3
"""PreToolUse hook: Block git config write commands.

The charter mandates per-commit `-c` flags — never modify global or repo-level
git config. This hook blocks `git config` write commands while allowing reads
(--get, --get-all, --list, -l) which are needed by Makefile and other tooling.

Input Language
==============

Fires on:      PreToolUse Bash
Matches:       git [globals] config [args] (any compound-command segment)
Does NOT match:
    - `gh issue create --body-file /tmp/x.md` where the body file mentions
      "git config" in prose (#216). Tokenized via shlex so data-position
      "git config" cannot be confused with a command-position invocation.
    - `grep "git config" /tmp/x` — the literal phrase as an argument value.
    - `echo "see git config docs"` — prose.
    - `git -c user.name=X commit` — per-commit identity flags (the very
      pattern this hook directs callers to).
    - `git config --get user.name` and other read-only forms.

Flag pass-through:
    --get / --get-all / --get-regexp / --list / -l / --show-origin /
    --show-scope → read-only, allowed.
    Anything else on `git config` → write, blocked.

Exit codes:
  0 — allow (not a git config command, or a read-only operation)
  2 — block (git config write detected)
"""

from __future__ import annotations

import json
import os
import sys

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from _shell_parse import (  # noqa: E402
    find_git_subcommand,
    iter_command_segments,
    strip_heredocs,
    tokenize,
)
from annunaki_log import log_pretooluse_block  # noqa: E402

# Read-only flags that mark a `git config` invocation as harmless.
_READ_ONLY_FLAGS = {
    "--get",
    "--get-all",
    "--get-regexp",
    "--list",
    "-l",
    "--show-origin",
    "--show-scope",
}


def _is_git_config_write(segment: list[str]) -> bool:
    """True if `segment` is a `git config <write>` invocation.

    A read-only invocation (any token in `_READ_ONLY_FLAGS` present) returns
    False; everything else with subcommand `config` returns True.
    """
    decoded = find_git_subcommand(segment)
    if decoded is None:
        return False
    _globals, rest = decoded
    if not rest or rest[0] != "config":
        return False
    args = rest[1:]
    for arg in args:
        # Match exact token OR equals-form prefix (e.g. --get-regexp=foo).
        if arg in _READ_ONLY_FLAGS:
            return False
        for ro in _READ_ONLY_FLAGS:
            if arg.startswith(ro + "="):
                return False
    return True


def check(input_data: dict) -> dict | None:
    """Check for git config writes. None to allow, dict to block."""
    tool_name = input_data.get("tool_name", "")
    if tool_name != "Bash":
        return None

    command = input_data.get("tool_input", {}).get("command", "")

    cleaned = strip_heredocs(command)
    tokens = tokenize(cleaned)
    if tokens is None:
        return None  # parse failure → fail open

    triggered = False
    for segment in iter_command_segments(tokens):
        if _is_git_config_write(segment):
            triggered = True
            break

    if not triggered:
        return None

    result = {
        "decision": "block",
        "reason": (
            "BLOCKED: `git config` writes are prohibited by the charter (§ Commit Identity). "
            "Never modify global or repo-level git config. "
            "Use per-commit `-c` flags instead:\n"
            '  git -c user.name="Name" -c user.email="email@example.com" commit -m "..."\n'
            "Read-only operations (--get, --list, -l) are allowed.\n"
            "See .claude/team/charter.md § Commit Identity for the full identity table."
        ),
    }
    log_pretooluse_block("block_git_config", command, result["reason"])
    return result


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    result = check(input_data)
    if result and result.get("decision") == "block":
        print(json.dumps(result))
        sys.exit(2)
    sys.exit(0)


if __name__ == "__main__":
    main()

#!/usr/bin/env python3
"""PreToolUse hook: Block stale /tmp/* message/body files on commit/PR/issue commands.

Refuses commands of the form ``git commit -F /tmp/...`` and ``gh {pr,issue}
{create,comment} --body-file /tmp/...`` when the target file's mtime is older
than ~30s. Such files are almost always leftovers from a prior task or session
that the current command is about to consume by mistake — see
``feedback_tmp_msg_file_stale.md`` for the three documented surfaces and the
2026-05-03 ontology-rebuild recurrence that motivated this hook.

Override paths the user can take when blocked:
  - rename the file to a non-/tmp path (e.g. .claude/scratch/msg.txt)
  - pass ``--message`` / ``--body`` inline instead of from a file
  - use a /tmp path that is genuinely fresh (Write the file again, then re-run
    the command — the freshness window resets to the new mtime)

The 30-second threshold is configurable via the ``STALE_TMP_THRESHOLD_SECONDS``
constant. Chosen as a balance between: long enough that a Write+Bash batched
in parallel always passes (Bash sees the file at <1s mtime), short enough that
a leftover file from a prior task in the same session is reliably caught.

Exit codes:
  0 — allow (no /tmp/* body-file argument, or file is fresh, or file missing)
  2 — block (target file mtime older than threshold)
"""

import json
import os
import re
import sys
import time
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))
from annunaki_log import log_pretooluse_block

STALE_TMP_THRESHOLD_SECONDS = 30

# Capture the path argument following each known body-file flag. The patterns
# look for `-F`, `--file`, `--body-file` followed by a /tmp/... path. We allow
# either a quoted or bare path, and we deliberately do NOT match the `=` form
# (e.g. `--body-file=/tmp/x`) — none of the supported callers (git commit / gh)
# use that form. Path capture stops at the first whitespace or shell operator.
_PATH_CHARS = r"[^\s;&|<>()`\"']+"

# Path captures for the file-flag patterns. We do NOT try to enclose the entire
# `git ... commit ... -F path` in a single regex — quoted args (e.g.
# `-c user.name="Aino Virtanen"`) defeat naive `\S+` skipping. Instead we split
# the command on shell separators (&&, ||, ;, |) to get one logical command per
# segment, decide whether the segment is a `git commit` or `gh {pr,issue}
# {create,comment,edit}` invocation, and only THEN look for the body-file flag
# anywhere in that segment.
_BODY_FILE_FLAG_RE = re.compile(
    rf"\s(?:-F|--file|--body-file)\s+(?P<path>{_PATH_CHARS})",
)

_SEGMENT_SPLIT_RE = re.compile(r"&&|\|\||;|(?<![|])\|(?![|])")

_GIT_COMMIT_RE = re.compile(r"\bgit\b[^\n]*?\bcommit\b")
_GH_BODY_RE = re.compile(r"\bgh\b\s+(?:pr|issue)\s+(?:create|comment|edit)\b")


def _segment_uses_body_file(segment: str) -> bool:
    """True if this shell segment is a git-commit or gh-body command we cover."""
    return bool(_GIT_COMMIT_RE.search(segment) or _GH_BODY_RE.search(segment))


def _extract_tmp_paths(command: str) -> list[str]:
    """Return /tmp/* paths supplied to git-commit -F or gh --body-file."""
    paths: list[str] = []
    for segment in _SEGMENT_SPLIT_RE.split(command):
        if not _segment_uses_body_file(segment):
            continue
        for match in _BODY_FILE_FLAG_RE.finditer(segment):
            raw = match.group("path").strip("\"'")
            if raw.startswith("/tmp/"):
                paths.append(raw)
    return paths


def _is_stale(path: str, now: float | None = None) -> bool:
    """True if the file exists and its mtime is older than the threshold."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        # File doesn't exist (or stat fails). The downstream command will
        # surface its own error; not our job to pre-empt that.
        return False
    cutoff = (now if now is not None else time.time()) - STALE_TMP_THRESHOLD_SECONDS
    return mtime < cutoff


def _format_age(path: str, now: float | None = None) -> str:
    """Human-friendly age string like '4m 12s ago' for the error message."""
    try:
        mtime = os.path.getmtime(path)
    except OSError:
        return "unknown age"
    age = (now if now is not None else time.time()) - mtime
    if age < 60:
        return f"{int(age)}s ago"
    if age < 3600:
        return f"{int(age // 60)}m {int(age % 60)}s ago"
    return f"{int(age // 3600)}h {int((age % 3600) // 60)}m ago"


def check(input_data: dict) -> dict | None:
    """Check for stale /tmp body-file args. Returns block dict or None."""
    if input_data.get("tool_name", "") != "Bash":
        return None

    command = input_data.get("tool_input", {}).get("command", "")
    if not command:
        return None

    tmp_paths = _extract_tmp_paths(command)
    if not tmp_paths:
        return None

    now = time.time()
    stale = [p for p in tmp_paths if _is_stale(p, now=now)]
    if not stale:
        return None

    offending = "\n".join(f"  - {p} (mtime {_format_age(p, now=now)})" for p in stale)
    result = {
        "decision": "block",
        "reason": (
            f"BLOCKED: stale /tmp/* file passed to git/gh body-file flag.\n"
            f"The following file(s) have an mtime older than "
            f"{STALE_TMP_THRESHOLD_SECONDS}s — likely leftovers from a prior "
            f"task or session:\n"
            f"{offending}\n\n"
            "This is the /tmp/* race captured in `feedback_tmp_msg_file_stale.md`: "
            "a Write+Bash pair batched in parallel can let Bash consume a stale "
            "file written days ago. To proceed, take one of:\n"
            "  1. Re-write the message/body to the same path (Write tool) and re-run "
            "this command — the freshness window resets.\n"
            "  2. Use a non-/tmp path (e.g. .claude/scratch/msg.txt) so the hook "
            "no longer matches.\n"
            "  3. Pass the content inline with `--message`/`-m` (git) or "
            "`--body`/`-b` (gh) instead of from a file."
        ),
    }
    log_pretooluse_block("block_stale_tmp_message_file", command, result["reason"])
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

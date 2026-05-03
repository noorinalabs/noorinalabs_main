#!/usr/bin/env python3
"""Tests for block_stale_tmp_message_file hook.

Run: python3 -m pytest .claude/hooks/tests/test_block_stale_tmp_message_file.py -v
"""

from __future__ import annotations

import os
import sys
import tempfile
import time
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
_HOOKS_DIR = _HERE.parent
sys.path.insert(0, str(_HOOKS_DIR))

import block_stale_tmp_message_file as hook  # noqa: E402


def _bash(command: str) -> dict:
    return {"tool_name": "Bash", "tool_input": {"command": command}}


def _touch(path: str, age_seconds: float) -> None:
    """Create the file and stamp it with mtime = now - age_seconds."""
    Path(path).write_text("body", encoding="utf-8")
    target = time.time() - age_seconds
    os.utime(path, (target, target))


class FreshnessGateTests(unittest.TestCase):
    """Core acceptance: fresh allowed, stale blocked."""

    def test_fresh_tmp_file_allowed(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            msg = f"{td}/msg.txt"
            _touch(msg, age_seconds=1)  # well within threshold
            result = hook.check(_bash(f"git commit -F {msg}"))
            self.assertIsNone(result)

    def test_stale_tmp_file_blocked_for_git_commit_F(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            msg = f"{td}/msg.txt"
            _touch(msg, age_seconds=120)  # > 30s threshold
            result = hook.check(_bash(f"git commit -F {msg}"))
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result["decision"], "block")
            self.assertIn(msg, result["reason"])

    def test_stale_tmp_file_blocked_for_git_commit_long_file(self):
        """`git commit --file <path>` is the long form of -F and must also block."""
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            msg = f"{td}/msg.txt"
            _touch(msg, age_seconds=120)
            result = hook.check(_bash(f"git commit --file {msg}"))
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result["decision"], "block")

    def test_stale_tmp_file_blocked_for_gh_pr_create(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            body = f"{td}/body.md"
            _touch(body, age_seconds=120)
            cmd = f"gh pr create --title x --body-file {body}"
            result = hook.check(_bash(cmd))
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result["decision"], "block")

    def test_stale_tmp_file_blocked_for_gh_issue_create(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            body = f"{td}/body.md"
            _touch(body, age_seconds=120)
            cmd = f"gh issue create --title x --body-file {body}"
            result = hook.check(_bash(cmd))
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result["decision"], "block")

    def test_stale_tmp_file_blocked_for_gh_pr_comment(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            body = f"{td}/body.md"
            _touch(body, age_seconds=120)
            cmd = f"gh pr comment 42 --body-file {body}"
            result = hook.check(_bash(cmd))
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result["decision"], "block")

    def test_stale_tmp_file_blocked_for_gh_issue_comment(self):
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            body = f"{td}/body.md"
            _touch(body, age_seconds=120)
            cmd = f"gh issue comment 42 --body-file {body}"
            result = hook.check(_bash(cmd))
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result["decision"], "block")


class NonMatchingTests(unittest.TestCase):
    """Cases where the hook must stay out of the way."""

    def test_non_tmp_path_not_matched(self):
        """Stale file outside /tmp must not trigger — non-/tmp paths are safe.

        Use the cwd (test run dir) for the temp dir, since the system tempfile
        default is /tmp on Linux which would defeat the purpose of this test.
        """
        with tempfile.TemporaryDirectory(dir=os.getcwd()) as td:
            msg = f"{td}/msg.txt"
            _touch(msg, age_seconds=120)
            self.assertFalse(msg.startswith("/tmp/"))
            result = hook.check(_bash(f"git commit -F {msg}"))
            self.assertIsNone(result)

    def test_inline_message_flag_not_matched(self):
        """`git commit -m '...'` does not pass a file → not the hook's concern."""
        result = hook.check(_bash("git commit -m 'fix stuff'"))
        self.assertIsNone(result)

    def test_inline_body_flag_not_matched(self):
        """`gh pr create --body '...'` does not pass a file → not matched."""
        result = hook.check(_bash("gh pr create --title x --body 'inline body'"))
        self.assertIsNone(result)

    def test_non_bash_tool_not_matched(self):
        result = hook.check({"tool_name": "Edit", "tool_input": {"command": "anything"}})
        self.assertIsNone(result)

    def test_empty_command_not_matched(self):
        result = hook.check(_bash(""))
        self.assertIsNone(result)

    def test_missing_tmp_file_does_not_block(self):
        """A non-existent file must not block — let downstream surface its own error."""
        result = hook.check(_bash("git commit -F /tmp/does-not-exist-xyz.txt"))
        self.assertIsNone(result)

    def test_unrelated_git_subcommand_not_matched(self):
        """`git log --grep /tmp/foo` must not be misread as a body-file."""
        result = hook.check(_bash("git log --grep /tmp/foo"))
        self.assertIsNone(result)

    def test_gh_pr_view_not_matched(self):
        """`gh pr view` has no --body-file; stray /tmp mention must not block."""
        result = hook.check(_bash("gh pr view 42 > /tmp/out.txt"))
        self.assertIsNone(result)

    def test_git_commit_with_identity_flags_and_fresh_file_allowed(self):
        """Realistic charter-format commit with -c identity flags + fresh -F file."""
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            msg = f"{td}/msg.txt"
            _touch(msg, age_seconds=1)
            cmd = (
                'git -c user.name="Aino Virtanen" '
                '-c user.email="parametrization+Aino.Virtanen@gmail.com" '
                f"commit -F {msg}"
            )
            result = hook.check(_bash(cmd))
            self.assertIsNone(result)

    def test_git_commit_with_quoted_identity_flags_and_stale_file_blocked(self):
        """Regression: quoted -c values containing spaces must not defeat detection.

        The first cut of this hook used `(?:\\s+-c\\s+\\S+)*` to skip leading -c
        flags, which silently failed once a value like
        `user.name="Aino Virtanen"` introduced a space inside the arg. The
        end-to-end dispatcher invocation surfaced that the hook never matched.
        """
        with tempfile.TemporaryDirectory(dir="/tmp") as td:
            msg = f"{td}/msg.txt"
            _touch(msg, age_seconds=120)
            cmd = (
                'git -c user.name="Aino Virtanen" '
                '-c user.email="parametrization+Aino.Virtanen@gmail.com" '
                f"commit -F {msg}"
            )
            result = hook.check(_bash(cmd))
            self.assertIsNotNone(result)
            assert result is not None
            self.assertEqual(result["decision"], "block")
            self.assertIn(msg, result["reason"])


class ExtractionTests(unittest.TestCase):
    """Direct coverage of _extract_tmp_paths regex behavior."""

    def test_extracts_git_F_path(self):
        self.assertEqual(
            hook._extract_tmp_paths("git commit -F /tmp/msg.txt"),
            ["/tmp/msg.txt"],
        )

    def test_extracts_gh_body_file_path(self):
        self.assertEqual(
            hook._extract_tmp_paths("gh pr create --body-file /tmp/body.md --title x"),
            ["/tmp/body.md"],
        )

    def test_skips_non_tmp_paths(self):
        self.assertEqual(
            hook._extract_tmp_paths("git commit -F .claude/scratch/msg.txt"),
            [],
        )

    def test_extracts_multiple_paths_in_compound_command(self):
        cmd = "git commit -F /tmp/a.txt && gh pr create --title x --body-file /tmp/b.md"
        self.assertEqual(
            sorted(hook._extract_tmp_paths(cmd)),
            ["/tmp/a.txt", "/tmp/b.md"],
        )


if __name__ == "__main__":
    unittest.main()

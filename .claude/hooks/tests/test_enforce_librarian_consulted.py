#!/usr/bin/env python3
"""Tests for enforce_librarian_consulted hook.

Covers the W8 hook-authorship-spec requirement: NEGATIVE MATCH coverage.
Each test documents which negative-space case it guards against.

Run: python3 -m pytest .claude/hooks/tests/test_enforce_librarian_consulted.py -v
Or:  python3 .claude/hooks/tests/test_enforce_librarian_consulted.py
"""

from __future__ import annotations

import json
import os
import sys
import tempfile
import unittest
from pathlib import Path

# Put the hooks dir on sys.path so we can import the hook module.
_HERE = Path(__file__).resolve().parent
_HOOKS_DIR = _HERE.parent
sys.path.insert(0, str(_HOOKS_DIR))

import enforce_librarian_consulted as hook  # noqa: E402


def _write_transcript(lines: list[dict]) -> str:
    """Write transcript lines to a temp file, return its path."""
    fd, path = tempfile.mkstemp(suffix=".jsonl", prefix="librarian_test_")
    with os.fdopen(fd, "w", encoding="utf-8") as f:
        for obj in lines:
            f.write(json.dumps(obj) + "\n")
    return path


def _librarian_user_line(text: str = "/ontology-librarian narrator API") -> dict:
    """User message with a slash-command invocation (string content form)."""
    return {
        "type": "user",
        "message": {
            "role": "user",
            "content": (
                "<command-message>ontology-librarian</command-message>\n"
                f"<command-name>{text}</command-name>"
            ),
        },
    }


def _librarian_skill_call() -> dict:
    """Assistant tool_use invoking the Skill tool with ontology-librarian."""
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "name": "Skill",
                    "input": {"skill": "ontology-librarian", "args": "hooks"},
                }
            ],
        },
    }


def _unrelated_user_text() -> dict:
    return {
        "type": "user",
        "message": {"role": "user", "content": [{"type": "text", "text": "please fix the bug"}]},
    }


def _unrelated_skill_call() -> dict:
    return {
        "type": "assistant",
        "message": {
            "role": "assistant",
            "content": [
                {
                    "type": "tool_use",
                    "name": "Skill",
                    "input": {"skill": "ontology-rebuild"},
                }
            ],
        },
    }


class AllowListTests(unittest.TestCase):
    """Paths that should NEVER require a librarian (negative-match cases)."""

    def _transcript_no_librarian(self) -> str:
        return _write_transcript([_unrelated_user_text(), _unrelated_skill_call()])

    def test_tmp_path_allowed_without_librarian(self) -> None:
        """NEG: /tmp/foo.md edits must not fire — out-of-repo scratch."""
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/tmp/foo.md"},
                "transcript_path": self._transcript_no_librarian(),
            }
        )
        self.assertIsNone(result, "edits under /tmp must be allowed without librarian")

    def test_memory_md_allowed_without_librarian(self) -> None:
        """NEG: MEMORY.md (any location) is the auto-memory index, not code."""
        result = hook.check(
            {
                "tool_name": "Write",
                "tool_input": {
                    "file_path": "/home/parameterization/.claude/projects/proj/memory/MEMORY.md"
                },
                "transcript_path": self._transcript_no_librarian(),
            }
        )
        self.assertIsNone(result, "MEMORY.md must be allowed without librarian")

    def test_memory_subdir_allowed_without_librarian(self) -> None:
        """NEG: files under .../memory/ are project memory, not code."""
        result = hook.check(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "/anywhere/memory/handoff.md"},
                "transcript_path": self._transcript_no_librarian(),
            }
        )
        self.assertIsNone(result, "memory/ files must be allowed")

    def test_user_claude_config_allowed_without_librarian(self) -> None:
        """NEG: ~/.claude/** is user config, not source code."""
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": os.path.expanduser("~/.claude/preferences.json")},
                "transcript_path": self._transcript_no_librarian(),
            }
        )
        self.assertIsNone(result, "~/.claude/** must be allowed")

    def test_annunaki_error_log_allowed_without_librarian(self) -> None:
        """NEG: .claude/annunaki/errors.jsonl is hook-managed, not hand-edited."""
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/repo/.claude/annunaki/errors.jsonl",
                },
                "transcript_path": self._transcript_no_librarian(),
            }
        )
        self.assertIsNone(result, ".claude/annunaki/ must be allowed")


class NonMatchedToolTests(unittest.TestCase):
    """Tools OTHER than Edit/Write/NotebookEdit must never block."""

    def test_bash_does_not_block(self) -> None:
        """NEG: Bash is not in the matcher set — must return None."""
        result = hook.check(
            {
                "tool_name": "Bash",
                "tool_input": {"command": "ls"},
                "transcript_path": _write_transcript([]),
            }
        )
        self.assertIsNone(result)

    def test_read_does_not_block(self) -> None:
        """NEG: Read is not a code-change tool; must not match."""
        result = hook.check(
            {
                "tool_name": "Read",
                "tool_input": {"file_path": "/anywhere/code.py"},
                "transcript_path": _write_transcript([]),
            }
        )
        self.assertIsNone(result)

    def test_grep_does_not_block(self) -> None:
        """NEG: Grep is read-only discovery, not a code-change tool."""
        result = hook.check(
            {
                "tool_name": "Grep",
                "tool_input": {"pattern": "foo"},
                "transcript_path": _write_transcript([]),
            }
        )
        self.assertIsNone(result)


class BlockingTests(unittest.TestCase):
    """In-scope code edits without librarian must BLOCK."""

    def test_compose_edit_without_librarian_blocks(self) -> None:
        """POS: the canonical case from #150 — compose edit without librarian."""
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/repo/noorinalabs-deploy/compose/docker-compose.prod.yml"
                },
                "transcript_path": _write_transcript(
                    [_unrelated_user_text(), _unrelated_skill_call()]
                ),
            }
        )
        assert result is not None  # mypy narrowing
        self.assertEqual(result["decision"], "block")
        self.assertIn("/ontology-librarian", result["reason"])

    def test_notebook_edit_without_librarian_blocks(self) -> None:
        """POS: NotebookEdit is in the matcher set."""
        result = hook.check(
            {
                "tool_name": "NotebookEdit",
                "tool_input": {"notebook_path": "/repo/analysis.ipynb"},
                "transcript_path": _write_transcript([]),
            }
        )
        assert result is not None  # mypy narrowing
        self.assertEqual(result["decision"], "block")

    def test_write_on_charter_blocks_without_librarian(self) -> None:
        """POS: .claude/team/ files are project state — require librarian.

        (Stance documented in the hook docstring: meta-files require librarian.)
        """
        result = hook.check(
            {
                "tool_name": "Write",
                "tool_input": {"file_path": "/repo/.claude/team/feedback_log.md"},
                "transcript_path": _write_transcript([]),
            }
        )
        assert result is not None  # mypy narrowing
        self.assertEqual(result["decision"], "block")

    def test_empty_transcript_blocks_real_code_edit(self) -> None:
        """POS: no transcript evidence -> block."""
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/repo/src/foo.py"},
                "transcript_path": _write_transcript([]),
            }
        )
        assert result is not None  # mypy narrowing
        self.assertEqual(result["decision"], "block")


class AllowWithLibrarianTests(unittest.TestCase):
    """Transcripts WITH a librarian call must allow in-scope edits."""

    def test_compose_edit_with_slash_command_allowed(self) -> None:
        """POS: same compose path, but transcript has /ontology-librarian user line."""
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/repo/noorinalabs-deploy/compose/docker-compose.prod.yml"
                },
                "transcript_path": _write_transcript(
                    [_librarian_user_line(), _unrelated_user_text()]
                ),
            }
        )
        self.assertIsNone(result, "librarian consulted -> edit must be allowed")

    def test_compose_edit_with_skill_call_allowed(self) -> None:
        """POS: librarian invoked via Skill tool -> allow."""
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {
                    "file_path": "/repo/noorinalabs-deploy/compose/docker-compose.prod.yml"
                },
                "transcript_path": _write_transcript([_librarian_skill_call()]),
            }
        )
        self.assertIsNone(result)

    def test_librarian_anywhere_in_transcript_counts(self) -> None:
        """POS: librarian invocation need only exist somewhere in the session."""
        lines = [
            _unrelated_user_text(),
            _unrelated_skill_call(),
            _librarian_skill_call(),
            _unrelated_user_text(),
        ]
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/repo/src/code.py"},
                "transcript_path": _write_transcript(lines),
            }
        )
        self.assertIsNone(result)


class FailOpenTests(unittest.TestCase):
    """If we cannot read the transcript, FAIL OPEN (don't block on our own bug)."""

    def test_missing_transcript_file_fails_open(self) -> None:
        """NEG-shape: nonexistent transcript path -> return None (false returned
        from _transcript_has_librarian in not-found case would actually BLOCK;
        OSError path fails open. Non-existence -> we cannot prove librarian was
        not called, but the strict choice here is to block; the function
        currently returns False for not-exists. Test the CURRENT stance so a
        future change is deliberate.)"""
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/repo/src/code.py"},
                "transcript_path": "/nonexistent/transcript.jsonl",
            }
        )
        # Current stance: missing file -> block (strict).
        assert result is not None  # mypy narrowing
        self.assertEqual(result["decision"], "block")

    def test_no_transcript_path_blocks(self) -> None:
        """NEG-shape: empty transcript_path -> block (no evidence = no librarian)."""
        result = hook.check(
            {
                "tool_name": "Edit",
                "tool_input": {"file_path": "/repo/src/code.py"},
                "transcript_path": "",
            }
        )
        assert result is not None  # mypy narrowing
        self.assertEqual(result["decision"], "block")


class SignalDetectionTests(unittest.TestCase):
    """Unit-level tests for _content_has_librarian_signal."""

    def test_string_content_with_slash_command(self) -> None:
        self.assertTrue(hook._content_has_librarian_signal("please run /ontology-librarian hooks"))

    def test_string_content_without_slash_command(self) -> None:
        self.assertFalse(hook._content_has_librarian_signal("please run /ontology-rebuild"))

    def test_text_block_with_slash_command(self) -> None:
        self.assertTrue(
            hook._content_has_librarian_signal(
                [{"type": "text", "text": "/ontology-librarian foo"}]
            )
        )

    def test_skill_call_with_librarian(self) -> None:
        self.assertTrue(
            hook._content_has_librarian_signal(
                [
                    {
                        "type": "tool_use",
                        "name": "Skill",
                        "input": {"skill": "ontology-librarian"},
                    }
                ]
            )
        )

    def test_skill_call_with_different_skill_rejected(self) -> None:
        """NEG: Skill tool with a DIFFERENT skill name must not trigger."""
        self.assertFalse(
            hook._content_has_librarian_signal(
                [
                    {
                        "type": "tool_use",
                        "name": "Skill",
                        "input": {"skill": "ontology-rebuild"},
                    }
                ]
            )
        )

    def test_other_tool_use_ignored(self) -> None:
        """NEG: tool_use blocks for non-Skill tools are irrelevant."""
        self.assertFalse(
            hook._content_has_librarian_signal(
                [
                    {
                        "type": "tool_use",
                        "name": "Bash",
                        "input": {"command": "/ontology-librarian"},
                    }
                ]
            )
        )


if __name__ == "__main__":
    unittest.main(verbosity=2)

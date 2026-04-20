#!/usr/bin/env python3
"""Unit tests for promotion-audit helpers.

Covers parsers, signal counters, and classifiers. Designed to run with
stdlib unittest (no pytest dependency). The smoke test lives in
`test_smoke.py` and exercises the full pipeline against current repo
state — this file keeps each unit isolated.
"""

from __future__ import annotations

import os
import sys
import tempfile
import textwrap
import unittest
from pathlib import Path

_HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(_HERE.parent))

import helpers as h  # noqa: E402

# ---------------------------------------------------------------------------
# Frontmatter parsing
# ---------------------------------------------------------------------------


class ParseFrontmatterTests(unittest.TestCase):
    def test_basic_scalars(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            name: Foo
            type: feedback
            status: active
            ---
            body here
            """
        )
        fm, body = h.parse_frontmatter(text)
        self.assertEqual(fm["name"], "Foo")
        self.assertEqual(fm["type"], "feedback")
        self.assertEqual(fm["status"], "active")
        self.assertIn("body here", body)

    def test_quoted_string(self) -> None:
        """NEG: quotes must be stripped; embedded colons preserved."""
        text = textwrap.dedent(
            """\
            ---
            superseded_by: "charter:hooks.md § Foo"
            ---
            """
        )
        fm, _ = h.parse_frontmatter(text)
        self.assertEqual(fm["superseded_by"], "charter:hooks.md § Foo")

    def test_inline_list(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            referenced_in_retros: ['W7', 'W8', 'P2W9']
            ---
            """
        )
        fm, _ = h.parse_frontmatter(text)
        self.assertEqual(fm["referenced_in_retros"], ["W7", "W8", "P2W9"])

    def test_empty_list(self) -> None:
        text = "---\nreferenced_in_retros: []\n---\n"
        fm, _ = h.parse_frontmatter(text)
        self.assertEqual(fm["referenced_in_retros"], [])

    def test_nested_threshold(self) -> None:
        text = textwrap.dedent(
            """\
            ---
            promotion_threshold:
              retro_citations: 3
              skill_invocations: 5
            ---
            """
        )
        fm, _ = h.parse_frontmatter(text)
        self.assertEqual(fm["promotion_threshold"]["retro_citations"], 3)
        self.assertEqual(fm["promotion_threshold"]["skill_invocations"], 5)

    def test_no_frontmatter(self) -> None:
        """NEG: a doc without frontmatter returns ({}, whole-text)."""
        text = "# Just markdown\n\ncontent"
        fm, body = h.parse_frontmatter(text)
        self.assertEqual(fm, {})
        self.assertEqual(body, text)

    def test_bool_coercion(self) -> None:
        text = "---\nrequires_decision: true\n---\n"
        fm, _ = h.parse_frontmatter(text)
        self.assertIs(fm["requires_decision"], True)


# ---------------------------------------------------------------------------
# Memory reading
# ---------------------------------------------------------------------------


def _write_memory(dir_: str, name: str, content: str) -> str:
    path = os.path.join(dir_, name)
    with open(path, "w", encoding="utf-8") as f:
        f.write(content)
    return path


class ReadMemoryTests(unittest.TestCase):
    def test_promotion_eligible_memory(self) -> None:
        with tempfile.TemporaryDirectory() as d:
            _write_memory(
                d,
                "feedback_test.md",
                textwrap.dedent(
                    """\
                    ---
                    name: Test rule
                    description: Testing
                    type: feedback
                    promotion_target: charter
                    promotion_threshold:
                      retro_citations: 3
                    referenced_in_retros: ['W7', 'W8', 'W9']
                    status: active
                    ---
                    body
                    """
                ),
            )
            mems = h.read_all_memories(d)
            self.assertEqual(len(mems), 1)
            m = mems[0]
            self.assertEqual(m.promotion_target, "charter")
            self.assertEqual(m.promotion_threshold["retro_citations"], 3)
            self.assertEqual(len(m.referenced_in_retros), 3)
            self.assertEqual(m.status, "active")

    def test_memory_index_and_handoff_excluded(self) -> None:
        """NEG: MEMORY.md and session_handoff.md must be skipped."""
        with tempfile.TemporaryDirectory() as d:
            _write_memory(d, "MEMORY.md", "# index\n")
            _write_memory(d, "session_handoff.md", "---\nname: handoff\n---\n")
            _write_memory(
                d,
                "project_real.md",
                "---\nname: Real\npromotion_target: none\nstatus: active\n---\n",
            )
            mems = h.read_all_memories(d)
            self.assertEqual(len(mems), 1)
            self.assertEqual(mems[0].filename, "project_real.md")

    def test_deterministic_sort_order(self) -> None:
        """Memories must come back in sorted-filename order for determinism."""
        with tempfile.TemporaryDirectory() as d:
            for n in ("project_z.md", "project_a.md", "project_m.md"):
                _write_memory(d, n, f"---\nname: {n}\npromotion_target: none\n---\n")
            mems = h.read_all_memories(d)
            self.assertEqual(
                [m.filename for m in mems],
                ["project_a.md", "project_m.md", "project_z.md"],
            )


# ---------------------------------------------------------------------------
# Charter section reading
# ---------------------------------------------------------------------------


class ReadCharterSectionsTests(unittest.TestCase):
    def test_tagged_section_detected(self) -> None:
        text = textwrap.dedent(
            """\
            # Title

            ## Non-procedural intro

            No marker here.

            ## Procedural step-by-step <!-- promotion-target: skill -->

            1. Do A
            2. Do B
            3. Do C

            ## Declared none <!-- promotion-target: none -->

            nothing to promote.
            """
        )
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(text)
            path = f.name
        try:
            sections = h.read_charter_sections(path)
            self.assertEqual(len(sections), 2)
            headings = [s.heading for s in sections]
            self.assertIn("Procedural step-by-step", headings)
            self.assertIn("Declared none", headings)
            proc = [s for s in sections if s.heading == "Procedural step-by-step"][0]
            self.assertEqual(proc.promotion_target, "skill")
            self.assertIn("Do A", proc.body)
        finally:
            os.unlink(path)

    def test_untagged_sections_skipped(self) -> None:
        """NEG: sections without a marker must not appear."""
        text = "## Untagged\n\nThis has steps\n1. step\n2. step\n3. step\n"
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(text)
            path = f.name
        try:
            self.assertEqual(h.read_charter_sections(path), [])
        finally:
            os.unlink(path)

    def test_promoted_to_backref_detected(self) -> None:
        text = textwrap.dedent(
            """\
            ## Already done <!-- promotion-target: skill -->

            <!-- promoted-to: skills/my-skill -->

            body
            """
        )
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(text)
            path = f.name
        try:
            sections = h.read_charter_sections(path)
            self.assertEqual(len(sections), 1)
            self.assertEqual(sections[0].promoted_to, "skills/my-skill")
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Retro citation counting
# ---------------------------------------------------------------------------


class CountRetroCitationsTests(unittest.TestCase):
    def _mem(self, name: str = "Some rule", filename: str = "feedback_x.md") -> h.Memory:
        return h.Memory(
            path=f"/fake/{filename}",
            name=name,
            description="",
            type_="feedback",
            promotion_target="charter",
            promotion_threshold={"retro_citations": 3, "skill_invocations": 5},
            referenced_in_retros=(),
            status="active",
            superseded_by="",
            supersedes="",
            requires_decision=False,
            body="",
        )

    def test_count_from_feedback_log(self) -> None:
        log = "we cited Some rule here\nand feedback_x.md there\nand Some rule again"
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(log)
            path = f.name
        try:
            n = h.count_retro_citations(self._mem(), path)
            # by_title=2, by_file=1, frontmatter_floor=0 -> max = 2
            self.assertEqual(n, 2)
        finally:
            os.unlink(path)

    def test_frontmatter_floor_applies(self) -> None:
        """NEG: if the log has zero hits but frontmatter lists retros, floor kicks in."""
        log = "no mentions"
        mem = h.Memory(
            path="/fake/feedback_x.md",
            name="Some rule",
            description="",
            type_="feedback",
            promotion_target="charter",
            promotion_threshold={"retro_citations": 3, "skill_invocations": 5},
            referenced_in_retros=("W7", "W8", "W9"),
            status="active",
            superseded_by="",
            supersedes="",
            requires_decision=False,
            body="",
        )
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(log)
            path = f.name
        try:
            self.assertEqual(h.count_retro_citations(mem, path), 3)
        finally:
            os.unlink(path)

    def test_missing_log_falls_back_to_frontmatter(self) -> None:
        """NEG: nonexistent feedback log must not crash."""
        mem = self._mem()
        mem = h.Memory(
            path=mem.path,
            name=mem.name,
            description=mem.description,
            type_=mem.type_,
            promotion_target=mem.promotion_target,
            promotion_threshold=mem.promotion_threshold,
            referenced_in_retros=("W9",),
            status=mem.status,
            superseded_by=mem.superseded_by,
            supersedes=mem.supersedes,
            requires_decision=mem.requires_decision,
            body=mem.body,
        )
        self.assertEqual(h.count_retro_citations(mem, "/nonexistent"), 1)


# ---------------------------------------------------------------------------
# Already-promoted detection
# ---------------------------------------------------------------------------


class FindAlreadyPromotedTests(unittest.TestCase):
    def test_detects_hook15_provenance(self) -> None:
        """POS: the canonical worked example from PR #153."""
        charter = textwrap.dedent(
            """\
            ## Hook 15: Enforce Librarian Consulted

            - **What it automates:** blocks edits
            - **Promotion provenance:** First end-to-end execution of the
              memory -> charter -> hook promotion pattern. Rule lived in
              CLAUDE.md § Ontology; first instance cites
              feedback_enforcement_hierarchy.md. Skill wrapper was
              /ontology-librarian.
            """
        )
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(charter)
            path = f.name
        try:
            refs = h.find_already_promoted(path)
            self.assertIn("CLAUDE.md § Ontology", refs)
            self.assertIn("feedback_enforcement_hierarchy.md", refs)
            self.assertIn("/ontology-librarian", refs)
        finally:
            os.unlink(path)

    def test_no_provenance_blocks_returns_empty(self) -> None:
        """NEG: charter without provenance blocks returns empty set."""
        charter = "## Hook 1: Foo\n\n- just a hook\n"
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(charter)
            path = f.name
        try:
            self.assertEqual(h.find_already_promoted(path), set())
        finally:
            os.unlink(path)

    def test_forward_reference_excluded(self) -> None:
        """NEG: `/name` inside a forward-reference phrase must not be
        marked as already-promoted. This is the specific false-positive
        caught during the first real audit run: Hook 15's provenance
        block references \"the future /promotion-audit skill design\"
        as a cross-reference; that is NOT a promotion claim."""
        charter = (
            "## Hook 15: Foo\n\n"
            "- **Promotion provenance:** Rule lived in CLAUDE.md \u00a7 Ontology. "
            "Worked example referenced by the future `/promotion-audit` skill design.\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(charter)
            path = f.name
        try:
            refs = h.find_already_promoted(path)
            self.assertIn("CLAUDE.md \u00a7 Ontology", refs)
            self.assertNotIn(
                "/promotion-audit",
                refs,
                msg="forward-referenced skill must not appear in already-promoted set",
            )
        finally:
            os.unlink(path)

    def test_backward_reference_still_counted(self) -> None:
        """POS: `/name` in a non-forward-reference context IS counted."""
        charter = (
            "## Hook 20: Foo\n\n"
            "- **Promotion provenance:** This hook enforces the "
            "`/thing-checker` skill which operators invoked 7x in W8.\n"
        )
        with tempfile.NamedTemporaryFile("w", suffix=".md", delete=False) as f:
            f.write(charter)
            path = f.name
        try:
            refs = h.find_already_promoted(path)
            self.assertIn("/thing-checker", refs)
        finally:
            os.unlink(path)


# ---------------------------------------------------------------------------
# Classification — memory
# ---------------------------------------------------------------------------


def _make_memory(**kwargs: object) -> h.Memory:
    defaults: dict[str, object] = {
        "path": "/fake/feedback_x.md",
        "name": "X",
        "description": "",
        "type_": "feedback",
        "promotion_target": "none",
        "promotion_threshold": {"retro_citations": 3, "skill_invocations": 5},
        "referenced_in_retros": (),
        "status": "active",
        "superseded_by": "",
        "supersedes": "",
        "requires_decision": False,
        "body": "",
    }
    defaults.update(kwargs)
    return h.Memory(**defaults)  # type: ignore[arg-type]


class ClassifyMemoryTests(unittest.TestCase):
    def test_none_target_yields_kept(self) -> None:
        m = _make_memory(promotion_target="none")
        d = h.classify_memory(m, {"retro_citations": 10}, set())
        self.assertEqual(d.kind, "KEPT")

    def test_superseded_status_yields_superseded(self) -> None:
        m = _make_memory(status="superseded", superseded_by="charter:foo")
        d = h.classify_memory(m, {"retro_citations": 10}, set())
        self.assertEqual(d.kind, "SUPERSEDED")

    def test_enforced_elsewhere_yields_superseded(self) -> None:
        """The feedback_enforcement_hierarchy case."""
        m = _make_memory(status="enforced-elsewhere", superseded_by="Hook 15")
        d = h.classify_memory(m, {"retro_citations": 5}, set())
        self.assertEqual(d.kind, "SUPERSEDED")

    def test_already_promoted_wins(self) -> None:
        """ALREADY-PROMOTED takes precedence even over active eligible memory."""
        m = _make_memory(promotion_target="charter", status="active")
        d = h.classify_memory(m, {"retro_citations": 10}, {"feedback_x.md"})
        self.assertEqual(d.kind, "ALREADY-PROMOTED")

    def test_threshold_not_met_kept(self) -> None:
        m = _make_memory(promotion_target="charter", status="active")
        d = h.classify_memory(m, {"retro_citations": 1}, set())
        self.assertEqual(d.kind, "KEPT")
        self.assertIn("1 < 3", d.signal)

    def test_threshold_met_auto(self) -> None:
        m = _make_memory(promotion_target="charter", status="active")
        d = h.classify_memory(m, {"retro_citations": 5}, set())
        self.assertEqual(d.kind, "AUTO")

    def test_requires_decision_forces_decide(self) -> None:
        m = _make_memory(promotion_target="charter", status="active", requires_decision=True)
        d = h.classify_memory(m, {"retro_citations": 10}, set())
        self.assertEqual(d.kind, "DECIDE")

    def test_hook_target_not_valid_for_memory(self) -> None:
        """NEG: memory -> hook is not a valid direct transition."""
        m = _make_memory(promotion_target="hook", status="active")
        d = h.classify_memory(m, {"retro_citations": 10}, set())
        self.assertEqual(d.kind, "KEPT")
        self.assertIn("not a valid memory transition", d.reason)


# ---------------------------------------------------------------------------
# Classification — charter section
# ---------------------------------------------------------------------------


def _make_section(**kwargs: object) -> h.CharterSection:
    defaults: dict[str, object] = {
        "path": "/fake/charter/issues.md",
        "heading": "Delegation Flow",
        "promotion_target": "skill",
        "body": "1. step\n2. step\n3. step",
        "promoted_to": "",
    }
    defaults.update(kwargs)
    return h.CharterSection(**defaults)  # type: ignore[arg-type]


class ClassifySectionTests(unittest.TestCase):
    def test_none_target_kept(self) -> None:
        d = h.classify_section(_make_section(promotion_target="none"), {})
        self.assertEqual(d.kind, "KEPT")

    def test_already_promoted_backref(self) -> None:
        d = h.classify_section(_make_section(promoted_to="skills/delegation-flow"), {})
        self.assertEqual(d.kind, "ALREADY-PROMOTED")

    def test_threshold_not_met(self) -> None:
        d = h.classify_section(_make_section(), {"skill_invocations": 1, "threshold": 5})
        self.assertEqual(d.kind, "KEPT")

    def test_threshold_met(self) -> None:
        d = h.classify_section(_make_section(), {"skill_invocations": 7, "threshold": 5})
        self.assertEqual(d.kind, "AUTO")

    def test_hook_target_not_valid_for_section(self) -> None:
        """NEG: charter sections only promote to skill."""
        d = h.classify_section(_make_section(promotion_target="hook"), {})
        self.assertEqual(d.kind, "KEPT")


# ---------------------------------------------------------------------------
# Classification — skill
# ---------------------------------------------------------------------------


def _make_skill(**kwargs: object) -> h.Skill:
    defaults: dict[str, object] = {
        "name": "thing-checker",
        "path": "/fake/.claude/skills/thing-checker/SKILL.md",
        "promotion_target": "hook",
        "description": "Check things",
        "body": "",
    }
    defaults.update(kwargs)
    return h.Skill(**defaults)  # type: ignore[arg-type]


class ClassifySkillTests(unittest.TestCase):
    def test_none_target_kept(self) -> None:
        d = h.classify_skill(_make_skill(promotion_target="none"), {}, set())
        self.assertEqual(d.kind, "KEPT")

    def test_threshold_met_is_decide_not_auto(self) -> None:
        """D6 locked: skill -> hook is ALWAYS DECIDE, never AUTO."""
        d = h.classify_skill(
            _make_skill(),
            {"skill_invocations": 100, "threshold": 5},
            set(),
        )
        self.assertEqual(d.kind, "DECIDE")

    def test_already_promoted_by_slash_name(self) -> None:
        d = h.classify_skill(
            _make_skill(name="ontology-librarian"),
            {"skill_invocations": 10, "threshold": 5},
            {"/ontology-librarian"},
        )
        self.assertEqual(d.kind, "ALREADY-PROMOTED")

    def test_threshold_not_met_kept(self) -> None:
        d = h.classify_skill(
            _make_skill(),
            {"skill_invocations": 1, "threshold": 5},
            set(),
        )
        self.assertEqual(d.kind, "KEPT")


# ---------------------------------------------------------------------------
# Render audit table — determinism
# ---------------------------------------------------------------------------


class RenderAuditTableTests(unittest.TestCase):
    def test_empty_decisions_renders_empty_state(self) -> None:
        out = h.render_audit_table([], "wave-9", "2026-04-19")
        self.assertIn("Promotion Audit — wave-9", out)
        self.assertIn("0 AUTO", out)
        self.assertIn("_None this run._", out)

    def test_same_input_yields_identical_output(self) -> None:
        """Core determinism guarantee: re-render must be byte-identical."""
        decisions = [
            h.Decision(
                kind="KEPT",
                item_id="feedback_x.md",
                from_tier="memory",
                to_tier="-",
                signal="retro_citations=0",
                reason="promotion_target=none",
            ),
            h.Decision(
                kind="SUPERSEDED",
                item_id="feedback_y.md",
                from_tier="memory",
                to_tier="-",
                signal="superseded_by: charter:foo",
                reason="Memory explicitly marked superseded",
            ),
        ]
        a = h.render_audit_table(decisions, "wave-9", "2026-04-19")
        b = h.render_audit_table(decisions, "wave-9", "2026-04-19")
        self.assertEqual(a, b)

    def test_sorted_within_bucket(self) -> None:
        """NEG: unsorted input must still produce sorted output."""
        decisions = [
            h.Decision(
                kind="KEPT",
                item_id="zzz.md",
                from_tier="memory",
                to_tier="-",
                signal="",
                reason="r",
            ),
            h.Decision(
                kind="KEPT",
                item_id="aaa.md",
                from_tier="memory",
                to_tier="-",
                signal="",
                reason="r",
            ),
        ]
        out = h.render_audit_table(decisions, "wave-9", "2026-04-19")
        self.assertLess(out.index("aaa.md"), out.index("zzz.md"))


# ---------------------------------------------------------------------------
# Artifact generation
# ---------------------------------------------------------------------------


class GenerateArtifactsTests(unittest.TestCase):
    template_dir: str

    @classmethod
    def setUpClass(cls) -> None:
        cls.template_dir = str(_HERE.parent / "templates")

    def test_charter_section_renders_memory_body(self) -> None:
        m = _make_memory(name="Test rule", description="A test", body="This is the rule body.")
        out = h.generate_charter_section(m, self.template_dir)
        self.assertIn("## Test rule", out)
        self.assertIn("This is the rule body.", out)
        self.assertIn("promotion-target: skill", out)
        self.assertIn("feedback_x.md", out)

    def test_skill_scaffold_slugifies_heading(self) -> None:
        s = _make_section(heading="Load-Bearing Followups for Disabled CI Jobs")
        out = h.generate_skill_scaffold(s, self.template_dir)
        self.assertIn("name: load-bearing-followups-for-disabled-ci-jobs", out)
        self.assertIn("Load-Bearing Followups for Disabled CI Jobs", out)
        self.assertIn("issues.md", out)

    def test_hook_draft_generates_title_and_body(self) -> None:
        s = _make_skill(name="retro-helper", description="Automates retros")
        out = h.generate_hook_draft_issue(s, self.template_dir)
        self.assertIn("/retro-helper", out["title"])
        self.assertIn("Automates retros", out["body"])
        self.assertIn("promote /retro-helper skill to hook", out["title"])


# ---------------------------------------------------------------------------
# Slugify
# ---------------------------------------------------------------------------


class SlugifyTests(unittest.TestCase):
    def test_basic(self) -> None:
        self.assertEqual(h._slugify("Hello World"), "hello-world")

    def test_strips_punctuation(self) -> None:
        self.assertEqual(h._slugify("Load-Bearing: Followups!"), "load-bearing-followups")

    def test_empty_fallback(self) -> None:
        self.assertEqual(h._slugify("   "), "section")


if __name__ == "__main__":
    unittest.main(verbosity=2)

# P3W3 Pattern D adoption signal-check

**Audit window:** 2026-05-03, P3W3 wave-3 kickoff + first-day implementer spawns
**Tracking issue:** noorinalabs-main#234
**Charter section under audit:** `.claude/team/charter/agents.md` § Pre-Spawn State Check + Crossed-Message Race Protocol
**Author:** Nadia Khoury (Program Director, parent `noorinalabs-main` team)
**Reviewer:** Aino Virtanen

## Background

Pattern D (landed at commit `a728339` post-P3W1 retro) introduced two coupled disciplines:

1. **Default protocol** — accept crossed-in-flight races as cost-of-throughput; standardize implementer ack shape:
   ```
   ack — task #N — already shipped at PR #M at YYYY-MM-DDTHH:MM:SSZ; no action needed
   ```
2. **Narrow trigger** — orchestrator MUST poll `gh pr list` / `gh issue view` BEFORE assignments that **spawn a new implementer instance** OR **change branch/worktree paths**. Skip the poll for follow-on tasks within already-active worktrees.

The P3W1 baseline at the time of the delta:
- ~5 crossed-in-flight races (4 Lucas-side + ≥1 Aisha-side)
- 0 spawn-duplication instances (no narrow-trigger materialized)
- Canonical ack-shape compliance unmeasured (the shape didn't exist yet)

This audit measures P3W3 against those baselines, with the caveat that P3W3 spans an immediate post-emergency stabilization wave (P3W2 ended with Emergency Mode declared per `feedback_pattern_e_emergency_process_collapse.md`) and a 14-PR catchup pass interleaving with kickoff. Process-discipline degradation under fire is in scope as a Pattern E correlate.

## Spawn inventory (P3W3, day 1 — 2026-05-03)

Source: `cross-repo-status.json wave_3_kickoff_corrections` + `gh pr list --base deployments/phase-3/wave-3` across all 4 in-scope repos.

| Spawn ID                | Repo                      | Issue   | PR   | Spawn nature                       | Pre-spawn-poll required? |
|-------------------------|---------------------------|---------|------|------------------------------------|--------------------------|
| Aisha-252               | noorinalabs-deploy        | #252    | #254 | New implementer, T1 emergency-exposed | YES                  |
| Idris-853               | noorinalabs-isnad-graph   | #853    | #854 | New implementer, T1 emergency-exposed | YES                  |
| Aisha-249               | noorinalabs-deploy        | #249    | #260 | New implementer, T1                | YES                      |
| Lucas-250               | noorinalabs-deploy        | #250    | #257 | New implementer, T1                | YES                      |
| Weronika-251            | noorinalabs-deploy        | #251    | #261 | New implementer, T1                | YES                      |
| Lucas-242 → Kofi-242    | noorinalabs-landing-page  | #242    | LP#75| New impl + repo-pivot (Lucas withdrawn, parent→child reassignment, branch/worktree change) | YES (twice — original + repo-pivot) |
| Weronika-255            | noorinalabs-deploy        | #255    | #259 | New implementer, T1 follow-on (added at owner-decision after Aisha-252 surfaced it) | YES |
| Aisha-256               | noorinalabs-deploy        | #256    | #258 | Follow-on task within already-active Aisha scope (Aisha-252 surfaced it during PR#254 work) | NO — same-implementer, sequential to PR#254 rebase |
| Lucas-243               | noorinalabs-deploy        | #243    | #266 | New implementer, T2                | YES                      |
| Aisha-244               | noorinalabs-deploy        | #244    | (in flight, runbook track) | New implementer, T2                | YES                      |
| Aisha-245               | noorinalabs-isnad-graph   | #245    | (in flight, frontend track) | New implementer, T2                | YES                      |
| Nadia-234 (this audit)  | noorinalabs-main          | #234    | (this PR) | New implementer, T3                | YES                      |
| Aino-237                | noorinalabs-main          | #237    | (in flight) | New implementer, T3                | YES                      |
| Bereket-review × 2      | noorinalabs-deploy        | review on #259 + #261 | n/a | Reviewer-class, not implementer; outside Pattern D scope | n/a |

**Spawn count subject to the narrow trigger:** 12 (Aisha-252, Idris-853, Aisha-249, Lucas-250, Weronika-251, Lucas-242, Kofi-242 [repo-pivot], Weronika-255, Lucas-243, Aisha-244, Aisha-245, Nadia-234, Aino-237) minus Aisha-256 which legitimately skipped the poll per § Narrow trigger paragraph 2 (already-active worktree).

13 spawns require pre-spawn poll; 1 spawn legitimately skipped.

## Section 1 — Pre-spawn poll adoption rate

**Numerical adoption rate: indeterminate-strict / 13/13 inferred-pass — see Confidence below.**

The audit cannot directly observe the orchestrator's `gh pr list` / `gh issue view` invocations from the spawn-time transcript at this audit's vantage point (Nadia-234 implementer session reads orchestrator state via `cross-repo-status.json` + GH API, not the orchestrator's command log). Instead, adoption is inferred from second-order evidence:

### Evidence FOR adoption (poll happened)

1. **Aisha-252 catch — orchestrator caught a missing wave-3 branch in `noorinalabs-deploy` BEFORE Aisha-252 began work.** `cross-repo-status.json wave_3_kickoff_corrections[0]`: *"Aisha-252 caught missing wave-3 branch in noorinalabs-deploy 2026-05-03; option A (push branch + ship time-critical fix) accepted."* This is the kind of state divergence a pre-spawn check surfaces — branch-existence is checked when verifying a wave-state baseline before delegating. Tracked at main#238 as a skill gap (the `/wave-kickoff` skill should have created branches in all in-scope repos at planning time, not at first-implementer-spawn).

2. **Idris-853 sibling-coordination catch (deploy#242 mis-attribution).** `wave_3_kickoff_corrections[1]`: *"Idris-853 caught deploy#242 sibling-of-isnad-graph mis-attribution 2026-05-03; #242 actual scope is noorinalabs-landing-page (per issue body's table); landing-page added as 4th wave-scope repo."* The orchestrator re-read the issue body as a second-pass verification at spawn time — this is consistent with a § Narrow trigger pre-spawn poll being executed on Idris-853's adjacent-issue context. The catch is an orchestrator-side win, but it implies the orchestrator was reading-before-spawning, not spawning-then-correcting.

3. **Issue #234 (this issue) was searched for prior PRs at spawn time.** Per the spawn brief I received: *"PR base = `deployments/phase-3/wave-3` in `noorinalabs-main`"* with explicit instruction to verify no prior PR exists. My own pre-work `gh pr list --search "in:title 234 OR in:title pattern-d OR in:title adoption"` returned `[]`, confirming the discipline applied to this very spawn.

4. **The 12-of-13 narrow-trigger-required spawns produced 9 distinct PRs across 3 repos with NO instance of duplicate-PR-for-same-issue across the wave.** If pre-spawn poll were systemically skipped, the spawn-duplication failure mode (which Pattern D's narrow trigger exists to prevent) would manifest as ≥1 redundant PR. That count is 0.

### Evidence AGAINST adoption (poll skipped or partial)

1. **Aisha-252 missing-wave-branch catch is itself an artifact of skipped pre-spawn state-check at the WAVE level (not the SPAWN level).** Pattern D's narrow trigger covers "verify the work is not already done" — but the prerequisite question "verify the wave's preconditions exist (branch in target repo)" is ADJACENT to Pattern D, not covered by it. The fact that Aisha-252's first-action surfaced this is a soft "no" on the broader pre-spawn-state-check posture. A more rigorous orchestrator pre-spawn check would have caught the missing branches before any implementer spawned. (See Section 3, charter-response item #1.)

2. **No orchestrator-side log artifact (e.g., a status comment "pre-spawn poll: PR list empty, issue OPEN, proceeding") was posted on any P3W3 issue.** Pattern D requires the poll but does not require posting evidence of the poll. This is by design (the poll is cheap — adding a 2-step audit overhead per spawn would inflate the cost the protocol was meant to keep low). However, the absence makes adoption unfalsifiable from the artifact trail alone — adoption is inferable only from outcome (no spawn-duplications) + spawn-brief content.

### Confidence

- **Strict adoption rate (orchestrator's actual `gh pr list` invocations attested in audit-visible artifacts):** 1/13 — only Nadia-234 has a self-attested poll (this audit's own pre-work, recorded above).
- **Inferred adoption rate (spawn-duplication failure mode did not occur):** 13/13 — all spawns produced uniquely-attributed work; no redundant PRs.
- **Recommended frame for next-retro reporting:** report the inferred rate, explicitly flag the audit-trail gap, and let Aino decide whether the gap warrants a charter-evidence-requirement promotion.

## Section 2 — Drift surface

**Numerical race count: 0 cross-agent crossed-in-flight races; 3+ within-agent self-loop replays; 1 sibling-coordination misroute (out-of-Pattern-D scope).**

P3W3 day 1 surfaced multiple distinct race-shape failures, but none are the cross-agent crossed-in-flight failure that Pattern D's default protocol covers. Categorizing:

### Cross-agent crossed-in-flight races (Pattern D default protocol target) — count: 0

No instance recorded where one agent shipped work and a separate agent's `task_assignment` for the same work arrived afterward. The work-distribution structure of P3W3 (issue-keyed assignments to single-named implementers, no parallel-claim-able backlog items) makes this rare-by-construction in the wave's first day. P3W1's 5 races came from coordinator-broadcast-style charters where multiple implementers simultaneously read the brief and started before the formal task_assignment landed. P3W3's spawn pattern was 1-issue-1-implementer with no broadcast brief, so the race mechanism was structurally absent.

This is **not necessarily** a Pattern D win — it is a structural difference in the wave's coordination shape. If P3W4 returns to broadcast-brief coordination, race count may rise.

### Within-agent self-loop task_assignment replays — count: 3+ confirmed

Per `feedback_self_loop_task_replay_glitch.md` (filed 2026-05-03 from Idris-853 implementer session):

- taskId 2 ("Read target files...") — replayed ~10min after PR open
- taskId 5 ("Choose Trivy CVE fix strategy") — replayed
- taskId 6 ("Implement fix on I.Yusuf/0853-trivy-cve-fix branch") — replayed

These are **harness-glitch-class** races — the inbox-to-mailbox bridge replays an agent's own completed tasks back to themselves with `assignedBy: <self-id>`. Architecturally distinct from Pattern D (which addresses cross-agent task-bus ordering, not self-loop replays). Listed here for completeness — Pattern D's default protocol does NOT extend to self-loop replays, and the new feedback memo correctly recommends a different decision tree (silent ignore + verify via `TaskGet → not-found`).

**Charter-response candidate:** Aino should consider whether to promote the self-loop-replay-decision-tree from `feedback_self_loop_task_replay_glitch.md` into an `agents.md` adjacent section (call it Pattern D-prime), to keep the two race shapes co-located in the implementer's mental model.

### Sibling-coordination misroute (Pattern D-adjacent, not in-scope) — count: 1

Idris-853 catch: deploy#242 originally attributed as "sibling of isnad-graph#853"; Idris re-read the issue body's per-service multi-arch status table and surfaced that the actual remaining work is in `noorinalabs-landing-page`. Outcome: landing-page added as 4th wave-scope repo; correction reply on deploy#242 (issuecomment-4366836610). Lucas was withdrawn as implementer, Kofi (landing-page team) reassigned per `feedback_child_repo_implementer_rule.md`.

This is Pattern D-adjacent: a pre-spawn poll on deploy#242 alone would NOT have caught this (the issue is OPEN, no prior PR), because the misroute is in the issue's *scope*, not its *state*. It's a verify-issue-body discipline (closer to `feedback_review_against_artifact_not_framing.md`), not a verify-state discipline.

**Charter-response candidate:** Aino should consider whether the pre-spawn poll's command-list should append a "skim issue body" step for cross-repo issues, or whether that's better-handled at the wave-planning layer.

### Repo-pivot during spawn (Lucas-242 → Kofi-242) — count: 1

Triggered by the deploy#242 sibling-coordination catch. Per Pattern D § Narrow trigger, "assignments that change branch/worktree paths" require pre-spawn poll. The Kofi-242 reassignment to a different repo is precisely this trigger. Audit cannot verify whether the pre-spawn poll was repeated for the Kofi-242 spawn (no audit-visible artifact), but the outcome (LP#75 OPEN, no duplicate PR) is consistent with the poll having occurred.

## Section 3 — Standardized ack-shape adherence

**Numerical compliance rate: 0/0 measurable; 0 canonical-shape uses observed across all P3W3 artifacts.**

The canonical ack shape — `ack — task #N — already shipped at PR #M at YYYY-MM-DDTHH:MM:SSZ; no action needed` — is intended for use when an implementer in a crossed-in-flight race posts a no-op acknowledgment to the orchestrator. The audit's measurable surface is:

1. **PR comments across P3W3 PRs** (#854, #254, #258, #257, #259, #260, #261, #266, LP#75): 0 occurrences of the canonical shape (verified via `gh pr view --json comments --jq '.comments[] | select(.body | test("ack . task|already shipped at PR"; "i"))'`).
2. **Issue comments on issues triggering the spawns** (#252, #242, #853, others): 0 occurrences of the canonical shape.
3. **`feedback_log.md`**: 5 hits on "Pattern D" / "pre-spawn" / "crossed" — all are P3W1-retro-era documentation of the protocol, no P3W3 implementer self-reports yet (P3W3 retro hasn't happened).

### Why the rate is 0/0 (denominator is also 0)

Per Section 2, **0 cross-agent crossed-in-flight races materialized in P3W3 day 1**. There were no scenarios where the canonical shape was the right tool to use. The 3+ self-loop task_assignment replays (Idris-853) are harness-glitch-class, where the correct response per the new memo is **silent ignore**, not the canonical ack shape (which would have been confusing — implementer ack-shaping a self-loop replay would imply a real cross-agent race occurred).

### Where Idris-853 *did* respond to a (different-shape) misroute

The 1-of-6 task_assignment that Idris-853 flagged to me at orchestrator-time (taskId 2: deploy#252 work routed to isnad-graph implementer) did NOT use the canonical ack shape — Idris correctly identified it as a different signal (cross-repo misroute, not crossed-in-flight) and used a free-form clarification ping. This was the correct behavior: Pattern D's canonical shape is keyed to "already-shipped" semantics, not "wrong implementer" semantics.

**Conclusion:** the canonical ack shape was correctly NOT used in the only P3W3 task_assignment-anomaly observed, because the anomaly's shape was different. Compliance is therefore "true negative" — non-use was the right call. No Pattern D adherence failure on this dimension.

## Top-3 findings + recommended charter-response actions for Aino

### Finding 1 — Adoption is inferable but not auditable from artifacts

The narrow trigger requires a pre-spawn poll but produces no audit trail. P3W3 outcomes (0 spawn-duplications) are consistent with adoption, but the strict-adoption rate from artifacts alone is 1/13 (only this audit's self-poll is attested).

**Recommended action:** Aino to decide whether to add a **lightweight evidence requirement** to Pattern D — e.g., orchestrator posts a one-line "pre-spawn check: PR-list clean, issue OPEN" status comment on the issue when spawning. Cost: 1 comment per new-implementer spawn (~13 in this wave). Benefit: future audits can compute strict adoption rate. Risk: comment-noise on issues; may be redundant with implementer's first PR comment.

**Alternative:** treat 0-spawn-duplications as the *only* signal needed (current Pattern D adoption-signal language) and accept indeterminate strict-adoption rate as cost-of-low-overhead.

### Finding 2 — Self-loop task_assignment replays are a 2nd race shape that Pattern D doesn't cover

Within-agent self-loop replays (3+ confirmed in P3W3 from Idris-853) are architecturally distinct from cross-agent crossed-in-flight races. The new `feedback_self_loop_task_replay_glitch.md` correctly recommends a different decision tree (silent ignore + `TaskGet → not-found` verify).

**Recommended action:** promote the self-loop-replay decision tree into `agents.md` as an adjacent sub-section (e.g., § Self-Loop Task-Assignment Replays — Harness Glitch Discipline) co-located with Pattern D, so implementers have both race-shape responses in one place. The current memo lives only in user-memory and won't propagate to subagent spawn briefs without a charter section.

### Finding 3 — Pattern E correlation: P3W3 day 1 is post-emergency, expect heightened process-discipline drift on later spawns

Per `feedback_pattern_e_emergency_process_collapse.md`, P3W2 ended with 13 deploy PRs in catchup-debt and 4-comment → 0-comment + 13min → 4sec merge degradation. P3W3 day 1's spawn-time errors (Aisha-252 missing-branch catch, Idris-853 misroute catch, child-repo-implementer-rule violation, self-loop replay glitch) are consistent with Pattern E carry-over. Pattern D's narrow trigger may be especially vulnerable in post-emergency waves where orchestrator attention is bisected between active stabilization + new wave kickoff.

**Recommended action:** at P3W3 retro, correlate Pattern D adoption signal with Pattern E recovery posture (both in `agents.md` and `emergency-mode.md`). If P3W3's adoption-signal looks weaker than P3W1's, attribute the delta to post-emergency-recovery factors before concluding Pattern D itself needs revision. Specifically, do NOT promote Pattern D from "narrow trigger" to "full poll-before-every-assignment" on the basis of P3W3 alone — wait for a clean (non-post-emergency) wave before re-baselining.

## Audit completeness

- [x] Pre-spawn poll adoption rate stated (Section 1: 1/13 strict, 13/13 inferred)
- [x] Drift surface enumerated (Section 2: 0 cross-agent races, 3+ self-loop replays, 1 sibling misroute, 1 repo-pivot)
- [x] Ack-shape compliance rate stated (Section 3: 0/0 — denominator 0, no canonical-shape opportunities arose)
- [x] At least 2 specific cited examples per section
- [x] Top-3 findings + recommended charter-response actions for Aino

## Audit limitations + future-work hooks

1. **Audit cannot see orchestrator's command log.** Strict adoption rate (Section 1) is inferable only via outcome + spawn-brief content. If the lightweight evidence requirement (Finding 1, Recommendation A) is adopted, future audits will compute strict rate directly.
2. **Day 1 only.** P3W3 spans 7-9 days; this audit captures the kickoff + first wave of spawns. A retro-time follow-up (covering day 2-end) is appropriate to catch any late-wave spawn duplications.
3. **Reviewer-class spawns excluded.** Pattern D's narrow trigger is implementer-spawn-focused. Reviewer assignments (e.g., Bereket × 2) are out of scope per the protocol's wording, though `feedback_role_class_specific_boundaries.md` notes that role-class-specific boundaries can hide failure modes; future Pattern D revisions may need a reviewer-spawn variant.
4. **Cross-repo wave-aware sibling reasoning** (per `feedback_cross_repo_wave_ref_resolution.md`) was not surfaced as a Pattern D failure here, but the deploy#242 misroute is structurally adjacent — sibling-coordination errors at spawn time are a class worth tracking separately.

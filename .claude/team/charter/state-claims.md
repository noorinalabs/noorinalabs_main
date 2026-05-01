# State Claims and Verification Discipline

This file documents the team's discipline for making claims about the state of artifacts (PRs, issues, branches, files, sha references) in coordination messages, review comments, and status updates.

## Refresh State Before Claim (Mandatory) <!-- promotion-target: skill -->

Before any state-claim — phrases like `X/Y cleared`, `comprehensive coverage`, `all items addressed`, `merged at sha Y`, `PR head is Z`, `verified at head_sha=W`, or any assertion about the current state of an artifact you are NOT actively writing to — perform a fresh verification call (`gh api`, `git show <ref>`, or equivalent) within the same tool-block as the claim, with manual eyeball-check that the verification confirms the claim.

### Sub-rule: pre-write checklist

Before any SendMessage, PR comment, or issue body containing a state-claim, the agent must have at least one verification tool-call (matching the artifact being claimed) in the same response or one of the immediately preceding responses since the claim's scope was last touched. The discipline is:

1. Identify the load-bearing state-claim in the message you are about to send.
2. Identify the artifact whose state is being claimed (PR head, issue state, comment count, sha, etc.).
3. Call the appropriate verification tool (`gh pr view --json state,mergedAt,headRefOid,...`, `gh issue view --json state,closedAt`, `git rev-parse origin/<branch>`, etc.) with **fresh fetch** for git data.
4. Manually eyeball-check the tool output confirms the claim.
5. THEN send the message.

If the verification disconfirms the claim, revise the message — do not send the original claim with caveats appended ("I think X but haven't checked"). The discipline is to assert only what verification confirms.

### Sub-rule: Manager class is NOT exempt

The manager-pass review and orchestrator coordination roles are most exposed to this failure mode because:

- **Information-volume** — managers/orchestrators track multiple PRs simultaneously; more state than any single role.
- **Comprehensive-claim posture** — managers default to "I've reviewed everything" framing; implementers default to "I touched X" framing. The first is more vulnerable to incomplete-coverage-claims.
- **Asymmetric verification incentives** — a missed implementer detail surfaces in PR-review (the implementer's diff at code-write-time is the natural verification gate); a missed manager detail propagates because the manager-pass IS the verification.

For these reasons, the manager-class agent must apply the discipline at LEAST as strictly as implementers — and arguably more strictly because manager-class state-claims propagate further. Manager-pass review-coverage claims that turn out to have gaps are moderate feedback events.

### Severity

- One-off slip (caught by self before propagating): minor, no feedback log entry needed.
- One-off slip (caught by another agent's correction): minor, optional feedback log entry.
- Repeated slips on the same memory (≥3 in a wave): moderate, feedback log entry required.
- Manager-class slip on load-bearing review-coverage claim: moderate (regardless of repetition).

### Worked examples (Phase 3 Wave 1)

11 in-wave instances logged. Most-illustrative:

- **Bereket's #210 v3 manager-pass:** claimed `all 5 original review items + the v3 runbook-drift fix... all present and correct`. Lucas's second-reviewer pass caught two more drift sites Bereket missed (runbook L161 + compose L614-621 still describing the pre-amendment runbook-step + 0775 model). Manager-pass was the gate-clearing review, so the missed drift would have propagated to merge if Lucas hadn't caught it.
- **Orchestrator's #208 "2/2 cleared" misclaim:** claimed gate clearance based on comment-count, not actual reviewer-count. The hook block at merge surfaced the gap. Resolved by reposting reviewer comments with corrected directionality.
- **Bereket's `main#233` charter-ambiguity framing:** asserted the charter had two textually-supportable readings for `Requestor`/`Requestee` directionality; later wire-artifact verification showed only Reading 1 was in actual use. The framing itself was a Pattern C instance — claimed without exhaustively reading wire artifacts.

### Why

Phase 3 Wave 1 produced 11 distinct instances across 3 people in one wave, despite each violator naming the failure mode each time it occurred and committing to corrected behavior each time. Recurrence-after-self-naming is the signal — charter language alone has not been sufficient to fix the discipline historically. The pre-write checklist sub-rule is the lightweight, agent-side discipline; structural safeguards (hook at SendMessage boundary OR independent verification routing for load-bearing manager-class claims) remain proposed for future wave-retro discussion if the recurrence pattern persists.

### Aspiration: post-publish audit (no enforcement)

The proactive variant — self-audit of own previously-published claims absent any external prompt — was demonstrated by no team member in Phase 3 Wave 1. Charter aspires to this discipline but does not mandate it. Easily becomes box-checking; the team's discipline portfolio is honestly named to include this gap.

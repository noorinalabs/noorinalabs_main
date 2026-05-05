---
name: wave-retro
description: Automated wave retrospective — PR analysis, assessments, trust matrix updates, feedback log, charter change proposals
args: team_name, Phase number, Wave number
---

Run a retrospective for a completed wave of the `{team_name}` team.

## Instructions

### 1. Ontology check

Run `/ontology-librarian` to check ontology staleness before the retro. If the ontology is significantly behind, note it in the retro findings — the wrapup should have run `/ontology-rebuild`, so staleness here indicates a process gap.

### 2. Gather merged PRs

List all PRs merged to the wave's deployments branch:

```bash
gh pr list --state merged --base "deployments/phase{N}/wave-{M}" --json number,title,author,body,mergedAt,reviews
```

### 3. Gather review comments and CI data

For each merged PR:

```bash
gh pr view {NUMBER} --json reviews,comments
gh run list --branch {PR_BRANCH} --json conclusion,name
```

Collect:
- Review comments (must-fix items, tech-debt items)
- CI pass/fail counts per PR
- Time from PR creation to merge

### 4. Per-engineer assessment

For each engineer who had PRs in this wave, assess:

- **Positive findings:** clean PRs, fast turnaround, good reviews given, helpful collaboration
- **Negative findings:** CI failures, must-fix items from reviews, late delivery, missing tests
- **Severity:** minor / moderate / severe (per charter § Feedback System)

Structure as:

```
### {Engineer Name}
- PRs: #{N1}, #{N2}
- CI failures: {count}
- Must-fix items received: {count}
- Tech-debt items created: {count}
- Assessment: {positive/negative findings}
- Severity: {minor|moderate|severe|none}
```

### 5. Update trust matrix

**Trust matrix lives on `main`**, not a side branch. Edit `.claude/team/trust_matrix.md` directly on the retro branch so the update lands in the same retro PR as the feedback log. Do NOT use a separate worktree or push to `CEO/0000-Trust_Matrix` — that pattern (retired 2026-04-17) orphaned trust updates off-main for months.

Apply directional trust changes based on wave performance:
- Reliable delivery, clean reviews → increase trust (+1, max 5)
- CI failures, must-fix items, broken commitments → decrease trust (-1, min 1)
- No significant signal → no change

Append a new `## Phase {N} Wave {M} Trust Updates ({DATE}) — {theme}` section with:
- A `| Rated | Old | New | Reason |` table for each relevant team grouping (e.g., `### Org-Level Team`)
- A `### Done Well / Needs Improvement (Phase {N} Wave {M})` matrix

The edit will be committed as part of the retro PR (see Step 6). Do NOT create a separate commit or PR for the trust matrix update.

### 6. Append to feedback log

Append a retro entry to `.claude/team/feedback_log.md`:

```markdown
## Retrospective: Phase {N} Wave {M} — {DATE}

### Team Performance
{summary of wave metrics: PRs merged, issues closed, CI health}

### Per-Engineer Assessments
{from step 3}

### Top 3 Going Well
1. {finding}
2. {finding}
3. {finding}

### Top 3 Pain Points
1. {finding}
2. {finding}
3. {finding}

### Proposed Process Changes
1. {change} — Rationale: {why}
2. {change} — Rationale: {why}
```

### 7. Propose charter changes

Based on pain points and findings, propose specific charter amendments. Present each as:

```
**Proposed change:** {what to change in charter}
**Section:** {which charter section}
**Rationale:** {why, based on retro findings}
```


### 7.5. Run promotion audit (`/promotion-audit`)

Invoke `/promotion-audit` to deterministically check whether any memories, charter sections, or skills have crossed promotion thresholds during this wave. The audit resolves the current wave from `cross-repo-status.json`, classifies every candidate, and:

- **AUTO-tier** (memory → charter, charter → skill): opens a PR with the auto-generated artifact; lands via the standard 2-reviewer pattern.
- **DECIDE-tier** (skill → hook): files a draft issue with the proposed hook design. Hooks are security-sensitive — never auto-applied (D6).
- **KEPT / SUPERSEDED / ALREADY-PROMOTED**: informational; no action.

The audit appends its table to this retro's feedback_log entry **and** writes a standalone log at `.claude/team/promotion_audit_log/{wave-name}.md`. On unchanged repo state, the audit is byte-deterministic — re-running produces identical output. See issue #152 for the full pipeline spec and PR #153 / Hook 15 for the worked example.

### 8. Present full retro summary to the user

**Output the complete retro summary directly in the conversation.** Do not just write to files — the user must see the retro without having to open `feedback_log.md`. Include:

- **Wave metrics:** PRs merged, issues closed, CI health, tech-debt filed
- **Per-engineer assessments:** each engineer's PRs, must-fix items, CI failures, severity rating
- **Trust matrix changes:** who went up/down and why
- **Top 3 going well**
- **Top 3 pain points**
- **Proposed process changes** with rationale
- **Fire/hire actions** (if any)
- **Proposed charter changes** (if any)

**Do NOT apply any charter changes without explicit user approval.** The user decides which proposals to adopt, modify, or reject.

## What remains manual

- User must approve all charter changes before they are applied
- Subjective assessment calibration (severity levels) may need user override
- Trust matrix changes are proposed — user can veto specific adjustments

## Wave-Concentration Metric (added P3W4 retro 2026-05-05)

In step 4 (per-engineer assessment), compute and report the **top-implementer concentration**:

```
top_concentration = (max PRs by single implementer) / (total PRs in wave)
```

If `top_concentration >= 0.6`, surface this in step 6 (feedback log) under "Top 3 pain points" or "Top 3 going well" depending on context:

- **Theme-fit concentration** (e.g., wave themed on a single domain that one engineer owns): note as a "going well" with a forward-looking flag for next wave's planning.
- **Fragility concentration** (e.g., a multi-domain wave where one engineer happened to absorb most of the load): note as a "pain point" with explicit redistribution actions for the next wave.

The metric is **visibility, not policy** — concentration is sometimes correct (theme-fit) and sometimes a risk (fragility); the retro forces the call.

Include in the wave-shape table as a separate row:

| Top-implementer concentration | {N PRs} / {total} = {pct}% by {engineer} |

**Why:** P3W4 had 80% of main# PRs from one engineer (Aino, 8 of 10). The work was clean (theme-fit hook bug-class consolidation), but the dependency risk on W5 carry-forwards (#263, #264 also Aino-tractable) was invisible until retro. A concentration row at the top of every retro forces next-wave planning to address it explicitly — distribute, accept the risk and document, or theme the next wave around the same engineer's surface.

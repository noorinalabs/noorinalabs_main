# Pull Requests

When all work on a feature branch is complete (code committed, review done, must-fixes resolved), the submitting team member **automatically creates a PR to the deployments branch** for their wave using the `gh` CLI. Do not wait for manual instruction.

**PR ownership:** Only the team member who implemented the work creates the PR. The Program Director must NOT create duplicate PRs for the same branch.

## Comment-Based Reviews (Mandatory) <!-- promotion-target: none -->
All agents share a single GitHub user account. **`gh pr review --approve` is blocked** — it always fails with "cannot approve your own pull request". All PR reviews MUST use comment-based reviews instead.

**Review format** (posted via `gh pr comment`):
```
Requestor: <comment author>
Requestee: <comment target>
RequestOrReplied: Request | Reply | Approved | ChangesRequested
TechDebt: none | #15, #16, ...
```

### Canonical meaning (resolves main#233)

The role names always describe the **comment** (not the PR):

- **`Requestor` is always the comment author** — the team member posting the comment, regardless of whether they are the PR author or a reviewer.
- **`Requestee` is always the comment target** — the team member the comment is addressed to.
- **`RequestOrReplied`** distinguishes the comment kind, NOT the role direction:
  - `Request` — initial review request from PR author (Requestor=PR author, Requestee=reviewer)
  - `Reply` — non-verdict response from any party (Requestor=replier, Requestee=person-being-replied-to)
  - `Approved` — reviewer's approving verdict (Requestor=reviewer, Requestee=PR author)
  - `ChangesRequested` — reviewer's blocking verdict (Requestor=reviewer, Requestee=PR author)

**Key consequence for verdict comments**: on `Approved` and `ChangesRequested` comments, `Requestor` is the reviewer (because the reviewer is the comment author). The hook counts distinct `Requestor` values across `Approved`/`ChangesRequested` comments to verify the 2-reviewer rule (resolves main#244 — the prior hook counted distinct `Requestee` values, which on verdict comments is the PR author, not the reviewer).

### Validation

- The `Requestor` of a `Request`-kind comment must differ from the comment author of the `Approved`/`ChangesRequested` comments (a PR author cannot self-approve their own PR via comment-based review). Enforced by `block_gh_pr_review.py` PreToolUse hook + `validate_pr_review.py` at merge time.
- The `TechDebt:` line is **mandatory** on every `Approved` and `ChangesRequested` comment. If the reviewer found non-blocking observations, they MUST create `tech-debt`-labeled issues BEFORE posting the verdict, then list the issue numbers. If no tech-debt was found, write `TechDebt: none`. Enforced by `validate_pr_review.py` PreToolUse hook at merge time.
- The 2-reviewer rule is satisfied when there are `Approved` comments from **two distinct `Requestor` values**, neither of which is the PR author. Single-reviewer waivers per § Single-Reviewer Exception (Wave-Bootstrap Only) are honored by the hook (resolves main#228) when the PR is labeled `wave-bootstrap` and the single reviewer is the Standards & Quality Lead.

## Review Prompt Template (Mandatory) <!-- promotion-target: none -->
When the orchestrator assigns a review to any agent, the prompt **MUST** include a copy-paste-ready `gh pr comment` command with all fields pre-filled. Do not rely on agents writing the format from memory — this has a 100% error rate.

**Template for orchestrator prompts** (Approved/ChangesRequested verdict — reviewer is the comment author, so Requestor=reviewer):
```
Post your review using this exact command:

gh pr comment {PR_NUMBER} --repo noorinalabs/{REPO} --body "Requestor: {REVIEWER_NAME}
Requestee: {PR_AUTHOR_NAME}
RequestOrReplied: Approved
TechDebt: none

{Your review summary here.}"
```

Replace `Approved` with `ChangesRequested` if blocking issues found. Replace `TechDebt: none` with issue numbers if tech-debt filed. Do NOT add bold markers, parenthetical descriptions, or extra fields.

For `Request`-kind comments (initial review request from PR author), the role direction inverts: Requestor={PR_AUTHOR_NAME}, Requestee={REVIEWER_NAME} (because the PR author is the comment author of the request).

**Why:** In Phase 3 Wave 1, all 7 initial reviews used wrong field names (`Requestee (reviewer):` instead of `Requestee:`) and omitted the `TechDebt:` line, requiring re-posts and blocking merges for ~15 minutes. In P3W3, the wave-completion batch's verdict comments mostly had `Requestee=author` (because Requestor was the reviewer-as-comment-author), which the prior `validate_pr_review.py` interpretation treated as 1 distinct reviewer instead of 2 — forcing `--admin` overrides on 5/5 wave-merge PRs (main#244).

Failing to include the review template in a review assignment prompt is a **minor feedback event** for the orchestrator.

## Two-Reviewer Assignment at Wave Kickoff <!-- promotion-target: none -->
Every PR must have **two reviewers** assigned at wave kickoff — a primary and a secondary. Both reviewers are named in the agent's spawn prompt and in the execution plan.

**Why:** In Phase 3 Wave 1, only one reviewer was planned per PR. Every PR needed ad-hoc second reviewer assignments, causing merge delays while idle agents were redirected.

The Program Director's execution plan MUST include a review matrix with two named reviewers per expected PR. The orchestrator verifies this before spawning agents.

## Single-Reviewer Exception (Wave-Bootstrap Only) <!-- promotion-target: none -->
The two-reviewer requirement may be waived **exclusively** for wave-bootstrap PRs — i.e., PRs that establish the tooling/CI/hooks that subsequent wave PRs will be gated by (e.g., the pre-commit hook rollout that the CI sweep depends on).

Strict conditions — **all must hold**:
- The PR is part of wave bootstrap (establishes infra that blocks other wave work)
- No more than **one** such exception per wave
- The single reviewer is the Standards & Quality Lead (Aino) or a comparable charter enforcer
- The exception is logged by name in the wave retro, with explicit justification

All other PRs require two comment-based reviews. `--admin` merges without two reviews are subject to the moderate-feedback-event classification in § Feedback System.

**See also:** § Trivial Cross-Repo Doc Sweep — a separate single-reviewer exception class for byte-identical doc syncs across child repos. The two exceptions are **independent budgets** (the wave-bootstrap 1-per-wave cap does not consume, and is not consumed by, doc-sweep waivers) and are **not cumulative** — a single PR may invoke at most one.

**Why:** In Phase 2 Wave 8, the single-reviewer shortcut was invoked 8× — it had stopped being an exception and become a pattern of convenience. This clause formalizes the boundary.

## Load-Bearing Followups for Disabled CI Jobs <!-- promotion-target: skill -->
When a PR disables a CI job to unblock merge, the followup tracking issue must be **load-bearing** — the re-enablement of the job is a first-class acceptance criterion of the issue, not a hidden subtask of "fix the underlying bug."

Concrete requirements:
1. **Followup issue exists before the disable PR is approved.** The reviewer verifies the issue number in the PR body under a `## Disabled CI jobs (load-bearing followup)` section.
2. **Followup issue acceptance criteria** must include:
   - A specific fix for the underlying problem
   - Re-enable the CI job (remove `if: false` / `--skip` / equivalent)
   - Verify green CI after re-enablement
   - All three bullets are required in the issue body.
3. **Breadcrumb in PR body.** The PR that disables a job must include a top-level section `## Disabled CI jobs (load-bearing followup)` naming the job disabled, the reason, and the followup issue number.
4. **No silent disables.** A PR that disables a CI job without both the issue and the breadcrumb is a moderate feedback event.

**Why:** Phase 2 Wave 8 ratified this rule mid-wave after two PRs (isnad-graph#811, design-system#56) disabled CI jobs with tracking issues that could be "closed" by just fixing the bug without ever re-enabling the job. Promoting the rule into the charter closes that loophole. Reference: `feedback_disable_followup_load_bearing.md` (historical memory, superseded by this clause).

## PR Review Workflow for Deployments Branch PRs <!-- promotion-target: skill -->
1. **Create the PR** targeting `deployments/phase{N}/wave-{M}`.
2. **Notify reviewers** — the PR creator must notify at least **two** other team members to review the PR. Use SendMessage or a GitHub comment to notify. **A PR MUST NOT be merged without at least two peer reviews from distinct non-authors.** For waves with fewer than 4 engineers, the manager's review counts but must include a substantive review comment (not just "LGTM"). This is enforced by the `validate_pr_review.py` PreToolUse hook. **This rule applies even on fast/compact waves** — speed does not exempt PRs from the review gate. Wave 7 merged 5 PRs with zero reviews; this must not recur.
3. **Reviewer performs the review** and posts a comment-based review on the PR with:
   - **Must-fix items** — blocks merge; the submitter must resolve before proceeding.
   - **Tech debt items** — does not block merge; tracked as GitHub Issues.
   - The reviewer then **notifies the PR creator** (via SendMessage or mention) that the review is complete and what action is needed.
4. **PR creator acts on review**:
   - **Must-fix items**: Fix immediately and push to the branch.
   - **Quick-fix tech debt**: Fix immediately if minimal impact.
   - **Non-trivial tech debt**: Create a GitHub Issue for future planning.
5. **Push final changes** from the review fixes.
6. **The team merges** the PR into the deployments branch themselves — no user approval needed for PRs into deployments branches.

## Additive Commits on ChangesRequested (Mandatory) <!-- promotion-target: none -->

When a reviewer marks `RequestOrReplied: ChangesRequested`, the fix MUST land as an **additive commit on the same branch**. Force-push (`git push --force` / `git push --force-with-lease`) during a ChangesRequested cycle is **prohibited** because it resets the HEAD-SHA anchor that the reviewer's `gh api contents/<path>?ref=<sha>` verification chain depends on (see § Trust the Artifact, Not the Framing). Without HEAD-SHA stability, the re-review's "delta from prior review" comparison becomes unreliable.

**What is allowed during ChangesRequested:**
- New commits added to the same branch (no rewrite of existing commits)
- A merge commit to update from base if the base advanced (use `git merge origin/<base>`, not `git rebase`)

**What is prohibited during ChangesRequested:**
- `git push --force` / `--force-with-lease`
- `git rebase` followed by force-push
- `git commit --amend` followed by force-push
- Squashing prior commits before re-review

**If a rebase is genuinely needed** (e.g., merge conflict that cannot be resolved by a merge commit, or the requesting reviewer asks for a clean history), the implementer MUST open a comment thread on the PR BEFORE rebasing, get explicit "rebase OK" from the requesting reviewer, then rebase. The reply to a request-to-rebase counts as a `RequestOrReplied: Reply` not an Approval — the re-review cycle restarts from the new HEAD.

**Pre-Approved squash-merge is unaffected.** Once both reviewers have posted `RequestOrReplied: Approved`, the HEAD-SHA anchor is no longer load-bearing, and `gh pr merge --squash` (which performs an effective rebase server-side) is the standard path.

**Why:** In Phase 3 Wave 3, all 4 ChangesRequested cycles (deploy#259 Path-A bundled, #261 perms+runbook, #266 cross-repo Option A, #267 5-fixes-in-49-lines) shipped as additive commits. The reviewers' second-pass reviews could compute the delta deterministically against the prior HEAD SHA. Zero force-pushes; zero "what changed since I last looked" ambiguity. Codifying the practice that worked.

**Severity if violated:** **Moderate** feedback event for the implementer. The reviewer may either re-do the full review at the new HEAD (slow path) or block merge until the implementer reverts the force-push and re-applies the fix as additive (correct path).

## Review Finding Disposition <!-- promotion-target: none -->
Every finding from a PR review must be dispositioned before merge. No finding may be silently dropped.

| Finding Type | Action Required | Blocks Merge? |
|-------------|----------------|---------------|
| **Must-fix** | PR originator fixes on the branch before merge | Yes |
| **Tech-debt** | Reviewer or originator creates a GitHub Issue for each item before merge | No (but issues must exist) |
| **Quick-fix tech-debt** | PR originator fixes immediately if minimal effort | No |

**Enforcement:** The charter enforcer (Aino) verifies during PR review that:
1. All must-fix items are resolved before approving merge
2. All tech-debt items have corresponding GitHub Issues created
3. Issues are labeled `tech-debt` and assigned to the appropriate team member

## Post-Merge Integration Verification <!-- promotion-target: skill -->
**After every PR merge into a deployments branch**, the manager must verify the integrated result before merging the next PR:

1. **Pull the updated deployments branch** locally (or in a worktree).
2. **Run the repo's full check command** (`make check`, `npm run check`, or equivalent — lint + typecheck + build).
3. **If the check fails:** The last-merged PR introduced a regression. The manager must notify the PR author to fix it before any further PRs are merged.
4. **If the check passes:** The next PR may be merged.

This catches semantic conflicts that GitHub's textual merge cannot detect (e.g., two PRs that individually pass CI but break when combined). Managers must NOT merge multiple PRs in rapid succession without verifying in between.

**CI enforcement:** All repositories must configure CI workflows to trigger on pushes to `deployments/**` branches (not just PRs). This provides automatic verification after each merge, complementing the manager's manual check.

## CI Workflow `pull_request` Triggers Must Cover Wave Branches <!-- promotion-target: none -->

CI workflows using a `pull_request` trigger MUST include active wave branches in the `branches` filter, OR omit the filter entirely so the workflow triggers on any base branch. Workflows whose `branches` filter is locked to `["main"]` (or any other single-branch list) silently skip CI on PRs targeting `deployments/phase-{N}/wave-{M}` — the wave PRs that aggregate before the main merge. This is the inverse of the push-trigger rule above: push triggers must cover `deployments/**`, AND PR triggers must cover them too.

**Required pattern** — explicit branch list including wave branches:

```yaml
on:
  pull_request:
    branches: ["main", "deployments/**"]
```

**OR — path-filtered (no branches filter at all):**

```yaml
on:
  pull_request:
    paths:
      - "src/**"
      - "tests/**"
```

**Anti-pattern** — main-only filter that drops wave-branch PRs:

```yaml
on:
  pull_request:
    branches: ["main"]   # WRONG: wave-branch PRs skip CI silently
```

**Reviewer enforcement:** When a PR adds or modifies a `.github/workflows/*.yml` file with a `pull_request: branches:` filter, reviewers MUST flag any single-branch list that does NOT include `deployments/**`, unless the PR body explicitly justifies the exclusion (e.g., "this workflow only runs on main-merge promotions, not pre-merge PRs").

**Why:** P2W10 surfaced this convention gap twice independently. (1) `noorinalabs-user-service/ci.yml` had `branches: ["main"]` — Anya's user-service#80 alembic-merge PR targeting `deployments/phase-2/wave-10` produced an empty `statusCheckRollup` (filed user-service#81). (2) `noorinalabs-deploy/integration-tests.yml` had the same anti-pattern — wave-10 PRs touching `integration-tests/**` would skip CI (filed deploy#152, fix in deploy#154). Both are the same CI-trigger-filter-written-against-single-branch-PR-flow error. Per [`feedback_enforcement_hierarchy.md`](../feedback_log.md), charter codification is step 1 + 2 (rule + reviewer reference); a future `validate_ci_trigger_branches` PreToolUse hook is filed as step 3 if the convention proves robust without manual reviewer reminders.

## Cross-Contract PRs <!-- promotion-target: skill -->
When two or more PRs in flight consume/produce from each other (Kafka topics, Parquet schemas, shared API contracts, wire formats between workers or services), the **first PR opened MUST include a "Contract" section** in the PR body. Subsequent PRs that consume or produce against that contract link to it and document any divergence explicitly.

The Contract section must specify:

1. **Message / schema / API shape** — concrete example or reference to a shared constants module (e.g., `workers/lib/topics.py`).
2. **Ownership** — which PR owns the contract; which owner adjudicates disputes.
3. **Divergence** — how other PRs may legitimately deviate (optional fields, label supersets, etc.).

Any reviewer may block a cross-contract PR that fails this requirement.

**Rationale:** in P2W9, noorinalabs-isnad-ingest-platform#18 (Weronika) and #21 (Wanjiku) built in parallel on incompatible assumptions about message shape (per-row `{label, id, props}` vs Parquet batches with `hadiths.parquet` payload). The mismatch surfaced only during reviewer cross-check after both PRs were essentially complete, forcing an owner-chaired design call (noorinalabs-main#192) and substantive rewires on both branches. A 5-minute Contract section in whichever PR opened first would have caught this upfront.

Derived from Phase 2 Wave 9 retrospective, 2026-04-22.

## Cross-PR Dependency Sequencing <!-- promotion-target: skill -->
When multiple PRs in the same wave have dependencies (e.g., PR B depends on changes from PR A):

1. **Identify dependencies** before merging — check if any PR depends on another PR's changes
2. **Merge in dependency order** — base PR first, dependent PR second
3. **Do NOT merge dependent PRs in parallel** — even if both have green CI, the dependent PR's CI ran against the base branch WITHOUT the dependency
4. **After merging the base PR**, the dependent PR must rebase/merge the updated base before its CI result is trusted
5. **Document dependencies** in PR descriptions: "Depends on PR #N (must merge first)"

## Wave Merge PR Verification <!-- promotion-target: skill -->
At the **end of a wave or phase**, the Manager creates a PR from the deployments branch into `main`. Before presenting the PR to the user:

1. **Verify all CI checks are green** — run `gh pr checks {NUMBER}` and confirm every job passes.
2. **If any check fails**, fix it before notifying the user. The user should NEVER see a wave merge PR with red CI.
3. **Report CI status** explicitly when presenting the PR: "All N checks passing."
4. **Provide full clickable URLs** when presenting PRs to the user — use `https://github.com/{org}/{repo}/pull/{number}`, not `repo#number` format.

The **user reviews and merges** this PR. Do not proceed to the next phase until the user has merged.

## PR Template <!-- promotion-target: none -->
```bash
git push -u origin <branch-name>
gh pr create --base deployments/phase{N}/wave-{M} --title "<short title>" --body "$(cat <<'EOF'
## Summary <!-- promotion-target: none -->
<1-3 bullet points describing the change>

## Related Issues <!-- promotion-target: none -->
Closes #<issue-number>

## Review Checklist <!-- promotion-target: none -->
- [ ] Reviewed by another team member
- [ ] Must-fix items resolved
- [ ] Tech debt items filed as GitHub Issues (if any)

Co-Authored-By: Firstname Lastname <parametrization+Firstname.Lastname@gmail.com>
Co-Authored-By: Claude Opus 4.6 (1M context) <noreply@anthropic.com>
EOF
)"
```

- PR title should be concise (under 70 characters).
- The body must reference the related GitHub Issue(s) with `Closes #N`.
- The submitting team member is responsible for creating the PR immediately upon branch completion.

## Pre-Push Checklist <!-- promotion-target: none -->
Before pushing a branch and creating a PR, every engineer must:

1. **Run the repo's lint check** (`ruff check` / `npm run lint` / equivalent) — fix all errors.
2. **Run the repo's format check** (`ruff format --check` / `npx prettier --check` / equivalent) — fix any formatting issues.
3. **Run the repo's typecheck** (`mypy` / `npm run typecheck` / equivalent) — fix type errors.
4. **Run the full test suite** — `npm run test` / `make test` / equivalent. This includes unit tests AND E2E/Playwright if the repo has them. Do NOT skip tests — content changes can break test assertions.
5. **Verify branch name** — `git branch --show-current` must match `{FirstInitial}.{LastName}/{IIII}-{issue-name}`.

Pushing code that fails lint, formatting, or tests is a **minor feedback event**.

## CI Must Be Green Before Merge <!-- promotion-target: none -->
**No PR may be merged while CI is failing, even if failures are pre-existing.** If a new CI workflow is introduced and it catches pre-existing violations, those violations must be fixed before or in the same PR as the workflow addition.

- If CI is red on the target branch due to pre-existing issues, fix forward — create a predecessor PR that resolves the violations, merge it first, then merge the CI workflow PR.
- If CI is red on a feature branch, the PR author must fix the failures before requesting review.
- Merging a PR with known CI failures is a **moderate feedback event**.

**Why:** In Phase 2 Wave 1, PR #72 introduced a hook CI workflow that immediately failed on pre-existing ruff I001 lint in other files. CI went red on main because the violations weren't fixed before merge.

## CI Enforcement After PR Creation <!-- promotion-target: skill -->
After creating a PR, **every team member** must follow this process:

1. **Wait for all CI jobs to complete.** Do not merge or request review until CI has finished.
2. **If all CI jobs pass:** The PR is ready for review. Proceed with the normal review workflow.
3. **If any CI job fails:**
   - Investigate the failure and attempt to fix the root cause.
   - Push the fix to the **same branch** (the PR will update automatically).
   - Alert the project owner (user) with the following information:
     - Which CI job failed
     - Root cause of the failure
     - What was done to fix it
     - Whether project owner assistance is required
4. **If the failure cannot be resolved:** Do **NOT** merge the PR. Notify the project owner immediately and pause all dependent work until the issue is resolved.

Violating this process (e.g., merging with red CI, ignoring failures, or failing to escalate) is treated as a **moderate feedback event** per the Feedback System.

## Design-Rationale Block for Critical-Path PRs (Mandatory) <!-- promotion-target: skill -->

PRs that touch critical-path workflow DAGs, observability stacks, or alert-rule definitions MUST include a design-rationale block at the load-bearing decision point.

### When this requirement applies

- PRs touching `.github/workflows/promote.yml`, `deploy-stg.yml`, `deploy-prod.yml`, or any other workflow whose failure-mode propagates to prod gates.
- PRs touching `infra/prometheus/alerts.yml`, `infra/prometheus/prometheus.yml`, blackbox/textfile-exporter configs, or any other observability artifact whose silence vs. firing has operator consequence.
- PRs introducing a new gate, predicate, or DAG ordering whose correctness depends on a specific multi-path outcome matrix.

### What the block must contain

- Either an inline file comment at the gate/predicate/decision point (preferred when the rationale binds to a specific code site), OR a section in the PR body labeled `Design rationale` / `Outcome matrix` / `Sequencing rationale`.
- A walk of the predicate algebra OR an outcome truth table OR a design-rationale-vs-alternatives comparison — whichever load-bears the decision.
- Citations to the issue body's spec (or a `Reality post-#N` mapping if the spec has drifted from current state).

### Worked examples (Phase 3 Wave 1)

- `noorinalabs-deploy#198` lines 232-258 — gate-stg-verify rationale block walking three failure modes (missing artifact, stale artifact, schema-version mismatch).
- `noorinalabs-deploy#201` PR body — 5-path retag-gate truth table (success/skipped/failure crosses + break-glass).
- `noorinalabs-deploy#208` `infra/blackbox-exporter/blackbox.yml` — load-bearing assertion comments per module.
- `noorinalabs-deploy#210` `infra/prometheus/alerts.yml` — dual-alert design comment (Failure vs Stale split rationale).

### Reviewer enforcement

Absence of a design-rationale block on an applicable PR is grounds for Changes-Requested. The block's quality (rather than its mere presence) is what reviewers should engage with.

### Severity if violated

Minor — but recurrence is moderate. The discipline is high-leverage for incident-response readability and retro-evidence quality; both pay dividends across multiple waves.

### Why

Phase 3 Wave 1 produced 4 corroborating data points (above) where the design-rationale block earned positive reviewer engagement, surfaced design alternatives during review, and provided the canonical retro evidence later. Without it, gate-DAG correctness is invisible to anyone reading the PR after merge.

## Trust the Artifact, Not the Framing (Mandatory) <!-- promotion-target: skill -->

Both implementer and reviewer disciplines on the same axis: verify spec assumptions and PR-body framing against ground truth before action.

### Implementer side

Before implementing per a spec, issue body, or upstream brief, verify the spec's load-bearing claims against the actual artifact:

- Issue body says "alert exists at X / read it, don't re-implement" → check `git log -- X` and `grep` the file before assuming.
- Spec says "extend Y to add Z" → check Y's current shape (post-prior-merges) before drafting; the spec may predate later changes.
- Brief from manager says "use convention K" → check `git branch -a` / `git grep` for K-shaped artifacts before encoding it as truth.

If the spec's load-bearing claims diverge from ground truth, surface the gap to the manager BEFORE implementing — do not silently absorb the divergence.

**Authoritative example:** `noorinalabs-deploy#161` 3-x scope catch (issue body said alert exists at `#153`, alert had been deferred and never landed; verified via `git log` + `grep` before pushing dead code).

### Reviewer side

Read the diff against the actual artifact (Caddyfile, compose env-vars, terraform state, alert YAML, runbook, etc.), not against the PR body's framing of what the diff does. PR-body framing is a useful navigation aid; the diff against the artifact is the ground truth.

**Authoritative example:** `noorinalabs-deploy#206` review caught a false-positive bug by walking `caddy/Caddyfile` lines 88-89 + 101 against the PR's section 3b dual-route logic. The PR-body framing said "user-service /health probe via Caddy rewrite + post-#156 subdomain fallback"; the artifact showed the fallback would route to isnad-graph instead of user-service, producing a silent false positive on user-service availability if user-service goes down.

### How to apply

- **Implementer:** before any Edit/Write inside a worktree, run `gh issue view`, `git log -- <load-bearing-path>`, and `grep` for any spec claim about existing artifacts.
- **Reviewer:** before posting Approved, walk at least one load-bearing claim in the PR body against the actual artifact via `gh api .../contents` or `git show <head>:<path>`.

### Severity if violated

- Implementer: silent absorption of a spec-vs-reality gap that produces dead code or wrong defaults is minor; producing a security regression (route mismatch, env-var leak, etc.) is severe.
- Reviewer: rubber-stamping based on PR-body framing alone is minor; missing a false-positive bug because reviewer read the framing but not the artifact is moderate.

### Why

Phase 3 Wave 1 produced 4 corroborating data points across two roles. Implementer side: `#161` scope catch + `#206` Reality-post-#87 mapping table. Reviewer side: `#206` Caddyfile evidence-receipts. Both halves of the same discipline.


## Trivial Cross-Repo Doc Sweep

When a single doc-sync change must land identically in N>1 child repos (e.g., backslash→slash path corrections, broken-URL fixes, copyright-year updates, identical CLAUDE.md sentence sync), a **Single-Reviewer Exception** is granted per child PR provided ALL of the following hold:

1. **Byte-identical diff** — every child PR's diff is byte-identical to every other (verifiable via `git show <pr-head>:<path> | diff -`). Per-repo adaptations (different branding, different file paths) DO NOT qualify; those go through standard 2-reviewer review.
2. **No behavior change** — change is doc/comment-only OR a configuration sync that produces no runtime difference.
3. **Tracking-issue link** — every child PR references one parent tracking issue in `noorinalabs-main` that enumerates all child PRs.
4. **CI green on every repo** — no CI failures across the sweep; one red CI revokes the exception for the whole sweep.

A sweep PR uses the same charter-format comments and TechDebt line as standard PRs. When the exception is invoked, the PR body must include a "Sweep:" line citing the tracking issue and the byte-identical-diff verification command.

**See also:** § Single-Reviewer Exception (Wave-Bootstrap Only) — a separate single-reviewer exception class for tooling/CI/hook-rollout PRs that gate subsequent wave work. The two exceptions are **independent budgets** (the wave-bootstrap 1-per-wave cap does not consume, and is not consumed by, doc-sweep waivers) and are **not cumulative** — a single PR may invoke at most one.

**Why:** P3W4 ran 4 separate per-repo PRs for an identical 1-line CLAUDE.md slash sync (isnad-graph#857, user-service#94, design-system#63, data-acquisition#34) — 4 review pairs, 4 CI runs, ~12 charter-format comments for a no-decision change. The 2-reviewer requirement is load-bearing for behavior changes; for byte-identical doc sweeps, the verification value is concentrated at the parent tracking issue, not at each child PR.

**Severity if violated:** Invoking the sweep exception on a non-byte-identical change, or skipping the tracking issue, is moderate (review-bypass for changes that needed standard review). The 2nd reviewer is the load-bearing safeguard against silent behavior change.

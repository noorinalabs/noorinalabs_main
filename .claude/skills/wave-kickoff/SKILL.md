---
name: wave-kickoff
description: Automated wave planning — branch creation, label management, issue labeling, kickoff comments, and execution plan
args: team_name, Phase number, Wave number
---

Automate the wave kickoff process for the `{team_name}` team.

> Note: all repo paths in bash blocks below are rooted at `$REPO_ROOT` to avoid cwd drift when the skill is invoked from a worktree or child-repo subdirectory (#149).

## Instructions

### 1. Create the deployments branch

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
cd "$REPO_ROOT"
git fetch origin
git checkout main && git pull origin main
git checkout -b deployments/phase{N}/wave-{M}
git push -u origin deployments/phase{N}/wave-{M}
```

If the branch already exists, check it out and pull latest instead.

### 2. Create wave label

Check if label `p{N}-wave-{M}` exists:

```bash
gh label list --search "p{N}-wave-{M}"
```

If missing, create it:

```bash
gh label create "p{N}-wave-{M}" --description "Phase {N} Wave {M}" --color "8B5CF6"
```

### 3. Pre-wave auth/scope audit

Verify the gh token has the scopes needed for this wave's operations. GitHub periodically hardens scope enforcement (e.g., Projects v2 requires the explicit `project` write scope; classic-Projects API deprecation). A missing scope mid-wave consumes orchestrator + user time chasing OAuth flows.

```bash
gh api -i user 2>&1 | grep -i "x-oauth-scopes"
```

Required scopes (baseline for all waves):
- `repo` — issues, PRs, comments, code
- `read:org` — roster / label lookups
- `project` — adding issues/PRs to the board (`gh project item-add`)
- `workflow` — editing `.github/workflows/*` files
- `gist`, `admin:public_key` — retained from prior grants

If any required scope is missing, instruct the user:
```
gh auth refresh -h github.com -s {missing_scope}
```
Wait for confirmation that scopes are updated before proceeding. Do NOT begin wave assignment with known-missing scopes.

**Why:** Phase 2 Wave 8 surfaced the Projects v2 scope gap mid-retro while trying to add PR #122 to the board. Fixing it interactively consumed ~30 minutes. Catching this at wave-kickoff prevents mid-wave interruptions.

### 4. Pre-wave CI triage

Before assigning issues, verify CI health across all repos in the wave scope:

```bash
gh run list --repo noorinalabs/{repo} --branch main --limit 1 --json conclusion
```

For each repo:
- If `conclusion` is `"success"`, mark it green.
- If `conclusion` is `"failure"` or missing, create a GitHub issue in that repo:
  ```bash
  gh issue create --repo noorinalabs/{repo} --title "CI red on main — triage before p{N}-wave-{M}" \
    --label "bug" --label "p{N}-wave-{M}" \
    --body "CI is failing on main. This must be triaged before wave work begins on this repo."
  ```
- Present a summary table to the user:
  | Repo | CI Status | Issue |
  |------|-----------|-------|
  | `noorinalabs-isnad-graph` | pass / **FAIL** | — / #NNN |

Flag repos with known-red CI so engineers are not confused by pre-existing failures.

### 5. Cross-reference wave issues against recent merges

Before posting kickoff comments, check if any wave issues were already resolved:

```bash
gh pr list --repo noorinalabs/{repo} --state merged --limit 20 --json number,title,body
```

For each merged PR:
1. Extract `Closes #N`, `Fixes #N`, or `Resolves #N` references from the PR body and title.
2. Compare those issue numbers against the wave issue list.
3. If a match is found, flag it to the user:
   ```
   ⚠ Issue #{N} ("{title}") may already be resolved by PR #{M} ("{pr_title}").
   Verify before assigning — remove from wave if confirmed fixed.
   ```

Wait for user confirmation before proceeding with assignment. Remove any confirmed-resolved issues from the wave list.

### 6. Collect issue list and assignments

Prompt the user for:
- List of issue numbers for this wave
- Assignee for each issue (FIRSTNAME_LASTNAME label)
- Peer review pairings (reviewer for each engineer)

Validate all assignee labels exist before proceeding:

```bash
gh label list --search "FIRSTNAME"
```

Create any missing labels before applying.

### 7. Label all issues

For each issue, apply the wave label and assignee label:

```bash
gh issue edit {NUMBER} --add-label "p{N}-wave-{M}" --add-label "{FIRSTNAME_LASTNAME}"
```

### 8. Post kickoff comments

Post a kickoff comment on each issue using charter format:

```
Requestor: Fatima.Okonkwo
Requestee: {Assignee.Name}
RequestOrReplied: Request

**Wave {M} Kickoff — Phase {N}**

This issue is assigned to you for p{N}-wave-{M}.
- Peer reviewer: {reviewer name}
- Branch from: `deployments/phase{N}/wave-{M}`
- Branch naming: `{FirstInitial}.{LastName}/{IIII}-{issue-slug}`
- Priority: {hotfix|security|bug|feature} (per charter § Wave Planning & Priority)

Please begin implementation.
```

### 9. Ontology librarian — both bakes required (MANDATORY)

**Two hooks enforce this independently, so both steps are required:**

**(a) Orchestrator bakes librarian output into the spawn prompt** — `enforce_ontology_context.py` scans the Agent tool prompt for the literal heading `## Ontology Context` and **blocks** the spawn if absent.

For each agent in the wave:
1. Identify the repos and code areas they'll modify
2. Run the librarian with a descriptive query:
   ```
   /ontology-librarian {repo} {area being modified}
   ```
3. Include the librarian's output (entities, services, conventions, stale warnings) in the agent's spawn prompt under a `## Ontology Context` section (literal heading — the hook matches on it)

**(b) Instruct the agent to run `/ontology-librarian` themselves as their FIRST action** — Hook 15 (`enforce_librarian_consulted.py`) scans the spawned agent's own transcript independently. Passing baked context from the orchestrator is not enough; Hook 15 still blocks Edit/Write/NotebookEdit until the agent invokes the librarian in their own session.

Spawn prompt pattern that satisfies both:
```
## MANDATORY first action
Run `/ontology-librarian {topic}` **yourself** in this session before any Edit/Write. Hook 15 scans your transcript.

## Ontology Context
(Baked from orchestrator's librarian run. Contents here.)
```

**Why:** In P2W3, running the librarian before spawning agents identified 10 stale issues — saving significant wasted effort. In P2W10 kickoff, the orchestrator forgot the `## Ontology Context` heading on 3 parallel spawns and all 3 were blocked.

### 9a. Delegation pattern — orchestrator spawns, managers request

Per charter `agents.md` § Hub-and-Spoke Orchestration Model + § Single-Leader Constraint:

- **Only the orchestrator (team lead) can call Agent.** Managers and implementers do not have the Agent tool.
- **Single team per session** — one `TeamCreate` per orchestrator session; additional TeamCreates fail with "Already leading team." Use `team_name: "noorinalabs"` for cross-repo waves.
- **Managers request implementer spawns** via `SendMessage` to the team lead with full context (name, roster file, issue, branch, reviewers, Contract ownership if applicable).
- **Team lead spawns each implementer** following step 9 above (both bakes).

When composing spawn prompts for implementers, pull the manager's specified reviewer pairings, branch names, and Contract expectations into the prompt so the implementer starts with full context.

### 10. Output execution plan

Generate and display a structured execution plan with:
- **Priority ordering:** hotfixes first, then security fixes, then bugs, then features (per charter § Wave Planning & Priority)
- **Issue table:** number, title, assignee, reviewer, priority tier
- **Dependencies:** any cross-PR dependencies identified
- **Estimated parallelism:** which issues can run concurrently

### 11. Report

Present the full plan to the user. Do NOT begin implementation until the user approves.

## What remains manual

- User must approve the execution plan before implementation starts
- User decides which issues to include in the wave
- Cross-team dependency resolution still requires lead coordination

# Branching Rules

## Deployments Branches

Each phase is organized into **waves** of parallel work. Before starting a wave, create a deployments branch:

```
deployments/phase{N}/wave-{M}
```

- Branched from `main` (pull latest first).
- **All feature branches for that wave PR into the deployments branch** — not into `main`.
- At the end of a phase, PR the deployments branch into `main`. **Wait for the user to merge** before starting the next phase.

## Feature Branches

- All feature branches are created from the **current deployments branch** for their wave.
- Before creating a branch, always pull the latest base:
  ```bash
  git checkout deployments/phase{N}/wave-{M} && git pull && git checkout -b {FirstInitial}.{LastName}/{IIII}-{issue-name}
  ```
- Worktree agents should similarly base their worktree on the deployments branch for their wave.
- **Worktree branch safety:** Each team member must verify they are on their own branch before committing. Never commit to another member's branch. Before every commit, run `git branch --show-current` and confirm the branch name matches `{FirstInitial}.{LastName}/...`. If the branch doesn't match, switch to the correct branch before committing.
- **Before submitting a PR**, the team member must merge the latest from the deployments branch into their feature branch to avoid merge conflicts:
  ```bash
  git fetch origin && git merge origin/deployments/phase{N}/wave-{M}
  ```
  Resolve any conflicts before pushing and creating the PR.

## Release Tagging Cadence

**Tags are created at the end of every wave** — after all PRs are merged but before the retro. Missing tags means missing GHCR images and deploy failures.

### Tag Format

| Context | Format | Example |
|---------|--------|---------|
| Wave release | `phase{N}-wave{M}` | `phase2-wave1` |
| Milestone release | `v{major}.{minor}.{patch}` | `v1.2.0` |

### Rules

1. **Every repo that had changes in the wave gets a tag.** Check merged PRs by wave label.
2. **Tags are created via `gh release create`** — this triggers GHCR publish workflows for repos that have them.
3. **Santiago Ferreira (Release Coordinator) owns tagging.** If unavailable, the orchestrator delegates.
4. **The `/wave-wrapup` skill includes tagging as step 12** — it is mandatory, not optional.
5. **Verify GHCR images were published** after tagging repos with publish-on-tag workflows.

### Repos Requiring Tags

| Repo | Has GHCR Publish? | Notes |
|------|-------------------|-------|
| `noorinalabs-isnad-graph` | Yes | Publishes on tag push |
| `noorinalabs-isnad-graph-ingestion` | No | No container image |
| `noorinalabs-deploy` | No | Config only, tag for versioning |
| `noorinalabs-design-system` | No | NPM package, not containerized |
| `noorinalabs-landing-page` | Yes | Publishes on tag push |
| `noorinalabs-main` | No | Org config, tag for versioning |

Failing to tag at wave end is a **minor feedback event** for the Release Coordinator.

## Worktree Cleanup

**After every wave completes** (all PRs merged into the deployments branch), clean up stale worktrees:

```bash
git worktree prune
```

This removes references to worktrees whose directories no longer exist. Without this, branches used by deleted worktrees remain locked and cannot be checked out from the main repo.

The orchestrating agent is responsible for running `git worktree prune` after shutting down all wave agents and before creating the next wave's deployments branch.

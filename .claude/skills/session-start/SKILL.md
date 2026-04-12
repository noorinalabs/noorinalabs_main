---
name: session-start
description: "MANDATORY first action in every session — runs full startup protocol (handoff, team, ontology, annunaki, wave, charter)"
---

# Session Start Protocol

**This skill MUST be invoked as the FIRST action in every new session.** Do not respond to the user's message, do not read files, do not run any other tool — invoke `/session-start` first. The user's actual request is handled AFTER this completes.

## Instructions

Execute all 6 steps below. Steps that are independent of each other SHOULD run in parallel. Present results in a single concise status table at the end.

### Step 0 — Handoff check

Read the session handoff file from project memory:

```
Read: ~/.claude/projects/-home-parameterization-code-noorinalabs-main/memory/session_handoff.md
```

If it exists, extract:
- What was done last session
- What's next
- Current branch, open PRs, open issues
- Any user notes

Summarize in 2-3 sentences. If the file doesn't exist, note "No handoff from previous session."

### Step 1 — Team cleanup

Stale team state from prior sessions causes "does not exist" / "already leading" errors. Always start fresh:

1. Run `TeamDelete` (will succeed even if no team exists)
2. Run `TeamCreate` with `team_name: "noorinalabs"` and `description: "Org-level coordination team for noorinalabs-main"`

Never try to reuse an existing team. Never skip this step.

### Step 2 — Ontology rebuild

Run `/ontology-rebuild` to resolve any dirty files from the previous session.

- If 0 dirty files, report "Ontology is current" and move on
- If dirty files exist, process them and commit the result
- This ensures the ontology reflects all changes before any new work begins

### Step 3 — Annunaki error check

Run `/annunaki` to check the error monitor.

- Report: hook active/inactive, error count, any new errors since last session
- If 5+ unprocessed errors, flag for `/annunaki-attack`
- If 0 errors or all are resolved PreToolUse blocks, report "No action needed"

### Step 4 — Wave/phase orientation

Read the current project state:

```bash
cat cross-repo-status.json
gh issue list --repo noorinalabs/noorinalabs-main --state open --limit 10 --json number,title,labels
```

Report:
- Active wave and phase
- Whether `cross-repo-status.json` is stale (check `last_updated` fields)
- Open issue count and any blockers
- Open PRs across repos

### Step 5 — Charter freshness check

Read the tail of the feedback log:

```bash
tail -40 .claude/team/feedback_log.md
```

Check for:
- Unapplied retro proposals (action items without corresponding changes)
- New hooks or skills introduced since the last charter update
- Any pending fire/hire actions

Report findings or "Charter is current."

## Output format

After all steps complete, present a single status block:

```
**Session Start — Complete**

| Step | Status |
|------|--------|
| 0. Handoff | {summary} |
| 1. Team | {created fresh / error} |
| 2. Ontology | {N dirty resolved / current} |
| 3. Annunaki | {N errors, action needed? / clear} |
| 4. Wave | {active wave, stale?, issues} |
| 5. Charter | {current / proposals pending} |

{Then address the user's actual message/request}
```

## What this skill does NOT do

- It does not begin any implementation work
- It does not create issues or PRs
- It does not modify the charter or team roster
- It only establishes situational awareness so the session starts informed

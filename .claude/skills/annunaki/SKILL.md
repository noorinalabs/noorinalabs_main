---
name: annunaki
description: View Annunaki error monitor status — shows recent captured errors and monitoring health
---

Display the current state of the Annunaki error monitor. This skill is the **status viewer** for the always-on error monitoring hook (`annunaki_monitor.py`).

## How it works

The Annunaki system has two parts:
1. **Monitor (hook):** A `PostToolUse` hook on Bash that fires after every command, detects errors via exit codes and pattern matching, and logs them to `.claude/annunaki/errors.jsonl`
2. **This skill:** Reads and summarizes the error log

## Instructions

### 1. Verify the hook is active

Check that `annunaki_monitor.py` is registered in `.claude/settings.json` under `PostToolUse`:

```bash
cat .claude/settings.json | grep -c annunaki_monitor
```

If 0, warn the user that monitoring is not active and offer to wire it up.

### 2. Read the error log

```bash
wc -l .claude/annunaki/errors.jsonl 2>/dev/null || echo "0 (no errors logged yet)"
```

### 3. Show recent errors

Display the last 20 errors with timestamps and commands:

```bash
tail -20 .claude/annunaki/errors.jsonl 2>/dev/null
```

Parse and present them in a readable table:

```
**Annunaki Error Monitor — Status**

**Hook:** {active | NOT ACTIVE}
**Total errors logged:** {count}
**Log file:** .claude/annunaki/errors.jsonl

**Recent Errors (last 20):**

| # | Timestamp | Command (truncated) | Exit Code | Pattern |
|---|-----------|---------------------|-----------|---------|
| 1 | ...       | ...                 | ...       | ...     |
```

### 4. Show error frequency

If there are more than 10 errors, show a breakdown:

```
**Error Frequency:**
- Errors in last hour: {N}
- Errors in last 24h: {N}
- Most common pattern: {pattern} ({count} occurrences)
- Most error-prone command prefix: {prefix} ({count} occurrences)
```

### 5. Suggest /annunaki-attack if warranted

If there are 5+ unprocessed errors, suggest running `/annunaki-attack` to analyze and fix them.

## What this skill does NOT do

- It does not fix errors — use `/annunaki-attack` for that
- It does not modify the error log
- It does not create issues or PRs

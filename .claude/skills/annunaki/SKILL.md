---
name: annunaki
description: View Annunaki error monitor status — shows recent captured errors and monitoring health
---

Display the current state of the Annunaki error monitor. This skill is the **status viewer** for the always-on error monitoring hook (`annunaki_monitor.py`).

> Note: all repo paths in bash blocks below are rooted at `$REPO_ROOT` to avoid cwd drift when the skill is invoked from a worktree or child-repo subdirectory (#149).

## How it works

The Annunaki system has two parts:
1. **Monitor (hook):** A `PostToolUse` hook on Bash that fires after every command, detects errors via exit codes and pattern matching, and logs them to `.claude/annunaki/errors.jsonl`
2. **This skill:** Reads and summarizes the error log

## Instructions

### 1. Verify the hook is active

Check that `annunaki_monitor.py` is registered in `.claude/settings.json` under `PostToolUse`:

```bash
REPO_ROOT="$(git rev-parse --show-toplevel)"
grep -c annunaki_monitor "$REPO_ROOT/.claude/settings.json"
```

If 0, warn the user that monitoring is not active and offer to wire it up.

### 2. Read the error log

```bash
wc -l "$REPO_ROOT/.claude/annunaki/errors.jsonl" 2>/dev/null || echo "0 (no errors logged yet)"
```

**Parsing note:** the log is JSONL but may contain blank or whitespace-only lines from historical manual edits. Any parser you write MUST skip them — `json.loads("")` raises `JSONDecodeError`. The canonical pattern is:

```python
for line in open(path):
    line = line.strip()
    if not line:
        continue
    try:
        rec = json.loads(line)
    except json.JSONDecodeError:
        continue  # skip corrupt lines
```

### 3. Show recent errors

Display the last 20 errors with timestamps and commands:

```bash
tail -20 "$REPO_ROOT/.claude/annunaki/errors.jsonl" 2>/dev/null
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

Use the blank-line-safe parser from § 2 when building the breakdown. A one-liner Bash recipe:

```bash
python3 - <<'PY' "$REPO_ROOT/.claude/annunaki/errors.jsonl"
import json, sys
from collections import Counter
by_hook = Counter()
with open(sys.argv[1]) as f:
    for line in f:
        line = line.strip()
        if not line:
            continue
        try:
            by_hook[json.loads(line).get("hook", "unknown")] += 1
        except json.JSONDecodeError:
            continue
for h, c in by_hook.most_common():
    print(f"{c:4d}  {h}")
PY
```

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

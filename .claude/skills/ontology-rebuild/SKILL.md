---
name: ontology-rebuild
description: Resolve dirty ontology entries — scan changed files, update ontology and auto-updatable docs, mark resolved
args: scope
---

Rebuild the ontology for files that have changed since the last resolution pass. The `scope` argument is optional — if omitted, processes all dirty files. If provided, can be `code`, `docs`, or a specific repo name to limit scope.

## Context

The ontology system has three roles:
- **Change Tracker** (hook) — automatically updates `ontology/checksums.json` whenever files are edited. Sets `last_tracked` hash.
- **Change Resolver** (this skill) — reads dirty entries from checksums, processes files, updates ontology. Sets `last_resolved` = `last_tracked`.
- **Librarian** (`/ontology-librarian`) — read-only reference to the ontology.

A file is "dirty" when `last_tracked != last_resolved` in `checksums.json`.

## Instructions

### 1. Read checksums and identify dirty files

```bash
cat ontology/checksums.json
```

Build a list of all files where `last_tracked != last_resolved`. If no dirty files exist, report "Ontology is up to date — no dirty files" and stop.

If `scope` argument is provided, filter:
- `code` — only source code files (`.py`, `.ts`, `.tsx`, `.js`, `.jsx`, `.go`, `.yaml`, `.yml`, `.toml`, `.json`, `.tf`, `.hcl`)
- `docs` — only documentation files (`.md`, `.rst`, `.txt`)
- `{repo-name}` — only files under that repo's directory (e.g., `noorinalabs-isnad-graph/`)

### 2. Process files in order: code → docs → high-level-docs

Process dirty files in this order:
1. **Source code files** — read each file, extract entities, services, APIs, patterns, data models
2. **Auto-updatable docs** (READMEs, CLAUDE.md, inline docs) — check for drift from code, update if needed
3. **Recommend-only docs** (high-level-docs/, engineering docs, mermaid diagrams, architecture documents in any repo) — read for intent and purpose, note recommendations but do NOT modify

For each file:
- Read the file content
- Determine which ontology file(s) it affects:
  - Domain entities/relationships → `ontology/domain.yaml`
  - Services, APIs, data stores, infrastructure → `ontology/services.yaml`
  - Conventions, patterns, tooling → `ontology/conventions.md`
  - Repo-specific internals → `ontology/repos/{repo-name}.yaml`
- Update the relevant ontology file(s) with extracted knowledge
- If the file is an auto-updatable doc that has drifted from code, update it

### 3. Cross-reference and consistency

After processing all dirty files:
- Check for orphaned entities (referenced but not defined)
- Check for stale references (defined but the source file no longer contains them)
- Verify cross-repo integration points are consistent between `services.yaml` and repo files

### 4. Update checksums

For each processed file, set `last_resolved = last_tracked` and `resolved_at = now` in `checksums.json`.

Also update checksums for any ontology files that were modified during this pass.

### 5. Report

```
**Ontology Rebuild Complete**

**Files processed:** {count}
**Ontology files updated:**
- domain.yaml: {entities added/updated/removed}
- services.yaml: {services added/updated/removed}
- conventions.md: {sections updated}
- repos/{name}.yaml: {changes}

**Docs auto-updated:** {list of docs that were updated to match code}

**Recommend-only changes (requires human review):**
- {file}: {recommended change}

**Consistency issues found:** {list or "None"}
```

### 6. Commit ontology changes

Stage and commit all ontology changes and any auto-updated docs. Use the Standards & Quality Lead identity (Aino Virtanen) for ontology commits:

```bash
git add ontology/
# Also add any auto-updated docs
git -c user.name="Aino Virtanen" -c user.email="parametrization+Aino.Virtanen@gmail.com" commit -m "ontology: rebuild — {summary of changes}"
```

## Docs update policy

| Doc type | Location | Action |
|----------|----------|--------|
| READMEs | Any repo | Auto-update to match code |
| CLAUDE.md | Any repo | Auto-update to match code |
| Inline code docs | Any repo | Auto-update to match code |
| high-level-docs/ | noorinalabs-main | Read-only — recommend changes |
| Engineering docs | Any repo (architecture.md, diagrams, etc.) | Read-only — recommend changes |
| Mermaid diagrams | Any repo | Read-only — recommend changes |

## What remains manual

- Recommend-only doc updates require human review and decision
- Ontology structure changes (adding new top-level categories) should be discussed first
- Removing entities requires confirmation — prefer marking as deprecated

#!/usr/bin/env python3
"""Upsert top-level keys in cross-repo-status.json preserving compact-inline shape.

The skill ecosystem (/wave-kickoff, /wave-start) writes that file with deliberate
mixed style: top-level wave_{N}_* keys are compact single-liners, older
wave_*_scope blocks are pretty-indented. A naive `jq ... > tmp && mv` round-trip
reformats every compact line to jq's default pretty form, doubling the file
length and producing a 500+ line cosmetic diff per wave.

This helper does targeted text-level upsert:
  - If the key exists at top level → replace its line in place.
  - If the key does not exist → insert a new compact-inline line right after
    the most-recent wave_{N}_* sibling (or before the closing `}`).

Validates JSON before AND after the rewrite so a malformed write is caught.

Invocation:
  upsert_status_keys.py <path> <key>=<json-encoded-value> [<key>=<json-encoded-value> ...]

Example:
  upsert_status_keys.py cross-repo-status.json \
    wave_5_scope_reconciled_at='"2026-05-05T22:31:00Z"' \
    wave_5_scope_reconciliation_note='"manual run"'

Each VALUE must be a self-contained JSON literal (string/number/bool/array/object).
Strings include their quotes — pass `'"foo"'` from the shell.
"""

import json
import re
import sys
from pathlib import Path


def upsert_top_level_key(text: str, key: str, json_value: str) -> str:
    """Replace `"<key>": ...,` line in place, or insert a new line if absent.

    Insertion point: after the last existing line whose top-level key matches
    `wave_<N>_*` for the same wave number embedded in `key` (best-effort sibling
    grouping). Falls back to inserting right after the opening `{` line.
    """
    line_re = re.compile(r'^(  )"' + re.escape(key) + r'":\s.*?,?\s*$', re.MULTILINE)
    new_line = f'  "{key}": {json_value},'
    m = line_re.search(text)
    if m:
        existing = m.group(0)
        last_existing = existing.rstrip()
        if last_existing.endswith(","):
            replacement = new_line
        else:
            replacement = new_line.rstrip(",")
        return text[: m.start()] + replacement + text[m.end() :]

    wave_num_match = re.match(r"wave_(\d+)_", key)
    if wave_num_match:
        sibling_re = re.compile(
            r'^(  )"wave_' + re.escape(wave_num_match.group(1)) + r'_[^"]+":.*$',
            re.MULTILINE,
        )
        siblings = list(sibling_re.finditer(text))
        if siblings:
            last = siblings[-1]
            return text[: last.end()] + "\n" + new_line + text[last.end() :]

    open_brace = text.find("{\n")
    if open_brace < 0:
        raise ValueError("could not locate opening `{` line for insertion")
    insertion_point = open_brace + 2
    return text[:insertion_point] + new_line + "\n" + text[insertion_point:]


def main(argv: list[str]) -> int:
    if len(argv) < 3:
        print(__doc__, file=sys.stderr)
        return 2

    path = Path(argv[1])
    pairs = []
    for arg in argv[2:]:
        if "=" not in arg:
            print(f"ERROR: argument {arg!r} is not key=value", file=sys.stderr)
            return 2
        k, _, raw = arg.partition("=")
        try:
            decoded = json.loads(raw)
        except json.JSONDecodeError as exc:
            print(f"ERROR: value for {k} is not valid JSON: {exc}", file=sys.stderr)
            return 2
        pairs.append((k, raw, decoded))

    text = path.read_text()
    parsed = json.loads(text)

    for key, json_value, decoded in pairs:
        text = upsert_top_level_key(text, key, json_value)
        parsed[key] = decoded

    reparsed = json.loads(text)
    if reparsed != parsed:
        print(
            "ERROR: text-level upsert diverged from logical upsert; aborting write",
            file=sys.stderr,
        )
        return 1

    path.write_text(text)
    for key, _, _ in pairs:
        print(f"  upserted: {key}")
    return 0


if __name__ == "__main__":
    sys.exit(main(sys.argv))

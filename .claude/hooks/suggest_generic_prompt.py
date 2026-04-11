#!/usr/bin/env python3
"""PostToolUse hook: Suggest generic prompts for .claude/ changes.

Fires after Edit or Write on files under .claude/. Emits a systemMessage
reminding the agent to consider whether the change could be genericized
into a product-neutral prompt for the 2real-team-framework repo.

Exit codes:
  0 — always (advisory hook, never blocks)
"""

import json
import sys
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent.parent
FRAMEWORK_REPO = REPO_ROOT.parent / "2real-team-framework"
GENERIC_PROMPTS_DIR = FRAMEWORK_REPO / "generic_prompts"

# File categories and what kind of generic prompt they suggest
CATEGORY_MAP = {
    "hooks": {
        "pattern": "/hooks/",
        "prompt_type": "hook",
        "suggestion": "a product-neutral hook that enforces the same pattern",
    },
    "skills": {
        "pattern": "/skills/",
        "prompt_type": "skill",
        "suggestion": "a product-neutral skill prompt that provides the same workflow",
    },
    "charter": {
        "pattern": "/team/charter",
        "prompt_type": "charter section",
        "suggestion": "a product-neutral charter template section",
    },
    "settings": {
        "pattern": "settings.json",
        "prompt_type": "settings template",
        "suggestion": "a product-neutral settings.json snippet or template",
    },
}


def _classify(file_path: str) -> dict | None:
    """Classify a .claude/ file into a prompt category."""
    for _name, info in CATEGORY_MAP.items():
        if info["pattern"] in file_path:
            return info
    return {
        "prompt_type": "configuration",
        "suggestion": "a product-neutral version of this configuration",
    }


def main() -> None:
    try:
        input_data = json.load(sys.stdin)
    except (json.JSONDecodeError, EOFError):
        sys.exit(0)

    tool_name = input_data.get("tool_name", "")
    if tool_name not in ("Edit", "Write"):
        sys.exit(0)

    file_path = input_data.get("tool_input", {}).get("file_path", "")
    if not file_path:
        sys.exit(0)

    # Only trigger for files under .claude/
    if "/.claude/" not in file_path:
        sys.exit(0)

    # Skip the ontology tracker checksum updates and annunaki logs
    skip_patterns = [
        "ontology/checksums.json",
        "annunaki/errors.jsonl",
    ]
    if any(p in file_path for p in skip_patterns):
        sys.exit(0)

    category = _classify(file_path)
    rel_path = file_path.split("/.claude/")[-1] if "/.claude/" in file_path else file_path

    framework_exists = GENERIC_PROMPTS_DIR.is_dir()
    framework_note = ""
    if framework_exists:
        framework_note = (
            " If the user approves, create the generic prompt file in "
            f"{GENERIC_PROMPTS_DIR} and offer to commit it."
        )

    message = (
        f"[Generic Prompt Suggestion] You just modified `.claude/{rel_path}` — "
        f"a {category['prompt_type']}. Consider whether this change could be "
        f"genericized into {category['suggestion']} for reuse in other projects. "
        f"If so, draft a product-neutral version (strip project-specific names, "
        f"paths, team members, repo names) and present it to the user for review."
        f"{framework_note}"
    )

    result = {"decision": "allow", "systemMessage": message}
    print(json.dumps(result))
    sys.exit(0)


if __name__ == "__main__":
    main()

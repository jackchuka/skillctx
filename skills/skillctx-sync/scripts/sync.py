#!/usr/bin/env python3
"""Find migrated skills and report which need a resolver update.

Usage:
    sync.py scan <skills-dir> <current-version>
        Scan for migrated skills and print JSON with status of each.

    sync.py update <skill-dir> <resolver-src> <current-version>
        Copy resolver, update frontmatter version, and refresh the setup block.

Zero external dependencies — uses only Python stdlib.
"""

from __future__ import annotations

import json
import re
import shutil
import sys
from pathlib import Path

MARKER_BEGIN = "<!-- skillctx:begin -->"
MARKER_END = "<!-- skillctx:end -->"

SETUP_TEMPLATE = """\
<!-- skillctx:begin -->
## Setup
Locate this skill's directory (the folder containing this SKILL.md), then run the
resolver script from there:

```
python <skill-dir>/scripts/skillctx-resolve.py resolve {skill_name}
```

The resolver outputs each binding as `key: value` (one per line).
For list values, it outputs JSON (e.g., `orgs: ["acme", "widgets-inc"]`).
Substitute each `{{binding_key}}` placeholder below with the resolved value.

If any values are missing or the user requests changes, use:
```
python <skill-dir>/scripts/skillctx-resolve.py set {skill_name} <key> <value>
```
<!-- skillctx:end -->"""


def find_migrated_skills(skills_dir: Path, current_version: str) -> list[dict[str, str]]:
    """Scan a directory of skills and return status of each migrated skill."""
    results = []
    for skill_md in sorted(skills_dir.glob("*/SKILL.md")):
        text = skill_md.read_text()
        version = extract_skillctx_version(text)
        if version is None:
            continue

        skill_name = skill_md.parent.name
        status = "current" if version == current_version else "outdated"

        results.append(
            {
                "skill": skill_name,
                "path": str(skill_md.parent),
                "version": version,
                "status": status,
            }
        )

    return results


def extract_skillctx_version(text: str) -> str | None:
    """Extract metadata.skillctx.version from YAML frontmatter."""
    fm = extract_frontmatter(text)
    if fm is None:
        return None
    match = re.search(r"skillctx:\s*\n\s+version:\s*[\"']?([^\s\"']+)", fm)
    return match.group(1) if match else None


def extract_frontmatter(text: str) -> str | None:
    """Return the YAML frontmatter string, or None."""
    if not text.startswith("---"):
        return None
    end = text.find("---", 3)
    if end == -1:
        return None
    return text[3:end]


def update_frontmatter_version(text: str, new_version: str) -> str:
    """Update or insert metadata.skillctx.version in frontmatter."""
    fm = extract_frontmatter(text)
    if fm is None:
        return text

    if "skillctx:" in fm:
        # Update existing version
        updated_fm = re.sub(
            r"(skillctx:\s*\n\s+version:\s*)[\"']?[^\s\"']+[\"']?",
            rf'\g<1>"{new_version}"',
            fm,
        )
    else:
        # Append skillctx block under metadata
        if "metadata:" in fm:
            updated_fm = re.sub(
                r"(metadata:.*?)(\Z)",
                rf'\1\n  skillctx:\n    version: "{new_version}"\2',
                fm,
                flags=re.DOTALL,
            )
        else:
            updated_fm = fm.rstrip() + f'\nmetadata:\n  skillctx:\n    version: "{new_version}"\n'

    return text.replace(fm, updated_fm, 1)


def replace_setup_block(text: str, skill_name: str) -> str:
    """Replace the <!-- skillctx:begin --> ... <!-- skillctx:end --> block."""
    begin_idx = text.find(MARKER_BEGIN)
    end_idx = text.find(MARKER_END)
    if begin_idx == -1 or end_idx == -1:
        return text

    end_idx += len(MARKER_END)
    new_block = SETUP_TEMPLATE.format(skill_name=skill_name)
    return text[:begin_idx] + new_block + text[end_idx:]


def cmd_scan(skills_dir: str, current_version: str) -> int:
    results = find_migrated_skills(Path(skills_dir), current_version)
    print(json.dumps(results, indent=2))
    return 0


def cmd_update(skill_dir: str, resolver_src: str, current_version: str) -> int:
    skill_path = Path(skill_dir)
    skill_md = skill_path / "SKILL.md"
    resolver_src_path = Path(resolver_src)

    if not skill_md.exists():
        print(f"error: {skill_md} not found", file=sys.stderr)
        return 1

    if not resolver_src_path.exists():
        print(f"error: resolver source {resolver_src_path} not found", file=sys.stderr)
        return 1

    skill_name = skill_path.name

    # Copy resolver
    dest_scripts = skill_path / "scripts"
    dest_scripts.mkdir(exist_ok=True)
    dest = dest_scripts / "skillctx-resolve.py"
    shutil.copy2(resolver_src_path, dest)
    dest.chmod(0o755)

    # Update SKILL.md
    text = skill_md.read_text()
    text = update_frontmatter_version(text, current_version)
    text = replace_setup_block(text, skill_name)
    skill_md.write_text(text)

    print(f"updated: {skill_name} → v{current_version}")
    return 0


def print_usage() -> None:
    print("usage: sync.py <scan|update> ...")
    print("  scan <skills-dir> <current-version>")
    print("  update <skill-dir> <resolver-src> <current-version>")


def main() -> int:
    if len(sys.argv) < 2 or sys.argv[1] in ("-h", "--help"):
        print_usage()
        return 0 if len(sys.argv) >= 2 else 1

    command = sys.argv[1]

    if command == "scan" and len(sys.argv) == 4:
        return cmd_scan(sys.argv[2], sys.argv[3])
    elif command == "update" and len(sys.argv) == 5:
        return cmd_update(sys.argv[2], sys.argv[3], sys.argv[4])
    else:
        print(f"error: invalid arguments for '{command}'", file=sys.stderr)
        return 1


if __name__ == "__main__":
    sys.exit(main())

#!/usr/bin/env python3
"""Sync version from pyproject.toml to SKILL.md files and marketplace.json."""

from __future__ import annotations

import json
import re
import sys
from pathlib import Path

ROOT = Path(__file__).resolve().parent.parent


def read_pyproject_version() -> str:
    text = (ROOT / "pyproject.toml").read_text()
    match = re.search(r'^version\s*=\s*"([^"]+)"', text, re.MULTILINE)
    if not match:
        sys.exit("Could not find version in pyproject.toml")
    return match.group(1)


def update_skill_md(path: Path, version: str) -> bool:
    text = path.read_text()
    updated = re.sub(
        r"^(\s+version:\s*).+$",
        rf"\g<1>{version}",
        text,
        count=1,
        flags=re.MULTILINE,
    )
    if updated == text:
        return False
    path.write_text(updated)
    return True


def update_plugin_json(path: Path, version: str) -> bool:
    data = json.loads(path.read_text())
    if data.get("version") == version:
        return False
    data["version"] = version
    path.write_text(json.dumps(data, indent=2) + "\n")
    return True


def update_readme_badge(path: Path, version: str) -> bool:
    text = path.read_text()
    updated = re.sub(
        r"(https://img\.shields\.io/badge/version-)[^-]+(-.+?\.svg)",
        rf"\g<1>{version}\2",
        text,
    )
    if updated == text:
        return False
    path.write_text(updated)
    return True


def update_marketplace_json(path: Path, version: str) -> bool:
    data = json.loads(path.read_text())
    changed = False

    for plugin in data.get("plugins", []):
        if plugin.get("version") != version:
            plugin["version"] = version
            changed = True

    if changed:
        path.write_text(json.dumps(data, indent=2) + "\n")
    return changed


def main() -> None:
    version = read_pyproject_version()
    print(f"Source version: {version} (pyproject.toml)")

    updated: list[str] = []
    skipped: list[str] = []

    # SKILL.md files
    for skill_md in sorted(ROOT.glob("skills/*/SKILL.md")):
        rel = skill_md.relative_to(ROOT)
        if update_skill_md(skill_md, version):
            updated.append(str(rel))
        else:
            skipped.append(str(rel))

    # README.md badge
    readme = ROOT / "README.md"
    if readme.exists():
        rel = readme.relative_to(ROOT)
        if update_readme_badge(readme, version):
            updated.append(str(rel))
        else:
            skipped.append(str(rel))

    # .claude-plugin JSON files
    plugin_dir = ROOT / ".claude-plugin"
    for name, updater in [
        ("plugin.json", update_plugin_json),
        ("marketplace.json", update_marketplace_json),
    ]:
        path = plugin_dir / name
        if path.exists():
            rel = path.relative_to(ROOT)
            if updater(path, version):
                updated.append(str(rel))
            else:
                skipped.append(str(rel))

    if updated:
        print(f"Updated: {', '.join(updated)}")
    if skipped:
        print(f"Already current: {', '.join(skipped)}")
    if not updated:
        print("Everything up to date.")


if __name__ == "__main__":
    main()

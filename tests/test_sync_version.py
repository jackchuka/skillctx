#!/usr/bin/env python3
"""Tests for scripts/sync-version.py."""

from __future__ import annotations

import importlib.util
import json
import textwrap
from pathlib import Path

SCRIPT = Path(__file__).parent.parent / "scripts" / "sync-version.py"

_spec = importlib.util.spec_from_file_location("sync_version", SCRIPT)
assert _spec and _spec.loader
_mod = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_mod)

read_pyproject_version = _mod.read_pyproject_version
update_skill_md = _mod.update_skill_md
update_plugin_json = _mod.update_plugin_json
update_marketplace_json = _mod.update_marketplace_json


class TestReadPyprojectVersion:
    def test_reads_version(self):
        version = read_pyproject_version()
        # Should match the pattern x.y.z
        assert version
        parts = version.split(".")
        assert len(parts) >= 2


class TestUpdateSkillMd:
    def test_updates_version(self, tmp_path: Path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            textwrap.dedent("""\
            ---
            name: test-skill
            metadata:
              version: 0.1.0
            ---
            # Test
        """)
        )
        assert update_skill_md(skill_md, "0.2.0")
        assert "version: 0.2.0" in skill_md.read_text()

    def test_no_change_when_current(self, tmp_path: Path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            textwrap.dedent("""\
            ---
            name: test-skill
            metadata:
              version: 0.2.0
            ---
            # Test
        """)
        )
        assert not update_skill_md(skill_md, "0.2.0")

    def test_no_change_when_no_version_field(self, tmp_path: Path):
        skill_md = tmp_path / "SKILL.md"
        skill_md.write_text(
            textwrap.dedent("""\
            ---
            name: test-skill
            ---
            # Test
        """)
        )
        assert not update_skill_md(skill_md, "0.2.0")


class TestUpdatePluginJson:
    def test_updates_version(self, tmp_path: Path):
        path = tmp_path / "plugin.json"
        path.write_text(json.dumps({"name": "test", "version": "0.1.0"}))
        assert update_plugin_json(path, "0.2.0")
        assert json.loads(path.read_text())["version"] == "0.2.0"

    def test_no_change_when_current(self, tmp_path: Path):
        path = tmp_path / "plugin.json"
        path.write_text(json.dumps({"name": "test", "version": "0.2.0"}))
        assert not update_plugin_json(path, "0.2.0")


class TestUpdateMarketplaceJson:
    def test_updates_all_plugin_versions(self, tmp_path: Path):
        path = tmp_path / "marketplace.json"
        data = {"plugins": [{"name": "a", "version": "0.1.0"}, {"name": "b", "version": "0.1.0"}]}
        path.write_text(json.dumps(data))
        assert update_marketplace_json(path, "0.2.0")
        result = json.loads(path.read_text())
        assert all(p["version"] == "0.2.0" for p in result["plugins"])

    def test_no_change_when_current(self, tmp_path: Path):
        path = tmp_path / "marketplace.json"
        data = {"plugins": [{"name": "a", "version": "0.2.0"}]}
        path.write_text(json.dumps(data))
        assert not update_marketplace_json(path, "0.2.0")

    def test_empty_plugins_list(self, tmp_path: Path):
        path = tmp_path / "marketplace.json"
        path.write_text(json.dumps({"plugins": []}))
        assert not update_marketplace_json(path, "0.2.0")

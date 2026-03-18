#!/usr/bin/env python3
"""Tests for skillctx-sync scripts/sync.py."""

import importlib.util
import json
import subprocess
import sys
from pathlib import Path

import pytest

SYNC_SCRIPT = Path(__file__).parent.parent / "skills" / "skillctx-sync" / "scripts" / "sync.py"

_spec = importlib.util.spec_from_file_location("sync", SYNC_SCRIPT)
assert _spec and _spec.loader
_sync = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_sync)

extract_frontmatter = _sync.extract_frontmatter
extract_skillctx_version = _sync.extract_skillctx_version
find_migrated_skills = _sync.find_migrated_skills
replace_setup_block = _sync.replace_setup_block
update_frontmatter_version = _sync.update_frontmatter_version

SKILL_MD_MIGRATED = """\
---
name: test-skill
metadata:
  skillctx:
    version: "0.1.0"
---

# test-skill

<!-- skillctx:begin -->
## Setup
Old setup block content.
<!-- skillctx:end -->

Rest of skill.
"""

SKILL_MD_CURRENT = """\
---
name: up-to-date-skill
metadata:
  skillctx:
    version: "0.2.0"
---

# up-to-date-skill

<!-- skillctx:begin -->
## Setup
Current setup block.
<!-- skillctx:end -->
"""

SKILL_MD_NOT_MIGRATED = """\
---
name: plain-skill
---

# plain-skill

No skillctx here.
"""


def _make_skills_dir(tmp_path: Path, skills: dict[str, str]) -> Path:
    """Create a skills directory with given skill name -> SKILL.md content."""
    skills_dir = tmp_path / "skills"
    for name, content in skills.items():
        skill_dir = skills_dir / name
        skill_dir.mkdir(parents=True)
        (skill_dir / "SKILL.md").write_text(content)
    return skills_dir


# --- unit tests: extract_frontmatter ---


class TestExtractFrontmatter:
    def test_extracts_valid_frontmatter(self):
        fm = extract_frontmatter(SKILL_MD_MIGRATED)
        assert fm is not None
        assert "name: test-skill" in fm

    def test_returns_none_without_frontmatter(self):
        assert extract_frontmatter("# Just a heading\nNo frontmatter.") is None

    def test_returns_none_for_unclosed_frontmatter(self):
        assert extract_frontmatter("---\nname: broken\n") is None


# --- unit tests: extract_skillctx_version ---


class TestExtractSkillctxVersion:
    def test_extracts_version_from_migrated_skill(self):
        assert extract_skillctx_version(SKILL_MD_MIGRATED) == "0.1.0"

    def test_returns_none_for_unmigrated_skill(self):
        assert extract_skillctx_version(SKILL_MD_NOT_MIGRATED) is None

    def test_returns_none_without_frontmatter(self):
        assert extract_skillctx_version("# No frontmatter") is None


# --- unit tests: update_frontmatter_version ---


class TestUpdateFrontmatterVersion:
    def test_updates_existing_version(self):
        result = update_frontmatter_version(SKILL_MD_MIGRATED, "0.2.0")
        assert '"0.2.0"' in result
        assert "0.1.0" not in result
        assert "Rest of skill." in result

    def test_inserts_skillctx_block_under_metadata(self):
        text = "---\nname: my-skill\nmetadata:\n  author: someone\n---\n\n# my-skill\n"
        result = update_frontmatter_version(text, "0.1.0")
        assert "skillctx:" in result
        assert '"0.1.0"' in result

    def test_noop_without_frontmatter(self):
        text = "# No frontmatter\nJust content."
        assert update_frontmatter_version(text, "0.1.0") == text


# --- unit tests: replace_setup_block ---


class TestReplaceSetupBlock:
    def test_replaces_block_with_skill_name(self):
        result = replace_setup_block(SKILL_MD_MIGRATED, "my-skill")
        assert "Old setup block content." not in result
        assert "scripts/skillctx-resolve.py resolve my-skill" in result
        assert "Rest of skill." in result

    def test_noop_without_markers(self):
        text = "# No markers here."
        assert replace_setup_block(text, "my-skill") == text

    def test_noop_with_missing_end_marker(self):
        text = "<!-- skillctx:begin -->\nSetup content but no end marker."
        assert replace_setup_block(text, "my-skill") == text


# --- unit tests: find_migrated_skills ---


class TestFindMigratedSkills:
    def test_finds_migrated_and_skips_plain(self, tmp_path):
        skills_dir = _make_skills_dir(
            tmp_path,
            {
                "test-skill": SKILL_MD_MIGRATED,
                "plain-skill": SKILL_MD_NOT_MIGRATED,
            },
        )
        results = find_migrated_skills(skills_dir, "0.2.0")
        assert len(results) == 1
        assert results[0]["skill"] == "test-skill"
        assert results[0]["status"] == "outdated"
        assert results[0]["version"] == "0.1.0"

    def test_marks_current_when_version_matches(self, tmp_path):
        skills_dir = _make_skills_dir(
            tmp_path,
            {
                "up-to-date-skill": SKILL_MD_CURRENT,
            },
        )
        results = find_migrated_skills(skills_dir, "0.2.0")
        assert len(results) == 1
        assert results[0]["status"] == "current"

    def test_returns_empty_when_no_migrated_skills(self, tmp_path):
        skills_dir = _make_skills_dir(
            tmp_path,
            {
                "plain-skill": SKILL_MD_NOT_MIGRATED,
            },
        )
        assert find_migrated_skills(skills_dir, "0.1.0") == []

    def test_returns_empty_for_empty_dir(self, tmp_path):
        skills_dir = tmp_path / "skills"
        skills_dir.mkdir()
        assert find_migrated_skills(skills_dir, "0.1.0") == []


# --- integration tests: CLI ---


def _run_cli(args: list[str]) -> tuple[int, str, str]:
    result = subprocess.run(
        [sys.executable, str(SYNC_SCRIPT), *args],
        capture_output=True,
        text=True,
    )
    return result.returncode, result.stdout.strip(), result.stderr.strip()


@pytest.mark.integration
class TestScanCLI:
    def test_outputs_json_with_migrated_skills(self, tmp_path):
        skills_dir = _make_skills_dir(tmp_path, {"test-skill": SKILL_MD_MIGRATED})
        code, stdout, _ = _run_cli(["scan", str(skills_dir), "0.2.0"])
        assert code == 0
        results = json.loads(stdout)
        assert len(results) == 1


@pytest.mark.integration
class TestUpdateCLI:
    def test_copies_resolver_and_updates_frontmatter(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(SKILL_MD_MIGRATED)

        resolver_src = tmp_path / "resolve.py"
        resolver_src.write_text("#!/usr/bin/env python3\n# new resolver\n")

        code, stdout, _ = _run_cli(["update", str(skill_dir), str(resolver_src), "0.2.0"])
        assert code == 0
        assert "updated" in stdout

        dest = skill_dir / "scripts" / "skillctx-resolve.py"
        assert dest.exists()
        assert "new resolver" in dest.read_text()

        text = (skill_dir / "SKILL.md").read_text()
        assert '"0.2.0"' in text
        assert "scripts/skillctx-resolve.py resolve test-skill" in text

    def test_exits_1_when_skill_md_missing(self, tmp_path):
        skill_dir = tmp_path / "missing-skill"
        skill_dir.mkdir()
        resolver_src = tmp_path / "resolve.py"
        resolver_src.write_text("# resolver\n")

        code, _, stderr = _run_cli(["update", str(skill_dir), str(resolver_src), "0.1.0"])
        assert code == 1
        assert "not found" in stderr

    def test_exits_1_when_resolver_missing(self, tmp_path):
        skill_dir = tmp_path / "test-skill"
        skill_dir.mkdir()
        (skill_dir / "SKILL.md").write_text(SKILL_MD_MIGRATED)

        code, _, stderr = _run_cli(["update", str(skill_dir), "/nonexistent/resolve.py", "0.1.0"])
        assert code == 1
        assert "not found" in stderr


@pytest.mark.integration
class TestCLIEdgeCases:
    def test_no_args_shows_usage(self):
        code, stdout, _ = _run_cli([])
        assert code == 1
        assert "usage" in stdout

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_help_flag_shows_usage(self, flag):
        code, stdout, _ = _run_cli([flag])
        assert code == 0
        assert "usage" in stdout

    def test_invalid_command_shows_error(self):
        code, _, stderr = _run_cli(["bogus"])
        assert code == 1
        assert "invalid" in stderr

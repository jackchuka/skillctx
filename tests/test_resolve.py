#!/usr/bin/env python3
"""Tests for skillctx-resolve.py (resolve and set subcommands)."""

import importlib.util
import json
import os
import subprocess
import sys
from copy import deepcopy
from pathlib import Path
from typing import Any

import pytest

RESOLVE_SCRIPT = Path(__file__).parent.parent / "skills" / "skillctx-ify" / "scripts" / "resolve.py"

_spec = importlib.util.spec_from_file_location("resolve", RESOLVE_SCRIPT)
assert _spec and _spec.loader
_resolve = importlib.util.module_from_spec(_spec)
_spec.loader.exec_module(_resolve)

walk_dotpath = _resolve.walk_dotpath
set_dotpath = _resolve.set_dotpath
load_config = _resolve.load_config
save_config = _resolve.save_config

SAMPLE_CONFIG: dict[str, Any] = {
    "vars": {
        "identity": {
            "github_username": "testuser",
            "github_orgs": ["org-a", "org-b"],
            "ego_keywords": ["test", "テスト"],
        },
        "slack": {
            "standup_channel_id": "C12345ABCDE",
            "standup_channel_name": "z-test-channel",
        },
        "paths": {
            "notebook": "~/Dropbox/sync/notebook",
        },
    },
    "skills": {
        "my-skill": {
            "channel_id": "vars.slack.standup_channel_id",
            "channel_name": "vars.slack.standup_channel_name",
        },
        "multi-binding": {
            "notebook": "vars.paths.notebook",
            "username": "vars.identity.github_username",
            "orgs": "vars.identity.github_orgs",
        },
        "empty-skill": {},
    },
}


# --- unit tests: walk_dotpath ---


class TestWalkDotpath:
    def test_resolves_scalar(self):
        assert walk_dotpath(SAMPLE_CONFIG, "vars.identity.github_username") == "testuser"

    def test_resolves_list(self):
        assert walk_dotpath(SAMPLE_CONFIG, "vars.identity.github_orgs") == ["org-a", "org-b"]

    def test_returns_none_for_missing_key(self):
        assert walk_dotpath(SAMPLE_CONFIG, "vars.nonexistent.field") is None

    def test_returns_none_for_partial_path(self):
        assert walk_dotpath(SAMPLE_CONFIG, "vars.identity") is not None
        assert walk_dotpath(SAMPLE_CONFIG, "vars.identity.github_username.nested") is None

    @pytest.mark.parametrize(
        "dotpath",
        ["", "nonexistent", "vars.slack.standup_channel_id.too.deep"],
    )
    def test_returns_none_for_invalid_paths(self, dotpath):
        assert walk_dotpath(SAMPLE_CONFIG, dotpath) is None


# --- unit tests: set_dotpath ---


class TestSetDotpath:
    def test_sets_scalar_value(self):
        config = deepcopy(SAMPLE_CONFIG)
        assert set_dotpath(config, "vars.slack.standup_channel_id", "NEW_ID")
        assert config["vars"]["slack"]["standup_channel_id"] == "NEW_ID"

    def test_sets_list_value(self):
        config = deepcopy(SAMPLE_CONFIG)
        assert set_dotpath(config, "vars.identity.github_orgs", ["x", "y"])
        assert config["vars"]["identity"]["github_orgs"] == ["x", "y"]

    def test_preserves_other_keys(self):
        config = deepcopy(SAMPLE_CONFIG)
        set_dotpath(config, "vars.slack.standup_channel_id", "CHANGED")
        assert config["vars"]["slack"]["standup_channel_name"] == "z-test-channel"
        assert config["vars"]["identity"]["github_username"] == "testuser"

    def test_returns_false_for_missing_path(self):
        config = deepcopy(SAMPLE_CONFIG)
        assert not set_dotpath(config, "vars.nonexistent.field", "value")

    def test_returns_false_for_non_dict_target(self):
        config = deepcopy(SAMPLE_CONFIG)
        assert not set_dotpath(config, "vars.identity.github_username.nested", "value")


# --- unit tests: load_config / save_config ---


class TestConfigIO:
    def test_load_returns_none_when_missing(self, tmp_path):
        assert load_config(tmp_path / "nonexistent.json") is None

    def test_save_and_load_roundtrip(self, tmp_path):
        path = tmp_path / "skillctx" / "config.json"
        save_config(path, SAMPLE_CONFIG)
        loaded = load_config(path)
        assert loaded == SAMPLE_CONFIG

    def test_save_creates_parent_dirs(self, tmp_path):
        path = tmp_path / "deep" / "nested" / "config.json"
        save_config(path, {"vars": {}})
        assert path.exists()


# --- integration tests: CLI ---


def _run_cli(
    args: list[str], config: dict[str, Any] | None = None, config_dir: str | None = None
) -> tuple[int, str, str]:
    """Run resolve.py via subprocess with an isolated config."""
    import tempfile

    if config_dir is not None:
        # Use the caller-provided directory directly
        config_path = Path(config_dir) / "skillctx" / "config.json"
        if config is not None:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(config, ensure_ascii=False))

        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = config_dir

        result = subprocess.run(
            [sys.executable, str(RESOLVE_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()

    with tempfile.TemporaryDirectory() as tmpdir:
        config_path = Path(tmpdir) / "skillctx" / "config.json"
        if config is not None:
            config_path.parent.mkdir(parents=True, exist_ok=True)
            config_path.write_text(json.dumps(config, ensure_ascii=False))

        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = tmpdir

        result = subprocess.run(
            [sys.executable, str(RESOLVE_SCRIPT), *args],
            capture_output=True,
            text=True,
            env=env,
        )
        return result.returncode, result.stdout.strip(), result.stderr.strip()


@pytest.mark.integration
class TestResolveCLI:
    def test_resolves_simple_bindings(self):
        code, stdout, _ = _run_cli(["resolve", "my-skill"], SAMPLE_CONFIG)
        assert code == 0
        assert "channel_id: C12345ABCDE" in stdout
        assert "channel_name: z-test-channel" in stdout

    def test_resolves_multiple_bindings(self):
        code, stdout, _ = _run_cli(["resolve", "multi-binding"], SAMPLE_CONFIG)
        assert code == 0
        assert "notebook: ~/Dropbox/sync/notebook" in stdout
        assert "username: testuser" in stdout
        assert "org-a" in stdout

    def test_empty_bindings_produces_no_output(self):
        code, stdout, _ = _run_cli(["resolve", "empty-skill"], SAMPLE_CONFIG)
        assert code == 0
        assert stdout == ""

    def test_missing_config_exits_1(self):
        import tempfile

        with tempfile.TemporaryDirectory() as tmpdir:
            env = os.environ.copy()
            env["XDG_CONFIG_HOME"] = tmpdir
            result = subprocess.run(
                [sys.executable, str(RESOLVE_SCRIPT), "resolve", "any-skill"],
                capture_output=True,
                text=True,
                env=env,
            )
            assert result.returncode == 1
            assert "config not found" in result.stderr

    def test_unmigrated_skill_exits_2(self):
        code, _, stderr = _run_cli(["resolve", "unknown-skill"], SAMPLE_CONFIG)
        assert code == 2
        assert "not in config" in stderr

    def test_broken_dotpath_warns_but_resolves_valid_keys(self):
        config: dict[str, Any] = {
            "vars": {"identity": {"github_username": "testuser"}},
            "skills": {
                "broken-skill": {
                    "username": "vars.identity.github_username",
                    "missing": "vars.nonexistent.field",
                }
            },
        }
        code, stdout, stderr = _run_cli(["resolve", "broken-skill"], config)
        assert code == 0
        assert "username: testuser" in stdout
        assert "broken reference" in stderr

    def test_no_args_shows_usage(self):
        result = subprocess.run(
            [sys.executable, str(RESOLVE_SCRIPT)],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 1
        assert "usage" in result.stdout

    @pytest.mark.parametrize("flag", ["-h", "--help"])
    def test_help_flag_shows_usage(self, flag):
        result = subprocess.run(
            [sys.executable, str(RESOLVE_SCRIPT), flag],
            capture_output=True,
            text=True,
        )
        assert result.returncode == 0
        assert "usage" in result.stdout


@pytest.mark.integration
class TestSetCLI:
    def test_sets_and_resolves_scalar(self, tmp_path):
        config_path = tmp_path / "skillctx" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps(SAMPLE_CONFIG, ensure_ascii=False))

        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = str(tmp_path)

        result = subprocess.run(
            [sys.executable, str(RESOLVE_SCRIPT), "set", "my-skill", "channel_id", "C_NEW_ID"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0
        assert "updated" in result.stdout

        result = subprocess.run(
            [sys.executable, str(RESOLVE_SCRIPT), "resolve", "my-skill"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert "channel_id: C_NEW_ID" in result.stdout

    def test_sets_list_value(self, tmp_path):
        config_path = tmp_path / "skillctx" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps(SAMPLE_CONFIG, ensure_ascii=False))

        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = str(tmp_path)

        result = subprocess.run(
            [
                sys.executable,
                str(RESOLVE_SCRIPT),
                "set",
                "multi-binding",
                "orgs",
                '["new-org-a", "new-org-b"]',
            ],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 0

        result = subprocess.run(
            [sys.executable, str(RESOLVE_SCRIPT), "resolve", "multi-binding"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert "new-org-a" in result.stdout

    def test_missing_config_exits_1(self, tmp_path):
        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = str(tmp_path)
        result = subprocess.run(
            [sys.executable, str(RESOLVE_SCRIPT), "set", "my-skill", "channel_id", "X"],
            capture_output=True,
            text=True,
            env=env,
        )
        assert result.returncode == 1
        assert "config not found" in result.stderr

    def test_unmigrated_skill_exits_2(self):
        code, _, stderr = _run_cli(["set", "unknown-skill", "key", "val"], SAMPLE_CONFIG)
        assert code == 2
        assert "not in config" in stderr

    def test_invalid_key_exits_3(self):
        code, _, stderr = _run_cli(["set", "my-skill", "nonexistent_key", "val"], SAMPLE_CONFIG)
        assert code == 3
        assert "is not a binding" in stderr

    def test_preserves_unrelated_data(self, tmp_path):
        config_path = tmp_path / "skillctx" / "config.json"
        config_path.parent.mkdir(parents=True)
        config_path.write_text(json.dumps(SAMPLE_CONFIG, ensure_ascii=False))

        env = os.environ.copy()
        env["XDG_CONFIG_HOME"] = str(tmp_path)

        subprocess.run(
            [sys.executable, str(RESOLVE_SCRIPT), "set", "my-skill", "channel_id", "CHANGED"],
            capture_output=True,
            text=True,
            env=env,
        )

        updated = json.loads(config_path.read_text())
        assert updated["vars"]["slack"]["standup_channel_id"] == "CHANGED"
        assert updated["vars"]["slack"]["standup_channel_name"] == "z-test-channel"
        assert updated["vars"]["identity"]["github_username"] == "testuser"
        assert updated["skills"]["multi-binding"]["notebook"] == "vars.paths.notebook"

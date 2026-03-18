# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Commands

```bash
uv sync --dev              # Install dependencies
uv run pytest              # Run all tests
uv run pytest tests/test_resolve.py -k test_name  # Run a single test
uv run ruff check .        # Lint
uv run ruff format .       # Format
uv run mypy .              # Type check
uv run python scripts/sync-version.py  # Sync version from pyproject.toml to SKILL.md + marketplace.json
```

## Architecture

This skill should work with **any agent host** that can run Python scripts and supports the agentskills.io skill format.

skillctx makes agent skills portable by extracting hardcoded values (usernames, paths, channel IDs) into a central config file (`~/.config/skillctx/config.json`) and embedding a resolver script into each skill.

**Config structure**: `vars` holds shared values organized by category (identity, slack, paths, blog). `skills` maps each skill name to bindings — key-to-dotpath mappings that reference values in `vars`.

**Two skills in `skills/`**:

- **skillctx-ify** — Migrates a skill: scans for hardcoded values (Phase 1, deterministic), classifies candidates with LLM judgment (Phase 2), then rewrites files and embeds the resolver (Phase 3).
- **skillctx-sync** — Bulk-updates the embedded resolver script across all previously migrated skills when `resolve.py` changes.

## Conventions

- `resolve.py` must stay zero-dependency (Python 3.10+ stdlib only) — it gets embedded into other repos
- Ruff config: line-length 100, target py310, rules E/F/I/UP/B/SIM/RUF
- mypy strict mode enabled; tests exempt from `disallow_untyped_defs`

---
name: skillctx-sync
description: >
  Update embedded skillctx resolver scripts across all migrated skills.
  Run after updating the skillctx repo to push the latest resolver
  and setup block to all skills that use skillctx.
license: MIT
compatibility: >
  Requires Python 3.10+. Works with Claude Code and any agentskills.io-compatible host.
metadata:
  author: jackchuka
  version: 0.1.0
  scope: generic
  confirms:
    - modify target skill scripts
    - modify target skill SKILL.md
---

# skillctx-sync

Update embedded `skillctx-resolve.py` scripts across all migrated skills.

## When to Use

- After updating the skillctx repo (bug fix in resolve.py, new features)
- User says "skillctx-sync", "update skillctx", or "sync skillctx"

## Prerequisites

- Python 3.10+
- Skills must be installed and discoverable by the agent host

## Workflow

1. **Read current version**: Run `python <skill-dir>/scripts/sync.py` with `--help` to verify the script is available. Read `pyproject.toml` in the skillctx repo root for the current version string.

2. **Scan for migrated skills**: Run `python <skill-dir>/scripts/sync.py scan <skills-dir> <current-version>` where `<skills-dir>` is the directory containing installed skills. The script outputs JSON:

   ```json
   [
     { "skill": "my-skill", "path": "/path/to/my-skill", "version": "0.1.0", "status": "outdated" },
     { "skill": "other-skill", "path": "/path/to/other-skill", "version": "0.2.0", "status": "current" }
   ]
   ```

   Only skills with `<!-- skillctx:begin -->` in their SKILL.md are included.

3. **Present outdated skills to user**: Filter the scan results to `"status": "outdated"` and show:

   ```
   Skills with outdated skillctx resolver:
   - my-skill (v0.1.0 → v0.2.0)
   - another-skill (v0.1.0 → v0.2.0)

   Update all? (yes/select/cancel)
   ```

   Wait for user confirmation.

4. **Update each selected skill**: For each skill the user approves, run:

   ```
   python <skill-dir>/scripts/sync.py update <skill-dir> <resolver-src> <current-version>
   ```

   Where `<resolver-src>` is `skills/skillctx-ify/scripts/resolve.py` (the canonical resolver in this repo). The script:
   - Copies the resolver to `<skill-dir>/scripts/skillctx-resolve.py`
   - Replaces the `<!-- skillctx:begin -->` ... `<!-- skillctx:end -->` block with the latest setup template
   - Updates `metadata.skillctx.version` in the skill's frontmatter

5. **Report** what was updated and any errors.

## Error Handling

| Error | Action |
|-------|--------|
| No migrated skills found | Report "no skills using skillctx found" |
| All skills already current | Report "all skills up to date" |
| Skill directory not writable | Warn and skip, list at the end |
| Missing `<!-- skillctx:end -->` marker | Warn — setup block may be malformed. Skip and list for manual review. |

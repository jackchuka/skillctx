---
name: skillctx-ify
description: >
  Migrate a skill to use skillctx. Identifies hardcoded values,
  extracts them as skill variables to ~/.config/skillctx/config.json,
  embeds a resolver script, and rewrites the skill.
  Invoke with the target skill name as argument.
license: MIT
compatibility: >
  Requires Python 3.10+. Works with Claude Code and any agentskills.io-compatible host.
argument-hint: "<skill-name>"
metadata:
  author: jackchuka
  version: 0.1.0
  scope: generic
  confirms:
    - modify config file
    - modify target skill files
    - add scripts/skillctx-resolve.py to target skill
---

# skillctx-ify

Migrate a skill to use skillctx for skill variable resolution.

## When to Use

- Making a skill portable (removing hardcoded values)
- Setting up a new skill to use skillctx
- User says "skillctx-ify" or "migrate skill to skillctx"

## Prerequisites

- Python 3.10+ (for the resolver script)
- Target skill must be installed and discoverable by the agent host

## Workflow

### Phase 1: Scan and classify

1. **Locate the target skill**: Find the skill directory by name. Follow symlinks to the actual directory.

2. **Check for prior migration**: Check for `<!-- skillctx:begin -->` marker in the skill's SKILL.md. If found, check `metadata.skillctx.version` in frontmatter.
   - If version matches current: report already migrated, stop.
   - If version is older: suggest running `skillctx-sync` to update.

3. **Read the skill files**: Read SKILL.md and all referenced files in the skill directory. Also read `references/known-patterns.md` for classification guidance.

4. **Identify candidates**: Scan the content for hardcoded values that are user-specific or environment-specific — usernames, Slack channel IDs, filesystem paths, org names, etc. For each candidate, determine:
   - Is this actually a skill variable or a generic/example string? Use context (tool calls vs prose), repetition, and specificity to decide.
   - What category does it belong to in `vars`? Use existing config categories as a guide. Defaults: `identity`, `slack`, `paths`, `blog`.
   - What should the binding key be named? See [Binding Key Naming](#binding-key-naming) below.

5. **Read existing config**: Read `${XDG_CONFIG_HOME:-~/.config}/skillctx/config.json` if it exists. If not, note it needs to be created. Reuse existing vars when the value already exists in the config — don't create duplicates.

### Phase 2: Confirm and rewrite

6. **Present proposed changes to user** in a table like this:

   | Hardcoded value | File:line   | Binding key       | Var dotpath                     | New?        |
   | --------------- | ----------- | ----------------- | ------------------------------- | ----------- |
   | `CABC123DEF`    | SKILL.md:42 | `channel_id`      | `vars.slack.channel_id`         | yes         |
   | `alice`         | SKILL.md:10 | `github_username` | `vars.identity.github_username` | no (exists) |

   Wait for user confirmation before proceeding.

7. **Rewrite skill files**:

   **a) Replace hardcoded values** with `{binding_key}` placeholders. The placeholder is a literal string in the skill file — it gets resolved at runtime by the resolver script.

   Before: `Post to #eng-standup (CABC123DEF)`
   After:  `Post to {channel_name} ({channel_id})`

   **b) Inject the setup block** near the top of SKILL.md (after the frontmatter and title), wrapped in comment markers:

   ```markdown
   <!-- skillctx:begin -->
   ## Setup
   Locate this skill's directory (the folder containing this SKILL.md), then run the
   resolver script from there:

   python <skill-dir>/scripts/skillctx-resolve.py resolve <skill-name>

   The resolver outputs each binding as `key: value` (one per line). For list values, it outputs JSON (e.g., `orgs: ["org-a", "org-b"]`). Substitute each `{binding_key}` placeholder below with the resolved value.

   If any values are missing or the user requests changes, use:
   python <skill-dir>/scripts/skillctx-resolve.py set <skill-name> <key> <value>
   <!-- skillctx:end -->
   ```

   **c) Update the skill's description** to remove migrated values and replace them with placeholders.

   **d) Add `metadata.skillctx.version: "0.1.0"`** to the skill's frontmatter.

### Phase 3: Write-back

8. **Copy resolver script**: Copy `scripts/resolve.py` (from this skill's directory) into the target skill's `scripts/` directory as `skillctx-resolve.py`. Create `scripts/` if it doesn't exist. Make it executable.

9. **Update config file**: Write the updated config with new vars and bindings. Create the directory (`mkdir -p`) if needed.

10. **Report**: Show what was extracted, bindings created, and files changed.

## Binding Key Naming

Binding keys are the names used as `{placeholders}` in the skill and as keys in `skills.<name>` in the config. They should be:

- **Descriptive of the role**, not the value. Use `channel_id` not `standup_channel_id` — the skill doesn't care which channel, just that it has one.
- **Scoped to the skill's perspective.** If a skill posts to one channel, `channel_id` is fine. If it uses two channels for different purposes, disambiguate: `post_channel_id`, `alert_channel_id`.
- **snake_case**, lowercase, no prefixes like `var_` or `ctx_`.
- **Stable.** Once a skill is migrated, renaming keys breaks existing configs. Choose names that won't need to change if the underlying value changes.

Examples:

| Hardcoded value           | Good binding key  | Bad binding key    | Why              |
| ------------------------- | ----------------- | ------------------ | ---------------- |
| `CABC123DEF`              | `channel_id`      | `slack_standup_id` | role > source    |
| `alice`                   | `github_username` | `user`             | too vague        |
| `~/Sync/notes`            | `notebook_path`   | `dropbox_path`     | tied to provider |
| `["acme", "widgets-inc"]` | `github_orgs`     | `orgs_list`        | redundant suffix |

## Error Handling

| Error                                    | Action                                                                        |
| ---------------------------------------- | ----------------------------------------------------------------------------- |
| Skill directory not found                | Report error, suggest checking the skill name                                 |
| Skill already migrated (current version) | Report and stop                                                               |
| Skill already migrated (older version)   | Suggest running `skillctx-sync`                                               |
| No candidates found                      | Report that skill has no hardcoded values. Add empty binding entry to config. |
| Config file malformed                    | Report the JSON parse error, suggest manual fix                               |

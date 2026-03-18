# Known Patterns for Skill Variable Detection

These patterns describe what to look for when reading a skill's files for hardcoded values. Use these descriptions alongside context, repetition, and specificity to classify candidates.

## Pattern Types

### Slack

#### slack_channel_id

- Looks like: `CABC123DEF` — uppercase C followed by 8+ alphanumeric characters
- **Is a skill variable when**: used in `slack_send_message`, `slack_read_channel`, or similar MCP tool calls
- **NOT a skill variable when**: used in a regex pattern description or documentation about Slack ID format

#### slack_channel_name

- Looks like: `#eng-team`, `#daily-standup` — `#` followed by lowercase with hyphens/underscores
- **Is a skill variable when**: used as a destination for posting or reading messages
- **NOT a skill variable when**: used as an example format or in documentation

#### slack_user_id

- Looks like: `UABC456DEF` — uppercase U followed by alphanumeric characters
- **Is a skill variable when**: used in mentions, DMs, or user lookups
- **NOT a skill variable when**: used as an example format

### GitHub

#### github_org_owner

- Looks like: `--owner acme-corp`, `org:acme-corp`
- **Is a skill variable when**: used in `gh search`, GraphQL queries, or API calls to filter by org
- **NOT a skill variable when**: used as a placeholder or example

#### github_username

- Looks like: `--author alice`, `from:alice`, or bare in URLs like `github.com/alice`
- **Is a skill variable when**: used to filter activity, identify the user, or in repo URLs
- **NOT a skill variable when**: used as a generic example (e.g., `octocat`)

#### github_repo

- Looks like: `owner/repo-name` in clone URLs, API calls, or `gh` commands
- **Is a skill variable when**: references a specific repo the skill operates on
- **NOT a skill variable when**: used as a format example or refers to the skill's own repo

### Paths

#### home_path

- Looks like: `~/Documents/notes`, `~/projects/my-app`
- **Is a skill variable when**: used as an output directory, input path, or save location
- **NOT a skill variable when**: used as a generic example path in documentation

#### claude_project_path

- Looks like: `.claude/projects/-Users-alice-some-project`
- **Always a skill variable**: contains machine-specific path segments

#### absolute_path

- Looks like: `/Users/alice/...`, `/home/alice/...`
- **Always a skill variable**: contains machine-specific path segments

### Identity

#### email_address

- Looks like: `alice@acme.io`, `bob@company.com`
- **Is a skill variable when**: used in tool calls, git config, or API requests
- **NOT a skill variable when**: uses a clearly generic domain (`example.com`, `test.com`)

#### personal_name

- Looks like: a person's name used in templates, signatures, or greetings
- **Is a skill variable when**: represents the skill user's identity
- **NOT a skill variable when**: used in example output or documentation

### Services

#### api_base_url

- Looks like: `https://api.mycompany.com`, `https://internal.service.dev`
- **Is a skill variable when**: used as a base URL for API calls or webhooks
- **NOT a skill variable when**: a well-known public API (e.g., `https://api.github.com`)

#### api_key_or_token

- Looks like: long alphanumeric strings, `sk-...`, `xoxb-...`, bearer tokens
- **Always a skill variable**: secrets should never be hardcoded. Extract and note that the value should be stored securely.

#### custom_domain

- Looks like: `myapp.vercel.app`, `blog.alice.dev`
- **Is a skill variable when**: references a user-specific domain
- **NOT a skill variable when**: references a well-known service domain

#### datadog_monitor_id

- Looks like: numeric IDs in Datadog API calls or dashboard URLs
- **Is a skill variable when**: references a specific monitor, dashboard, or service
- **NOT a skill variable when**: used as an example format

### Project

#### team_or_project_name

- Looks like: appears in URLs, tool calls, or project references (e.g., Linear project, Jira board)
- **Is a skill variable when**: identifies a specific team or project the skill operates on
- **NOT a skill variable when**: a generic term like "default" or "main"

#### database_or_resource_name

- Looks like: specific names for databases, BigQuery datasets, S3 buckets, etc.
- **Is a skill variable when**: references a specific resource the skill reads/writes
- **NOT a skill variable when**: used as an example or placeholder

## Classification Hints

When reading skill files, consider:

1. **Context**: Is the value used in a tool call, a command, or prose? Values in tool calls and commands are almost always skill variables.
2. **Repetition**: Does the same value appear in multiple places? Likely a skill variable.
3. **Specificity**: Generic terms (e.g., "main", "default") are rarely skill variables. Specific identifiers (e.g., `CABC123DEF`) almost always are.
4. **When in doubt, extract it.** It's better to propose a candidate the user rejects than to miss a hardcoded value. The user will review all proposals before any changes are made.

## Category Assignment

Use existing categories in the config as a guide. Defaults:

| Category   | Contains                                      |
| ---------- | --------------------------------------------- |
| `identity` | Usernames, email, personal names, org names   |
| `slack`    | Channel IDs, channel names, user IDs          |
| `paths`    | Filesystem paths, project paths               |
| `blog`     | Platform names, domains, preferences          |
| `services` | API URLs, tokens, monitor IDs, resource names |
| `project`  | Team names, repo references, database names   |

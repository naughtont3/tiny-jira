# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A minimal Python CLI for interacting with Jira Cloud and Jira Server using API tokens. Single-file application (`tiny-jira-cli.py`) using the `jira` (pycontribs/jira) library for API communication. Intentionally kept small and extensible.

## Dependencies

```bash
pip install -r requirements.txt
```

Dependencies: `jira` (pycontribs/jira), `pyyaml`, `rich`

## Configuration

The CLI requires endpoint and token. For Jira Cloud (default), `user` (email) is also required. For Jira Server with a PAT, set `auth: pat` and `user` is not needed. An optional `project` field sets the default project.

**Config search order:**
1. `.config.yml` in the working directory
2. `~/.tiny_jira/config.yml`
3. Environment variables (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, `JIRA_DEFAULT_PROJECT`, `JIRA_AUTH_METHOD`)

**Two config formats are supported:**

Legacy flat format:
```yaml
endpoint: "https://your-domain.atlassian.net"
user: "you@example.com"
token: "your_api_token"    # supports file: prefix, e.g. "file:/path/to/token"
project: "INFRA"           # optional default project
auth: "pat"                # optional; use "pat" for Jira Server PAT (Bearer token)
```

Multi-project format (named profiles under `projects:` key):
```yaml
projects:
  cloud-project:
    endpoint: "https://domain1.atlassian.net"
    user: "user@example.com"
    token: "file:/path/to/token"
    project: "INFRA"
  server-project:
    endpoint: "https://jira.example.org"
    token: "file:/path/to/pat"
    project: "DS"
    auth: pat               # uses Bearer token, no user needed
default: cloud-project      # optional; falls back to first entry
```

Select a profile at runtime with `-p PROFILE_NAME`. Debug config with `--dump`.

## Running the CLI

```bash
python tiny-jira-cli.py issue ABC-123                     # View single issue
python tiny-jira-cli.py issue ABC-123 --show-comments     # Include comments
python tiny-jira-cli.py issue                             # List your issues
python tiny-jira-cli.py issue -p INFRA -n 5               # Filter by project, limit results
python tiny-jira-cli.py issue --filter "status:Done"      # Filter results locally
python tiny-jira-cli.py issue -c key,summary,status       # Select columns
python tiny-jira-cli.py search "status = 'In Progress'"   # JQL search
python tiny-jira-cli.py comments ABC-123                  # View comments
python tiny-jira-cli.py --ascii issue                     # Disable color for piping
```

A `tiny-jira` wrapper script activates the venv and forwards arguments to `tiny-jira-cli.py`.

## Testing

```bash
python tests/test_jira_libs.py
```

Validates library compatibility with the Jira Cloud instance. Only `jira` (pycontribs/jira) is currently compatible.

## Architecture

Single-file CLI (`tiny-jira-cli.py`, ~1000 lines) with these layers:

- **Configuration** (`get_config()`, `_load_config_file()`, `_resolve_token()`): Detects config format (legacy vs multi-project), resolves `file:` token prefixes, falls back through search order. Case-insensitive profile lookup for multi-project mode. Supports two auth modes: `basic_auth` (default, for Cloud) and `token_auth` (when `auth: pat`, for Server PATs).
- **Command handlers** (`cmd_issue()`, `cmd_search()`, `cmd_comments()`): Each subcommand is a dedicated function dispatched from `main()` via argparse subparsers.
- **Display** (`print_issue()`, `render_comments()`, `print_block()`): Uses Rich library for tables, panels, and color. `--ascii` mode disables styling for piped output.
- **Column registry** (`get_column_registry()`): Centralized metadata for table columns (key, summary, status, labels, assignee, created, updated). Each entry defines a label, style, width constraints, and a lambda for field extraction. `calculate_column_widths()` dynamically allocates terminal width.
- **Filtering** (`parse_filters()`, `filter_issues()`): Local post-query filtering with `--filter "field:value,field:value"` syntax. Case-insensitive substring matching.

Key patterns:
- `print_issue()` handles both JIRA Issue objects and raw dicts for backward compatibility (`hasattr(issue, 'key')` checks)
- The `jira` library provides object-oriented field access: `issue.fields.summary`, `issue.fields.assignee.displayName`
- `.config.yml` starts with a dot to avoid accidental commits (in `.gitignore`)

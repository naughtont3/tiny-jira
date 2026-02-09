# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A minimal Python CLI for interacting with Jira Cloud using API tokens. The project uses the `jira` (pycontribs/jira) library for API communication and is intentionally kept small and extensible.

## Dependencies

Install dependencies:
```bash
pip install -r requirements.txt
```

Dependencies: `jira`, `pyyaml`

## Configuration

The CLI requires three configuration values, which can be provided via `.config.yml` (note the leading dot) or environment variables:

**Preferred: .config.yml format:**
```yaml
endpoint: "https://your-domain.atlassian.net"
user: "you@example.com"
token: "your_api_token"
```

The `token` field supports a `file:` prefix to read the token from a file:
```yaml
token: "file:/path/to/token/file"
```

**Fallback: Environment variables:**
```bash
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="your_api_token"
```

Configuration loading order:
1. Read from `.config.yml` if present (note: file starts with a dot)
2. Fall back to environment variables
3. Exit with error if any required values are missing

**Configuration debugging:**
```bash
python tiny-jira-cli.py --dump  # Show current configuration
```

## Running the CLI

The CLI has three main commands:

**View a single issue:**
```bash
python tiny-jira-cli.py issue ABC-123
python tiny-jira-cli.py issue ABC-123 --no-description
```

**List issues:**
```bash
python tiny-jira-cli.py issue                    # List your issues
python tiny-jira-cli.py issue -p INFRA           # List issues from INFRA project
python tiny-jira-cli.py issue -p INFRA -n 5      # Limit to 5 results
python tiny-jira-cli.py issue --describe         # Include descriptions
```

**Search issues with JQL:**
```bash
python tiny-jira-cli.py search "project = ABC AND assignee = currentUser()"
python tiny-jira-cli.py search "status = 'In Progress'" -n 50
python tiny-jira-cli.py search "project = ABC" --describe --width 120
```

**View comments on an issue:**
```bash
python tiny-jira-cli.py comments ABC-123
python tiny-jira-cli.py comments ABC-123 --width 120
```

## Architecture

This is a single-file CLI application (tiny-jira-cli.py) with a simple structure:

- **Configuration Management**: `get_config()` loads credentials and an optional default project from .config.yml or environment variables, with support for `file:` prefix for token files. Returns a JIRA client instance from the `jira` library.
- **Display Utilities**: `wrap()` and `print_issue()` handle text formatting and issue display. These work with both JIRA Issue objects and dict responses for backward compatibility.
- **Command Handlers**: Each subcommand has a dedicated `cmd_*()` function:
  - `cmd_issue()` - Shows single issue OR lists issues (with optional project filter)
  - `cmd_search()` - Searches using JQL queries
  - `cmd_comments()` - Displays comments on an issue
- **API Communication**: Uses the `jira` (pycontribs/jira) library which provides a high-level interface to Jira Cloud REST API v3. The library handles authentication, request formatting, and response parsing.

Key implementation details:
- The `jira` library wraps API v3 endpoints and provides object-oriented access to issue fields (e.g., `issue.fields.summary`, `issue.fields.assignee.displayName`)
- `print_issue()` includes compatibility code to handle both JIRA Issue objects and raw dict responses
- Configuration file is `.config.yml` (starts with a dot) to avoid accidental commits
- Token can be loaded from a separate file using `file:/path/to/token` syntax

## Testing

There is a test script that validates library compatibility:
```bash
python tests/test_jira_libs.py
```

This script tests both `jira` (pycontribs/jira) and `atlassian-python-api` libraries. As of the latest tests, only `jira` (pycontribs/jira) is fully compatible with the current Jira Cloud instance.

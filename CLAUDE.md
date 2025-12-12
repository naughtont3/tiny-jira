# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

A minimal Python CLI for interacting with Jira Cloud using API tokens. The project is intentionally kept small and extensible.

## Dependencies

Install dependencies:
```bash
pip install -r requirements.txt
```

Dependencies: `requests`, `pyyaml`

## Configuration

The CLI requires three configuration values, which can be provided via `config.yml` or environment variables:

**config.yml format:**
```yaml
endpoint: "https://your-domain.atlassian.net"
user: "you@example.com"
token: "your_api_token"
```

The `token` field supports a `file:` prefix to read the token from a file:
```yaml
token: "file:/path/to/token/file"
```

**Environment variables (fallback):**
```bash
export JIRA_BASE_URL="https://your-domain.atlassian.net"
export JIRA_EMAIL="you@example.com"
export JIRA_API_TOKEN="your_api_token"
```

Configuration loading order:
1. Read from `config.yml` if present
2. Fall back to environment variables
3. Exit with error if any required values are missing

## Running the CLI

The CLI has three main commands:

**View a single issue:**
```bash
python tiny-jira-cli.py issue ABC-123
python tiny-jira-cli.py issue ABC-123 --no-description
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

- **Configuration Management**: `get_config()` loads credentials from config.yml or environment variables, with support for token files
- **Display Utilities**: `wrap()` and `print_issue()` handle text formatting and issue display
- **Command Handlers**: Each subcommand (`issue`, `search`, `comments`) has a dedicated `cmd_*()` function
- **API Communication**: Uses `requests` library with basic auth (email + API token) to call Jira Cloud REST API v3 endpoints

Key API endpoints used:
- `/rest/api/3/issue/{issueKey}` - Get single issue
- `/rest/api/3/search` - Search issues with JQL
- `/rest/api/3/issue/{issueKey}/comment` - Get issue comments

The CLI uses argparse for command-line argument parsing with subparsers for each command.

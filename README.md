# tiny-jira

A "tiny" Jira CLI in Python.

The intent is to have something small and extensible,
that works with current API Tokens.

Using the `jira` (pycontribs/jira) Python package with Rich for terminal output.

## Setup

```bash
pip install -r requirements.txt
```

Run directly or use the `tiny-jira` wrapper script (activates the venv automatically):
```bash
python tiny-jira-cli.py --help
tiny-jira --help
```

## Configuration

The CLI needs three values: Jira base URL, user email, and an API token.

**Config search order:**
1. `.config.yml` in the working directory
2. `~/.tiny_jira/config.yml`
3. Environment variables (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`)

### Single-project config

```yaml
endpoint: "https://your-domain.atlassian.net"
user: "you@example.com"
token: "file:/path/to/token"  # or the token string directly
project: "INFRA"              # optional default project
```

### Multi-project config

```yaml
projects:
  infra:
    endpoint: "https://domain1.atlassian.net"
    user: "user@example.com"
    token: "file:/path/to/token"
    project: "INFRA"
  other:
    endpoint: "https://domain2.atlassian.net"
    user: "other@example.com"
    token: "token-string"
    project: "OTHER"
default: infra    # optional; falls back to first entry
```

Select a profile at runtime with `-p PROFILE_NAME`.

- The `token` key accepts a `file:/path/to/token` prefix to read the token from a file.
- Environment variable fallback: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`, and optional `JIRA_DEFAULT_PROJECT`.
- Debug what the CLI sees with `--dump`.
- See `misc/_config.yml` for a full example.

## Usage

**View a single issue:**
```bash
tiny-jira issue ABC-123
tiny-jira issue ABC-123 --no-description
tiny-jira issue ABC-123 --show-comments
```

**List issues:**
```bash
tiny-jira issue                              # List your assigned issues
tiny-jira issue -p INFRA                     # Filter by project (or select profile)
tiny-jira issue -n 5                         # Limit results
tiny-jira issue --describe                   # Include descriptions
tiny-jira issue --filter "status:Done"       # Local post-query filter
tiny-jira issue -c key,summary,status        # Select table columns
```

**Search with JQL:**
```bash
tiny-jira search "project = ABC AND assignee = currentUser()"
tiny-jira search "status = 'In Progress'" -n 50
tiny-jira search "project = ABC" --describe --width 120
```

**View comments:**
```bash
tiny-jira comments ABC-123
tiny-jira comments ABC-123 --width 120
```

**Other options:**
```bash
tiny-jira --dump                             # Show current configuration
tiny-jira --ascii issue                      # Disable color/styling for piping
tiny-jira --examples                         # Show usage examples
```

Available columns for `-c`: key, summary, status, labels, assignee, created, updated.

Filter syntax for `--filter`: `field:"value",field:"value"` with case-insensitive substring matching. Supported fields: key, summary, status, assignee, reporter, labels, issuetype, created, updated.

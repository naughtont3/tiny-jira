# tiny-jira

A "tiny" jira CLI in Python.

The intent is to have something small and extensible,
that works with current API Tokens.

Using the `jira` Python package.

## Setup

- Install deps: `pip install -r requirements.txt`
- Run the CLI: `python tiny-jira-cli.py issue ABC-123` (see `--help` for more commands)

## Configuration

The CLI needs three values: Jira base URL, user email, and an API token. Preferred configuration is a local `.config.yml` (note the leading dot):

```yaml
endpoint: "https://your-domain.atlassian.net"
user: "you@example.com"
token: "file:/path/to/token"  # or the token string directly
```

- The `token` key accepts `file:/path/to/token` to read from a file.
- Environment variable fallback: `JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`.
- Show what the CLI sees with `python tiny-jira-cli.py --dump`.

**Configuration search order:**
1. `.config.yml` in the working directory
2. `~/.tiny_jira/config.yml`
3. Environment variables (`JIRA_BASE_URL`, `JIRA_EMAIL`, `JIRA_API_TOKEN`)


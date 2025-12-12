#!/usr/bin/env python3
import os
import sys
import argparse
import textwrap
import requests
import yaml

def get_config():
    # Try to read from .config.yml first
    config_file = ".config.yml"
    base_url = None
    email = None
    api_token = None

    if os.path.exists(config_file):
        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        base_url = config.get("endpoint")
        email = config.get("user")
        token_value = config.get("token")

        # Handle file: prefix for token
        if token_value and token_value.startswith("file:"):
            token_path = token_value[5:]  # Remove "file:" prefix
            try:
                with open(token_path, "r") as tf:
                    api_token = tf.read().strip()
            except FileNotFoundError:
                print(f"Error: Token file not found: {token_path}", file=sys.stderr)
                sys.exit(1)
        else:
            api_token = token_value

    # Fall back to environment variables if not set from config
    if not base_url:
        base_url = os.environ.get("JIRA_BASE_URL")
    if not email:
        email = os.environ.get("JIRA_EMAIL")
    if not api_token:
        api_token = os.environ.get("JIRA_API_TOKEN")

    missing = [name for name, val in [
        ("JIRA_BASE_URL/endpoint", base_url),
        ("JIRA_EMAIL/user", email),
        ("JIRA_API_TOKEN/token", api_token),
    ] if not val]

    if missing:
        print(f"Error: missing configuration: {', '.join(missing)}", file=sys.stderr)
        print("Please provide them via .config.yml or environment variables:", file=sys.stderr)
        print('  .config.yml format:', file=sys.stderr)
        print('    endpoint: "https://your-domain.atlassian.net"', file=sys.stderr)
        print('    user: "you@example.com"', file=sys.stderr)
        print('    token: "your_api_token"', file=sys.stderr)
        print('  OR set environment variables:', file=sys.stderr)
        print('    export JIRA_BASE_URL="https://your-domain.atlassian.net"', file=sys.stderr)
        print('    export JIRA_EMAIL="you@example.com"', file=sys.stderr)
        print('    export JIRA_API_TOKEN="your_api_token"', file=sys.stderr)
        sys.exit(1)

    return base_url.rstrip("/"), email, api_token


def wrap(text, width=80, indent=""):
    if not text:
        return ""
    wrapper = textwrap.TextWrapper(width=width, subsequent_indent=indent)
    return wrapper.fill(text)


def print_issue(issue, show_description=True, width=100):
    key = issue.get("key")
    fields = issue.get("fields", {})
    summary = fields.get("summary", "")
    issue_type = fields.get("issuetype", {}).get("name", "")
    status = fields.get("status", {}).get("name", "")
    reporter = (fields.get("reporter") or {}).get("displayName", "")
    assignee = (fields.get("assignee") or {}).get("displayName", "")

    print(f"{key}  [{issue_type}]  (Status: {status})")
    print(f"Summary    : {summary}")
    print(f"Reporter   : {reporter}")
    print(f"Assignee   : {assignee}")
    print("-" * width)

    if show_description:
        desc = fields.get("description") or ""
        if isinstance(desc, dict):
            # Cloud sometimes uses "doc" format; this is a simple fallback.
            desc = desc.get("content") or ""
        print("Description:")
        if not desc:
            print("  (no description)")
        else:
            for line in str(desc).splitlines():
                print("  " + wrap(line, width=width - 2, indent="  "))

    print()


def cmd_issue(args):
    base_url, email, api_token = get_config()
    issue_key = args.key

    url = f"{base_url}/rest/api/3/issue/{issue_key}"
    resp = requests.get(url, auth=(email, api_token))

    if resp.status_code == 404:
        print(f"Issue {issue_key} not found.")
        sys.exit(1)
    if not resp.ok:
        print(f"Error fetching issue: HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    issue = resp.json()
    print_issue(issue, show_description=not args.no_description)


def cmd_search(args):
    base_url, email, api_token = get_config()
    jql = args.jql

    url = f"{base_url}/rest/api/3/search"
    params = {
        "jql": jql,
        "maxResults": args.max_results,
    }
    resp = requests.get(url, params=params, auth=(email, api_token))

    if not resp.ok:
        print(f"Error searching issues: HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    data = resp.json()
    issues = data.get("issues", [])

    if not issues:
        print("No issues found.")
        return

    for issue in issues:
        print_issue(issue, show_description=args.describe, width=args.width)


def cmd_comments(args):
    base_url, email, api_token = get_config()
    issue_key = args.key

    url = f"{base_url}/rest/api/3/issue/{issue_key}/comment"
    resp = requests.get(url, auth=(email, api_token))

    if resp.status_code == 404:
        print(f"Issue {issue_key} not found.")
        sys.exit(1)
    if not resp.ok:
        print(f"Error fetching comments: HTTP {resp.status_code}")
        print(resp.text)
        sys.exit(1)

    data = resp.json()
    comments = data.get("comments", [])

    if not comments:
        print(f"No comments on {issue_key}.")
        return

    print(f"Comments for {issue_key}:")
    print("-" * args.width)
    for c in comments:
        author = (c.get("author") or {}).get("displayName", "(unknown)")
        body = c.get("body") or ""
        print(f"Author: {author}")
        print("Body:")
        for line in str(body).splitlines():
            print("  " + wrap(line, width=args.width - 2, indent="  "))
        print("-" * args.width)


def main():
    parser = argparse.ArgumentParser(
        description="Minimal Jira CLI using Jira Cloud REST API"
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump configuration and exit",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    # jira_cli.py issue KEY
    p_issue = subparsers.add_parser("issue", help="Show a single issue")
    p_issue.add_argument("key", help="Issue key, e.g. ABC-123")
    p_issue.add_argument(
        "--no-description",
        action="store_true",
        help="Do not show issue description",
    )
    p_issue.set_defaults(func=cmd_issue)

    # jira_cli.py search "JQL"
    p_search = subparsers.add_parser("search", help="Search issues with JQL")
    p_search.add_argument("jql", help='JQL query, e.g. \'project = ABC AND assignee = currentUser()\'')
    p_search.add_argument(
        "-n", "--max-results",
        type=int,
        default=20,
        help="Max results to return (default: 20)",
    )
    p_search.add_argument(
        "--describe",
        action="store_true",
        help="Also print descriptions for each issue",
    )
    p_search.add_argument(
        "--width",
        type=int,
        default=100,
        help="Output width for wrapping text (default: 100)",
    )
    p_search.set_defaults(func=cmd_search)

    # jira_cli.py comments KEY
    p_comments = subparsers.add_parser("comments", help="Show comments for an issue")
    p_comments.add_argument("key", help="Issue key, e.g. ABC-123")
    p_comments.add_argument(
        "--width",
        type=int,
        default=100,
        help="Output width for wrapping text (default: 100)",
    )
    p_comments.set_defaults(func=cmd_comments)

    args = parser.parse_args()

    if args.dump:
        base_url, email, api_token = get_config()
        print(f"Endpoint: {base_url}")
        print(f"User: {email}")
        print(f"Token: {'*' * 8 if api_token else '(not set)'}")
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()


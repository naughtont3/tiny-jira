#!/usr/bin/env python3
import os
import sys
import argparse
import textwrap
import yaml
from jira import JIRA
from jira.exceptions import JIRAError


def get_config():
    """Load config and return a JIRA client instance."""
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

    # Return JIRA client instance
    try:
        jira = JIRA(server=base_url.rstrip("/"), basic_auth=(email, api_token))
        return jira, base_url, email, api_token
    except JIRAError as e:
        print(f"Error connecting to Jira: {e}", file=sys.stderr)
        sys.exit(1)


def wrap(text, width=80, indent=""):
    """Wrap text to specified width."""
    if not text:
        return ""
    wrapper = textwrap.TextWrapper(width=width, subsequent_indent=indent)
    return wrapper.fill(text)


def print_issue(issue, show_description=True, width=100):
    """Print issue details. Works with both JIRA Issue objects and dicts."""
    # Handle both JIRA Issue objects and dict responses
    if hasattr(issue, 'key'):
        # JIRA Issue object
        key = issue.key
        summary = issue.fields.summary
        issue_type = issue.fields.issuetype.name
        status = issue.fields.status.name
        reporter = issue.fields.reporter.displayName if issue.fields.reporter else ""
        assignee = issue.fields.assignee.displayName if issue.fields.assignee else ""
        description = issue.fields.description if show_description else None
    else:
        # Dict format (for backward compatibility)
        key = issue.get("key")
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        issue_type = fields.get("issuetype", {}).get("name", "")
        status = fields.get("status", {}).get("name", "")
        reporter = (fields.get("reporter") or {}).get("displayName", "")
        assignee = (fields.get("assignee") or {}).get("displayName", "")
        description = fields.get("description") if show_description else None

    print(f"{key}  [{issue_type}]  (Status: {status})")
    print(f"Summary    : {summary}")
    print(f"Reporter   : {reporter}")
    print(f"Assignee   : {assignee}")
    print("-" * width)

    if show_description and description:
        print("Description:")
        if isinstance(description, dict):
            # Cloud sometimes uses "doc" format; this is a simple fallback.
            description = description.get("content") or ""
        if not description:
            print("  (no description)")
        else:
            for line in str(description).splitlines():
                print("  " + wrap(line, width=width - 2, indent="  "))
    elif show_description:
        print("Description:")
        print("  (no description)")

    print()


def cmd_issue(args):
    """Display a single issue or list all issues."""
    jira, _, _, _ = get_config()

    # If no key provided, list all issues
    if not args.key:
        try:
            # Build JQL query based on project filter
            if args.project:
                jql = f"project = {args.project} ORDER BY updated DESC"
            else:
                # Default: issues assigned to or reported by current user
                jql = "assignee = currentUser() OR reporter = currentUser() ORDER BY updated DESC"

            issues = jira.search_issues(jql, maxResults=args.max_results)

            if not issues:
                print("No issues found.")
                return

            for issue in issues:
                print_issue(issue, show_description=args.describe, width=args.width)
        except JIRAError as e:
            print(f"Error fetching issues: {e}")
            sys.exit(1)
    else:
        # Show single issue
        try:
            issue = jira.issue(args.key)
            print_issue(issue, show_description=not args.no_description, width=args.width)
        except JIRAError as e:
            if e.status_code == 404:
                print(f"Issue {args.key} not found.")
            else:
                print(f"Error fetching issue: {e}")
            sys.exit(1)


def cmd_search(args):
    """Search for issues using JQL."""
    jira, _, _, _ = get_config()

    try:
        issues = jira.search_issues(args.jql, maxResults=args.max_results)

        if not issues:
            print("No issues found.")
            return

        for issue in issues:
            print_issue(issue, show_description=args.describe, width=args.width)
    except JIRAError as e:
        print(f"Error searching issues: {e}")
        sys.exit(1)


def cmd_comments(args):
    """Display comments for an issue."""
    jira, _, _, _ = get_config()

    try:
        issue = jira.issue(args.key)
        comments = jira.comments(issue)

        if not comments:
            print(f"No comments on {args.key}.")
            return

        print(f"Comments for {args.key}:")
        print("-" * args.width)
        for c in comments:
            author = c.author.displayName if hasattr(c.author, 'displayName') else str(c.author)
            body = c.body or ""
            print(f"Author: {author}")
            print("Body:")
            for line in str(body).splitlines():
                print("  " + wrap(line, width=args.width - 2, indent="  "))
            print("-" * args.width)
    except JIRAError as e:
        if e.status_code == 404:
            print(f"Issue {args.key} not found.")
        else:
            print(f"Error fetching comments: {e}")
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Minimal Jira CLI using Jira Cloud REST API",
        epilog="""
Examples:
  # Show configuration
  %(prog)s --dump

  # View a single issue
  %(prog)s issue ABC-123

  # List all issues from a project
  %(prog)s issue -p INFRA -n 10

  # List issues with descriptions
  %(prog)s issue -p INFRA --describe

  # Search with JQL
  %(prog)s search "project = INFRA AND status = 'In Progress'"

  # Show comments on an issue
  %(prog)s comments ABC-123
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump configuration and exit",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    # jira_cli.py issue [KEY]
    p_issue = subparsers.add_parser(
        "issue",
        help="Show a single issue or list all issues",
        epilog="""
Examples:
  # Show a specific issue with description
  %(prog)s ABC-123

  # Show issue without description
  %(prog)s ABC-123 --no-description

  # List all issues from INFRA project
  %(prog)s -p INFRA

  # List 5 most recent issues from a project
  %(prog)s -p INFRA -n 5

  # List issues with descriptions
  %(prog)s -p INFRA --describe

  # List your issues (assigned to or reported by you)
  %(prog)s
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p_issue.add_argument("key", nargs="?", help="Issue key, e.g. ABC-123 (if omitted, lists all issues)")
    p_issue.add_argument(
        "--no-description",
        action="store_true",
        help="Do not show issue description (for single issue)",
    )
    p_issue.add_argument(
        "-p", "--project",
        type=str,
        help="Filter by project when listing issues (e.g., INFRA, ABC)",
    )
    p_issue.add_argument(
        "-n", "--max-results",
        type=int,
        default=20,
        help="Max results to return when listing all issues (default: 20)",
    )
    p_issue.add_argument(
        "--describe",
        action="store_true",
        help="Show descriptions when listing all issues",
    )
    p_issue.add_argument(
        "--width",
        type=int,
        default=100,
        help="Output width for wrapping text (default: 100)",
    )
    p_issue.set_defaults(func=cmd_issue)

    # jira_cli.py search "JQL"
    p_search = subparsers.add_parser(
        "search",
        help="Search issues with JQL",
        epilog="""
Examples:
  # Search for issues assigned to you
  %(prog)s "assignee = currentUser()"

  # Search by project and status
  %(prog)s "project = INFRA AND status = 'In Progress'"

  # Search with custom result limit
  %(prog)s "project = INFRA" -n 50

  # Search and show descriptions
  %(prog)s "project = INFRA AND assignee = currentUser()" --describe

  # Complex JQL query
  %(prog)s "project = INFRA AND status IN ('To Do', 'In Progress') ORDER BY priority DESC"
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
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
    p_comments = subparsers.add_parser(
        "comments",
        help="Show comments for an issue",
        epilog="""
Examples:
  # Show all comments on an issue
  %(prog)s ABC-123

  # Show comments with custom text width
  %(prog)s ABC-123 --width 120
        """,
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
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
        _, base_url, email, api_token = get_config()
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

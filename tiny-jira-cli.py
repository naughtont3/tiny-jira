#!/usr/bin/env python3
import os
import sys
import re
import argparse
import textwrap
import yaml
from jira import JIRA
from jira.exceptions import JIRAError
from rich.console import Console
from rich.table import Table
from rich.panel import Panel
from rich.text import Text
from rich import box

console = Console()


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
                console.print(f"[red]Error: Token file not found: {token_path}[/red]", file=sys.stderr)
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
        console.print(f"[red]Error: missing configuration: {', '.join(missing)}[/red]", file=sys.stderr)
        console.print("[yellow]Please provide them via .config.yml or environment variables:[/yellow]", file=sys.stderr)
        console.print('  [cyan].config.yml format:[/cyan]', file=sys.stderr)
        console.print('    endpoint: "https://your-domain.atlassian.net"', file=sys.stderr)
        console.print('    user: "you@example.com"', file=sys.stderr)
        console.print('    token: "your_api_token"', file=sys.stderr)
        console.print('  [cyan]OR set environment variables:[/cyan]', file=sys.stderr)
        console.print('    export JIRA_BASE_URL="https://your-domain.atlassian.net"', file=sys.stderr)
        console.print('    export JIRA_EMAIL="you@example.com"', file=sys.stderr)
        console.print('    export JIRA_API_TOKEN="your_api_token"', file=sys.stderr)
        sys.exit(1)

    # Return JIRA client instance
    try:
        jira = JIRA(server=base_url.rstrip("/"), basic_auth=(email, api_token))
        return jira, base_url, email, api_token
    except JIRAError as e:
        console.print(f"[red]Error connecting to Jira: {e}[/red]", file=sys.stderr)
        sys.exit(1)


def wrap(text, width=80, indent=""):
    """Wrap text to specified width."""
    if not text:
        return ""
    wrapper = textwrap.TextWrapper(width=width, subsequent_indent=indent)
    return wrapper.fill(text)


def create_issues_table():
    """Create a Rich table for displaying issues."""
    table = Table(box=box.ROUNDED, show_header=True, header_style="bold cyan")
    table.add_column("Key", style="bold yellow", width=16)
    table.add_column("Summary", style="default", width=40)
    table.add_column("Status", style="green", width=15)
    table.add_column("Labels", style="magenta", width=20)
    table.add_column("Assignee", style="blue", width=20)
    table.add_column("Created", style="dim", width=12)
    table.add_column("Updated", style="dim", width=12)
    return table


def parse_filters(filter_string):
    """Parse filter string into list of (field, value) tuples.

    Example: 'summary:"CSP ",assignee:"christ"'
    Returns: [("summary", "CSP "), ("assignee", "christ")]
    """
    if not filter_string:
        return []

    # Pattern to match: fieldname:"value"
    pattern = r'(\w+):"([^"]*)"'
    matches = re.findall(pattern, filter_string)
    return [(field.lower(), value) for field, value in matches]


def filter_issues(issues, filters):
    """Filter issues based on field filters (case-insensitive substring match).

    Args:
        issues: List of JIRA Issue objects
        filters: List of (field, value) tuples from parse_filters()

    Returns:
        Filtered list of issues where ALL filters match
    """
    if not filters:
        return issues

    filtered = []
    for issue in issues:
        match_all = True
        for field, value in filters:
            value_lower = value.lower()

            if field == "key":
                if value_lower not in issue.key.lower():
                    match_all = False
                    break
            elif field == "summary":
                if value_lower not in issue.fields.summary.lower():
                    match_all = False
                    break
            elif field == "status":
                if value_lower not in issue.fields.status.name.lower():
                    match_all = False
                    break
            elif field == "assignee":
                assignee_name = issue.fields.assignee.displayName if issue.fields.assignee else ""
                if value_lower not in assignee_name.lower():
                    match_all = False
                    break
            elif field == "reporter":
                reporter_name = issue.fields.reporter.displayName if issue.fields.reporter else ""
                if value_lower not in reporter_name.lower():
                    match_all = False
                    break
            elif field == "labels":
                # Match if value is substring of any label
                labels_str = " ".join(issue.fields.labels).lower()
                if value_lower not in labels_str:
                    match_all = False
                    break
            elif field == "issuetype":
                if value_lower not in issue.fields.issuetype.name.lower():
                    match_all = False
                    break
            # Unknown fields are ignored

        if match_all:
            filtered.append(issue)

    return filtered


def add_issue_to_table(table, issue):
    """Add a single issue as a row to the Rich table."""
    # Handle both JIRA Issue objects and dict responses
    if hasattr(issue, 'key'):
        # JIRA Issue object
        key = issue.key
        summary = issue.fields.summary or ""
        status = issue.fields.status.name if issue.fields.status else ""
        assignee = issue.fields.assignee.displayName if issue.fields.assignee else ""
        labels = issue.fields.labels if issue.fields.labels else []
        created = issue.fields.created[:10] if issue.fields.created else ""
        updated = issue.fields.updated[:10] if issue.fields.updated else ""
    else:
        # Dict format (for backward compatibility)
        key = issue.get("key", "")
        fields = issue.get("fields", {})
        summary = fields.get("summary", "")
        status = fields.get("status", {}).get("name", "")
        assignee = (fields.get("assignee") or {}).get("displayName", "")
        labels = fields.get("labels", [])
        created = (fields.get("created") or "")[:10]
        updated = (fields.get("updated") or "")[:10]

    # Format labels as comma-separated string
    labels_str = ", ".join(labels) if labels else "-"

    # Add row with values (Rich will handle truncation)
    table.add_row(
        key,
        summary,
        status,
        labels_str,
        assignee if assignee else "-",
        created,
        updated
    )


def print_issue(issue, show_description=True, width=100, format="detailed"):
    """Print issue details. Works with both JIRA Issue objects and dicts.

    Args:
        issue: JIRA Issue object or dict
        show_description: Whether to show description in detailed format
        width: Width for text wrapping
        format: "detailed" for full view, "table" for compact table row
    """
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
        labels = issue.fields.labels if issue.fields.labels else []
        created = issue.fields.created[:10] if issue.fields.created else ""
        updated = issue.fields.updated[:10] if issue.fields.updated else ""
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
        labels = fields.get("labels", [])
        created = (fields.get("created") or "")[:10]
        updated = (fields.get("updated") or "")[:10]

    # Build the content for the panel
    content = []
    content.append(f"[bold yellow]{key}[/bold yellow]  [cyan][{issue_type}][/cyan]  [green](Status: {status})[/green]")
    content.append(f"[bold]Summary:[/bold]    {summary}")
    content.append(f"[bold]Reporter:[/bold]   {reporter if reporter else '[dim]None[/dim]'}")
    content.append(f"[bold]Assignee:[/bold]   {assignee if assignee else '[dim]Unassigned[/dim]'}")

    if labels:
        labels_str = ", ".join(f"[magenta]{label}[/magenta]" for label in labels)
        content.append(f"[bold]Labels:[/bold]     {labels_str}")

    content.append(f"[bold]Created:[/bold]    [dim]{created}[/dim]")
    content.append(f"[bold]Updated:[/bold]    [dim]{updated}[/dim]")

    if show_description:
        content.append("")
        content.append("[bold]Description:[/bold]")
        if description:
            if isinstance(description, dict):
                # Cloud sometimes uses "doc" format; this is a simple fallback.
                description = description.get("content") or ""
            if not description:
                content.append("  [dim](no description)[/dim]")
            else:
                for line in str(description).splitlines():
                    wrapped = wrap(line, width=width - 4, indent="  ")
                    content.append(f"  {wrapped}")
        else:
            content.append("  [dim](no description)[/dim]")

    # Print as a panel
    console.print(Panel("\n".join(content), border_style="blue", padding=(1, 2)))
    console.print()


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

            # Apply filters if specified
            if args.filter:
                filter_list = parse_filters(args.filter)
                issues = filter_issues(issues, filter_list)

            if not issues:
                console.print("[yellow]No issues found.[/yellow]")
                return

            # Use table format when listing multiple issues without descriptions
            if args.describe:
                # Use detailed format with descriptions
                for issue in issues:
                    print_issue(issue, show_description=True, width=args.width, format="detailed")
            else:
                # Use compact table format
                table = create_issues_table()
                for issue in issues:
                    add_issue_to_table(table, issue)
                console.print(table)
        except JIRAError as e:
            console.print(f"[red]Error fetching issues: {e}[/red]", file=sys.stderr)
            sys.exit(1)
    else:
        # Show single issue (always use detailed format)
        try:
            issue = jira.issue(args.key)
            print_issue(issue, show_description=not args.no_description, width=args.width, format="detailed")
        except JIRAError as e:
            if e.status_code == 404:
                console.print(f"[red]Issue {args.key} not found.[/red]", file=sys.stderr)
            else:
                console.print(f"[red]Error fetching issue: {e}[/red]", file=sys.stderr)
            sys.exit(1)


def cmd_search(args):
    """Search for issues using JQL."""
    jira, _, _, _ = get_config()

    try:
        issues = jira.search_issues(args.jql, maxResults=args.max_results)

        if not issues:
            console.print("[yellow]No issues found.[/yellow]")
            return

        # Use table format when not showing descriptions
        if args.describe:
            for issue in issues:
                print_issue(issue, show_description=True, width=args.width, format="detailed")
        else:
            table = create_issues_table()
            for issue in issues:
                add_issue_to_table(table, issue)
            console.print(table)
    except JIRAError as e:
        console.print(f"[red]Error searching issues: {e}[/red]", file=sys.stderr)
        sys.exit(1)


def cmd_comments(args):
    """Display comments for an issue."""
    jira, _, _, _ = get_config()

    try:
        issue = jira.issue(args.key)
        comments = jira.comments(issue)

        if not comments:
            console.print(f"[yellow]No comments on {args.key}.[/yellow]")
            return

        console.print(f"\n[bold cyan]Comments for {args.key}:[/bold cyan]\n")
        for i, c in enumerate(comments, 1):
            author = c.author.displayName if hasattr(c.author, 'displayName') else str(c.author)
            body = c.body or ""

            content = []
            content.append(f"[bold blue]Author:[/bold blue] {author}")
            content.append("")

            for line in str(body).splitlines():
                wrapped = wrap(line, width=args.width - 4, indent="")
                content.append(wrapped)

            console.print(Panel("\n".join(content), border_style="dim blue", padding=(1, 2)))

    except JIRAError as e:
        if e.status_code == 404:
            console.print(f"[red]Issue {args.key} not found.[/red]", file=sys.stderr)
        else:
            console.print(f"[red]Error fetching comments: {e}[/red]", file=sys.stderr)
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
    p_issue.add_argument(
        "--filter",
        help='Filter results by field values (format: field:"value",field:"value"). '
             'Supported fields: key, summary, status, assignee, reporter, labels, issuetype. '
             'Example: --filter summary:"bug",status:"progress"'
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
        console.print(Panel(
            f"[bold cyan]Endpoint:[/bold cyan] {base_url}\n"
            f"[bold cyan]User:[/bold cyan]     {email}\n"
            f"[bold cyan]Token:[/bold cyan]    {'*' * 8 if api_token else '[dim](not set)[/dim]'}",
            title="[bold yellow]Jira Configuration[/bold yellow]",
            border_style="green",
            padding=(1, 2)
        ))
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

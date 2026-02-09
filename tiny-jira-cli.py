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
TABLE_BOX = box.ROUNDED
ASCII_MODE = False


def print_block(content, **panel_kwargs):
    """Print a block of text; fall back to plain text when in ASCII mode."""
    if ASCII_MODE:
        console.print(content)
    else:
        console.print(Panel(content, **panel_kwargs))


def get_config():
    """Load config and return a JIRA client instance plus resolved defaults."""
    # Try to read from .config.yml first, then ~/.tiny_jira/config.yml
    config_paths = [
        ".config.yml",
        os.path.join(os.path.expanduser("~"), ".tiny_jira", "config.yml"),
    ]
    base_url = None
    email = None
    api_token = None
    default_project = None

    for config_file in config_paths:
        if not os.path.exists(config_file):
            continue

        with open(config_file, "r") as f:
            config = yaml.safe_load(f)

        base_url = config.get("endpoint")
        email = config.get("user")
        token_value = config.get("token")
        project_value = config.get("project")

        if project_value:
            default_project = project_value

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

        # Stop after first config file found in priority order
        if base_url or email or api_token:
            break

    # Fall back to environment variables if not set from config
    if not base_url:
        base_url = os.environ.get("JIRA_BASE_URL")
    if not email:
        email = os.environ.get("JIRA_EMAIL")
    if not api_token:
        api_token = os.environ.get("JIRA_API_TOKEN")
    if not default_project:
        default_project = os.environ.get("JIRA_DEFAULT_PROJECT")

    missing = [name for name, val in [
        ("JIRA_BASE_URL/endpoint", base_url),
        ("JIRA_EMAIL/user", email),
        ("JIRA_API_TOKEN/token", api_token),
    ] if not val]

    if missing:
        console.print(f"[red]Error: missing configuration: {', '.join(missing)}[/red]", file=sys.stderr)
        console.print("[yellow]Please provide them via .config.yml, ~/.tiny_jira/config.yml, or environment variables:[/yellow]", file=sys.stderr)
        console.print('  [cyan].config.yml / ~/.tiny_jira/config.yml format:[/cyan]', file=sys.stderr)
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
        return jira, base_url, email, api_token, default_project
    except JIRAError as e:
        console.print(f"[red]Error connecting to Jira: {e}[/red]", file=sys.stderr)
        sys.exit(1)


def wrap(text, width=80, indent=""):
    """Wrap text to specified width."""
    if not text:
        return ""
    wrapper = textwrap.TextWrapper(width=width, subsequent_indent=indent)
    return wrapper.fill(text)


def show_examples(prog_name):
    """Display usage examples and exit."""
    examples = textwrap.dedent(f"""
        Examples:
          # Show configuration
          {prog_name} --dump

          # View a single issue
          {prog_name} issue ABC-123

          # List all issues from a project
          {prog_name} issue -p INFRA -n 10

          # List issues with descriptions
          {prog_name} issue -p INFRA --describe

          # Search with JQL
          {prog_name} search "project = INFRA AND status = 'In Progress'"

          # Show comments on an issue
          {prog_name} comments ABC-123

        Issue command:
          # Show a specific issue with description
          {prog_name} issue ABC-123

          # Show issue without description
          {prog_name} issue ABC-123 --no-description

          # List all issues from INFRA project
          {prog_name} issue -p INFRA

          # List 5 most recent issues from a project
          {prog_name} issue -p INFRA -n 5

          # List issues with descriptions
          {prog_name} issue -p INFRA --describe

          # List your issues (assigned to or reported by you)
          {prog_name} issue

        Search command:
          # Search for issues assigned to you
          {prog_name} search "assignee = currentUser()"

          # Search by project and status
          {prog_name} search "project = INFRA AND status = 'In Progress'"

          # Search with custom result limit
          {prog_name} search "project = INFRA" -n 50

          # Search and show descriptions
          {prog_name} search "project = INFRA AND assignee = currentUser()" --describe

          # Complex JQL query
          {prog_name} search "project = INFRA AND status IN ('To Do', 'In Progress') ORDER BY priority DESC"

        Comments command:
          # Show all comments on an issue
          {prog_name} comments ABC-123

          # Show comments with custom text width
          {prog_name} comments ABC-123 --width 120
    """).strip()
    print_block(
        examples,
        title="[bold yellow]Examples[/bold yellow]",
        border_style="green",
        padding=(1, 2)
    )


def get_column_registry():
    """Return a dictionary mapping column names to their configuration.

    Each column config includes:
    - header: Display name for column header
    - style: Rich style for the column
    - min_width: Minimum width for the column
    - ideal_width: Ideal width (None means flexible/summary field)
    - field_extractor: Function to extract value from issue
    """
    return {
        'key': {
            'header': 'Key',
            'style': 'bold yellow',
            'min_width': 10,
            'ideal_width': 12,
            'field_extractor': lambda issue: (
                issue.key if hasattr(issue, 'key') else issue.get('key', '')
            )
        },
        'summary': {
            'header': 'Summary',
            'style': 'default',
            'min_width': 30,
            'ideal_width': None,  # Flexible - gets remaining space
            'field_extractor': lambda issue: (
                (issue.fields.summary or "") if hasattr(issue, 'key')
                else issue.get('fields', {}).get('summary', '')
            )
        },
        'status': {
            'header': 'Status',
            'style': 'green',
            'min_width': 10,
            'ideal_width': 12,
            'field_extractor': lambda issue: (
                (issue.fields.status.name if issue.fields.status else "") if hasattr(issue, 'key')
                else issue.get('fields', {}).get('status', {}).get('name', '')
            )
        },
        'labels': {
            'header': 'Labels',
            'style': 'magenta',
            'min_width': 10,
            'ideal_width': 15,
            'field_extractor': lambda issue: (
                ", ".join(issue.fields.labels) if hasattr(issue, 'key') and issue.fields.labels
                else "-" if hasattr(issue, 'key')
                else (", ".join(issue.get('fields', {}).get('labels', [])) if issue.get('fields', {}).get('labels', []) else "-")
            )
        },
        'assignee': {
            'header': 'Assignee',
            'style': 'blue',
            'min_width': 12,
            'ideal_width': 18,
            'field_extractor': lambda issue: (
                (issue.fields.assignee.displayName if issue.fields.assignee else "-") if hasattr(issue, 'key')
                else ((issue.get('fields', {}).get('assignee') or {}).get('displayName', '-'))
            )
        },
        'created': {
            'header': 'Created',
            'style': 'dim',
            'min_width': 10,
            'ideal_width': 10,
            'field_extractor': lambda issue: (
                (issue.fields.created[:10] if issue.fields.created else "") if hasattr(issue, 'key')
                else (issue.get('fields', {}).get('created', '') or "")[:10]
            )
        },
        'updated': {
            'header': 'Updated',
            'style': 'dim',
            'min_width': 10,
            'ideal_width': 10,
            'field_extractor': lambda issue: (
                (issue.fields.updated[:10] if issue.fields.updated else "") if hasattr(issue, 'key')
                else (issue.get('fields', {}).get('updated', '') or "")[:10]
            )
        },
    }


def calculate_column_widths(columns, terminal_width):
    """Calculate optimal widths for each column based on terminal width.

    Priority-based approach:
    1. Start with minimum widths for all columns
    2. Expand fields to ideal widths (prioritize non-summary fields)
    3. Give remaining space to summary

    Args:
        columns: List of column names
        terminal_width: Available terminal width

    Returns:
        Dict mapping column names to calculated widths
    """
    registry = get_column_registry()

    # Reserve space for table borders and padding
    # Each column needs ~3 chars (padding + border), plus 2 for table edges
    border_overhead = len(columns) * 3 + 2
    available_width = max(terminal_width - border_overhead, 40)  # Minimum 40 chars

    widths = {}

    # Phase 1: Allocate minimum widths
    for col in columns:
        widths[col] = registry[col]['min_width']
        available_width -= registry[col]['min_width']

    # Phase 2: Expand non-summary fields to their ideal widths
    for col in columns:
        ideal = registry[col]['ideal_width']
        if ideal is not None and ideal > widths[col]:  # Has ideal width and not yet at ideal
            extra_needed = ideal - widths[col]
            if available_width >= extra_needed:
                widths[col] = ideal
                available_width -= extra_needed
            else:
                # Give what we can
                widths[col] += available_width
                available_width = 0
                break

    # Phase 3: Give remaining space to summary (if it's in the columns)
    if 'summary' in columns and available_width > 0:
        widths['summary'] += available_width

    return widths


def parse_columns_arg(columns_arg):
    """Parse the --columns argument into a list of column names.

    Args:
        columns_arg: Comma-separated string of column names

    Returns:
        List of column names, or None if no argument provided

    Raises:
        ValueError: If invalid column names provided
    """
    if not columns_arg:
        return None

    columns = [c.strip().lower() for c in columns_arg.split(',')]

    # Validate
    registry = get_column_registry()
    invalid = [c for c in columns if c not in registry]
    if invalid:
        available = ', '.join(sorted(registry.keys()))
        raise ValueError(
            f"Invalid column(s): {', '.join(invalid)}\n"
            f"Available columns: {available}"
        )

    return columns


def create_issues_table(columns=None):
    """Create a Rich table for displaying issues with customizable columns.

    Args:
        columns: List of column names to display. If None, uses default columns.

    Returns:
        Tuple of (Table object, list of column names)
    """
    # Default to current 7 columns for backward compatibility
    if columns is None:
        columns = ['key', 'summary', 'status', 'labels', 'assignee', 'created', 'updated']

    registry = get_column_registry()

    # Calculate dynamic widths based on terminal width
    widths = calculate_column_widths(columns, console.width)

    # Create table
    table = Table(box=TABLE_BOX, show_header=True, header_style="bold cyan")

    # Add columns with calculated widths
    for col_name in columns:
        config = registry[col_name]
        table.add_column(
            config['header'],
            style=config['style'],
            width=widths[col_name]
        )

    return table, columns


def parse_filters(filter_string):
    """Parse filter string into list of (field, value) tuples.

    Supports both quoted and unquoted values:
    - 'summary:"CSP ",assignee:"christ"' -> [("summary", "CSP "), ("assignee", "christ")]
    - 'summary:Scheduling,status:Done' -> [("summary", "Scheduling"), ("status", "Done")]
    """
    if not filter_string:
        return []

    # Pattern to match: fieldname:"value" OR fieldname:value
    # Try quoted pattern first, then unquoted
    pattern_quoted = r'(\w+):"([^"]*)"'
    pattern_unquoted = r'(\w+):([^,]+)'

    matches = re.findall(pattern_quoted, filter_string)
    if not matches:
        # No quoted matches, try unquoted pattern
        matches = re.findall(pattern_unquoted, filter_string)
        # Strip whitespace from unquoted values
        matches = [(field, value.strip()) for field, value in matches]

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

    # Track which unknown fields we've warned about to avoid duplicate warnings
    warned_fields = set()

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
                summary = issue.fields.summary or ""
                if value_lower not in summary.lower():
                    match_all = False
                    break
            elif field == "status":
                status_name = issue.fields.status.name if issue.fields.status else ""
                if value_lower not in status_name.lower():
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
                labels = issue.fields.labels or []
                labels_str = " ".join(labels).lower()
                if value_lower not in labels_str:
                    match_all = False
                    break
            elif field == "issuetype":
                issuetype_name = issue.fields.issuetype.name if issue.fields.issuetype else ""
                if value_lower not in issuetype_name.lower():
                    match_all = False
                    break
            elif field == "updated":
                updated_date = (issue.fields.updated[:10] if issue.fields.updated else "")
                if value_lower not in updated_date.lower():
                    match_all = False
                    break
            elif field == "created":
                created_date = (issue.fields.created[:10] if issue.fields.created else "")
                if value_lower not in created_date.lower():
                    match_all = False
                    break
            else:
                # Unknown field - warn user (only once per field)
                if field not in warned_fields:
                    warned_fields.add(field)
                    supported = "key, summary, status, assignee, reporter, labels, issuetype, created, updated"
                    console.print(
                        f"[yellow]Warning: Unknown filter field '{field}' ignored. "
                        f"Supported fields: {supported}[/yellow]"
                    )
                # Continue checking other filters but skip this one
                continue

        if match_all:
            filtered.append(issue)

    return filtered


def add_issue_to_table(table, issue, columns):
    """Add a single issue as a row to the Rich table.

    Args:
        table: Rich Table object
        issue: JIRA Issue object or dict
        columns: List of column names (in display order)
    """
    registry = get_column_registry()

    # Extract values for each column using the registry extractors
    row_values = []
    for col_name in columns:
        extractor = registry[col_name]['field_extractor']
        value = extractor(issue)
        row_values.append(value)

    table.add_row(*row_values)


def render_comments(issue_key, comments, width):
    """Render comments for an issue using Rich panels."""
    if not comments:
        console.print(f"[yellow]No comments on {issue_key}.[/yellow]")
        return

    console.print(f"\n[bold cyan]Comments for {issue_key}:[/bold cyan]\n")
    for c in comments:
        if ASCII_MODE:
            console.print("-" * 27)
        author = c.author.displayName if hasattr(c.author, 'displayName') else str(c.author)
        body = c.body or ""

        content = []
        content.append(f"[bold blue]Author:[/bold blue] {author}")
        content.append("")

        for line in str(body).splitlines():
            wrapped = wrap(line, width=width - 4, indent="")
            content.append(wrapped)

        print_block("\n".join(content), border_style="dim blue", padding=(1, 2))
        if ASCII_MODE:
            console.print()


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
    print_block("\n".join(content), border_style="blue", padding=(1, 2))
    console.print()


def cmd_issue(args):
    """Display a single issue or list all issues."""
    jira, _, _, _, default_project = get_config()

    # If no key provided, list all issues
    if not args.key:
        try:
            # Build JQL query based on project filter
            project = args.project or default_project
            if project:
                jql = f"project = {project} ORDER BY updated DESC"
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

            # Parse columns argument
            try:
                columns = parse_columns_arg(getattr(args, 'columns', None))
            except ValueError as e:
                console.print(f"[red]Error: {e}[/red]", file=sys.stderr)
                sys.exit(1)

            # Use table format when listing multiple issues without descriptions
            if args.describe:
                # Use detailed format with descriptions
                for issue in issues:
                    print_issue(issue, show_description=True, width=args.width, format="detailed")
            else:
                # Use compact table format
                table, col_list = create_issues_table(columns)
                for issue in issues:
                    add_issue_to_table(table, issue, col_list)
                console.print(table)
        except JIRAError as e:
            console.print(f"[red]Error fetching issues: {e}[/red]", file=sys.stderr)
            sys.exit(1)
    else:
        # Show single issue (always use detailed format)
        try:
            issue = jira.issue(args.key)
            print_issue(issue, show_description=not args.no_description, width=args.width, format="detailed")

            if args.show_comments:
                try:
                    comments = jira.comments(issue)
                    render_comments(args.key, comments, args.width)
                except JIRAError as e:
                    console.print(f"[red]Error fetching comments for {args.key}: {e}[/red]", file=sys.stderr)
                    sys.exit(1)
        except JIRAError as e:
            if e.status_code == 404:
                console.print(f"[red]Issue {args.key} not found.[/red]", file=sys.stderr)
            else:
                console.print(f"[red]Error fetching issue: {e}[/red]", file=sys.stderr)
            sys.exit(1)


def cmd_search(args):
    """Search for issues using JQL."""
    jira, _, _, _, _ = get_config()

    try:
        issues = jira.search_issues(args.jql, maxResults=args.max_results)

        if not issues:
            console.print("[yellow]No issues found.[/yellow]")
            return

        # Parse columns argument
        try:
            columns = parse_columns_arg(getattr(args, 'columns', None))
        except ValueError as e:
            console.print(f"[red]Error: {e}[/red]", file=sys.stderr)
            sys.exit(1)

        # Use table format when not showing descriptions
        if args.describe:
            for issue in issues:
                print_issue(issue, show_description=True, width=args.width, format="detailed")
        else:
            table, col_list = create_issues_table(columns)
            for issue in issues:
                add_issue_to_table(table, issue, col_list)
            console.print(table)
    except JIRAError as e:
        console.print(f"[red]Error searching issues: {e}[/red]", file=sys.stderr)
        sys.exit(1)


def cmd_comments(args):
    """Display comments for an issue."""
    jira, _, _, _, _ = get_config()

    try:
        issue = jira.issue(args.key)
        comments = jira.comments(issue)

        render_comments(args.key, comments, args.width)

    except JIRAError as e:
        if e.status_code == 404:
            console.print(f"[red]Issue {args.key} not found.[/red]", file=sys.stderr)
        else:
            console.print(f"[red]Error fetching comments: {e}[/red]", file=sys.stderr)
        sys.exit(1)


def main():
    parser = argparse.ArgumentParser(
        description="Minimal Jira CLI using Jira Cloud REST API",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    parser.add_argument(
        "--dump",
        action="store_true",
        help="Dump configuration and exit",
    )
    parser.add_argument(
        "--ascii",
        action="store_true",
        help="Disable color/styling for grep-friendly output",
    )
    parser.add_argument(
        "--examples",
        action="store_true",
        help="Show usage examples and exit",
    )
    subparsers = parser.add_subparsers(dest="command", required=False)

    # jira_cli.py issue [KEY]
    p_issue = subparsers.add_parser(
        "issue",
        help="Show a single issue or list all issues",
        formatter_class=argparse.RawDescriptionHelpFormatter
    )
    p_issue.add_argument("key", nargs="?", help="Issue key, e.g. ABC-123 (if omitted, lists all issues)")
    p_issue.add_argument(
        "--no-description",
        action="store_true",
        help="Do not show issue description (for single issue)",
    )
    p_issue.add_argument(
        "--show-comments",
        action="store_true",
        help="Include comments when showing a specific issue",
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
             'Supported fields: key, summary, status, assignee, reporter, labels, issuetype, created, updated. '
             'Example: --filter summary:"bug",status:"progress",updated:"2025-12"'
    )
    p_issue.add_argument(
        "-c", "--columns",
        type=str,
        help="Comma-separated columns to display in table view. "
             "Available: key, summary, status, labels, assignee, created, updated. "
             "Default: key,summary,status,labels,assignee,created,updated"
    )
    p_issue.set_defaults(func=cmd_issue)

    # jira_cli.py search "JQL"
    p_search = subparsers.add_parser(
        "search",
        help="Search issues with JQL",
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
    p_search.add_argument(
        "-c", "--columns",
        type=str,
        help="Comma-separated columns to display in table view. "
             "Available: key, summary, status, labels, assignee, created, updated. "
             "Default: key,summary,status,labels,assignee,created,updated"
    )
    p_search.set_defaults(func=cmd_search)

    # jira_cli.py comments KEY
    p_comments = subparsers.add_parser(
        "comments",
        help="Show comments for an issue",
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

    # Configure console based on ASCII preference
    global console, TABLE_BOX, ASCII_MODE
    if args.ascii:
        console = Console(color_system=None, force_terminal=False, no_color=True, highlight=False)
        TABLE_BOX = box.ASCII
        ASCII_MODE = True
    else:
        console = Console()
        TABLE_BOX = box.ROUNDED
        ASCII_MODE = False

    if args.examples:
        show_examples(parser.prog)
        sys.exit(0)

    if args.dump:
        _, base_url, email, api_token, default_project = get_config()
        config_lines = [
            f"[bold cyan]Endpoint:[/bold cyan] {base_url}",
            f"[bold cyan]User:[/bold cyan]     {email}",
            f"[bold cyan]Token:[/bold cyan]    {'*' * 8 if api_token else '[dim](not set)[/dim]'}",
        ]
        if default_project:
            config_lines.append(f"[bold cyan]Project:[/bold cyan]  {default_project}")
        print_block(
            "\n".join(config_lines),
            title="[bold yellow]Jira Configuration[/bold yellow]",
            border_style="green",
            padding=(1, 2)
        )
        sys.exit(0)

    if not args.command:
        parser.print_help()
        sys.exit(1)

    args.func(args)


if __name__ == "__main__":
    main()

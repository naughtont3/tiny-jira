#!/usr/bin/env python3
"""Quick test script to verify jira and atlassian-python-api libraries work with current Jira instance"""
import sys
import yaml

# Load config from existing config.yml
def get_config():
    with open("config.yml", "r") as f:
        config = yaml.safe_load(f)

    base_url = config.get("endpoint")
    email = config.get("user")
    token_value = config.get("token")

    if token_value and token_value.startswith("file:"):
        token_path = token_value[5:]
        with open(token_path, "r") as tf:
            api_token = tf.read().strip()
    else:
        api_token = token_value

    return base_url.rstrip("/"), email, api_token


def test_pycontribs_jira():
    """Test the jira (pycontribs) library"""
    print("=" * 60)
    print("Testing: jira (pycontribs/jira)")
    print("=" * 60)

    try:
        from jira import JIRA
    except ImportError:
        print("❌ Library not installed. Install with: pip install jira")
        return False

    try:
        base_url, email, api_token = get_config()
        print(f"Connecting to: {base_url}")
        print(f"As user: {email}")

        # Connect to Jira
        jira = JIRA(
            server=base_url,
            basic_auth=(email, api_token)
        )

        print("✅ Authentication successful!")

        # Test getting current user info
        current_user = jira.current_user()
        print(f"✅ Current user: {current_user}")

        # Test searching for issues (limit to 2 for quick test)
        # Use bounded query with project restriction
        print("\nTesting search (fetching 2 issues)...")

        # Try to get project from config, or use unbounded as fallback
        try:
            with open("config.yml", "r") as f:
                config = yaml.safe_load(f)
                project = config.get("project", "")
                if project:
                    jql = f'project = {project} ORDER BY created DESC'
                else:
                    jql = 'assignee = currentUser() ORDER BY created DESC'
        except:
            jql = 'assignee = currentUser() ORDER BY created DESC'

        print(f"JQL: {jql}")
        issues = jira.search_issues(jql, maxResults=2)

        if issues:
            print(f"✅ Found {len(issues)} issue(s)")
            for issue in issues:
                print(f"\n  Key: {issue.key}")
                print(f"  Summary: {issue.fields.summary}")
                print(f"  Status: {issue.fields.status.name}")
                print(f"  Type: {issue.fields.issuetype.name}")
                if issue.fields.assignee:
                    print(f"  Assignee: {issue.fields.assignee.displayName}")
        else:
            print("⚠️  No issues found (this might be normal)")

        print("\n✅ jira library works correctly!\n")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


def test_atlassian_api():
    """Test the atlassian-python-api library"""
    print("=" * 60)
    print("Testing: atlassian-python-api")
    print("=" * 60)

    try:
        from atlassian import Jira
    except ImportError:
        print("❌ Library not installed. Install with: pip install atlassian-python-api")
        return False

    try:
        base_url, email, api_token = get_config()
        print(f"Connecting to: {base_url}")
        print(f"As user: {email}")

        # Connect to Jira
        jira = Jira(
            url=base_url,
            username=email,
            password=api_token
        )

        print("✅ Authentication successful!")

        # Test getting current user info
        current_user = jira.myself()
        print(f"✅ Current user: {current_user.get('displayName', current_user.get('name'))}")

        # Test searching for issues (limit to 2 for quick test)
        print("\nTesting search (fetching 2 issues)...")

        # Try to get project from config, or use unbounded as fallback
        try:
            with open("config.yml", "r") as f:
                config = yaml.safe_load(f)
                project = config.get("project", "")
                if project:
                    jql = f'project = {project} ORDER BY created DESC'
                else:
                    jql = 'assignee = currentUser() ORDER BY created DESC'
        except:
            jql = 'assignee = currentUser() ORDER BY created DESC'

        print(f"JQL: {jql}")
        results = jira.jql(jql, limit=2)

        if results and results.get('issues'):
            issues = results['issues']
            print(f"✅ Found {len(issues)} issue(s)")
            for issue in issues:
                fields = issue.get('fields', {})
                print(f"\n  Key: {issue.get('key')}")
                print(f"  Summary: {fields.get('summary')}")
                print(f"  Status: {fields.get('status', {}).get('name')}")
                print(f"  Type: {fields.get('issuetype', {}).get('name')}")
                if fields.get('assignee'):
                    print(f"  Assignee: {fields['assignee'].get('displayName')}")
        else:
            print("⚠️  No issues found (this might be normal)")

        print("\n✅ atlassian-python-api library works correctly!\n")
        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        traceback.print_exc()
        return False


if __name__ == "__main__":
    print("\nJira Library Compatibility Test")
    print("This will test both popular Jira Python libraries\n")

    results = []

    # Test both libraries
    results.append(("jira (pycontribs)", test_pycontribs_jira()))
    print()
    results.append(("atlassian-python-api", test_atlassian_api()))

    # Summary
    print("=" * 60)
    print("SUMMARY")
    print("=" * 60)
    for name, success in results:
        status = "✅ WORKS" if success else "❌ FAILED"
        print(f"{name}: {status}")

    print("\nNext steps:")
    print("- If a library works, you can use it in your CLI")
    print("- If neither is installed, run:")
    print("  pip install jira")
    print("  pip install atlassian-python-api")

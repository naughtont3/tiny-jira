# Next Steps for tiny-jira CLI

## Current Status

### Completed:
- ✅ Created CLAUDE.md documentation file
- ✅ Added `--dump` flag to display configuration
- ✅ Fixed config.yml path issues (token file path, project name)
- ✅ Tested both Python Jira libraries (`jira` and `atlassian-python-api`)
- ✅ Verified `jira` (pycontribs/jira) library works with the Jira instance

### Test Results:
- **jira (pycontribs/jira) v3.10.5**: ✅ FULLY WORKING
  - Authentication successful
  - Successfully queries INFRA project
  - Properly parses all issue fields
  - Uses correct API v3 endpoints

- **atlassian-python-api v4.0.7**: ❌ NOT COMPATIBLE
  - Still uses deprecated API v2 endpoints
  - Not recommended for this project

### Current Configuration:
- Endpoint: `https://amscproject.atlassian.net`
- User: `thomas.naughton@americansciencecloud.org`
- Token: Loaded from file at `/Users/3t4/tokens/` (path corrected)
- Project: `INFRA` (corrected from `AmSC`)

## Next Steps

### Option 1: Refactor to use `jira` library
Refactor `tiny-jira-cli.py` to use the `jira` (pycontribs/jira) library instead of raw `requests` calls.

**Benefits:**
- Automatic authentication handling
- Built-in field parsing (no manual JSON navigation)
- Better error handling and messages
- Support for more Jira features out of the box
- Maintained and up-to-date with Jira API changes

**Changes needed:**
1. Update `requirements.txt` to include `jira`
2. Refactor `get_config()` to return JIRA client instance
3. Simplify `cmd_issue()`, `cmd_search()`, `cmd_comments()` functions
4. Update field access patterns (e.g., `issue.fields.summary` instead of `issue.get('fields', {}).get('summary')`)
5. Test all commands still work correctly

### Option 2: Keep current implementation
Stay with the current `requests`-based approach to maintain the "tiny" philosophy.

**Benefits:**
- Minimal dependencies
- Full control over API calls
- Easier to understand for learning purposes

**Changes needed:**
- None, current implementation works
- May need updates if Jira API changes in the future

## Files to Review When Resuming:
- `tiny-jira-cli.py` - Main CLI implementation
- `test_jira_libs.py` - Library compatibility tests
- `config.yml` - Configuration file with correct settings
- `CLAUDE.md` - Documentation for future Claude Code sessions

## Questions to Consider:
1. Which option aligns better with project goals (simplicity vs functionality)?
2. Are there specific Jira features needed that would benefit from the library?
3. Should we maintain both versions (tiny vs full-featured)?

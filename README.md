# GitLab AI Code Review Agent

An automated code review agent for GitLab that uses Claude AI to provide friendly, constructive feedback on merge requests.

## Features

📝 **Structured Reviews**: JSON-formatted feedback with severity and category classifications  
💬 **Inline Comments**: Posts specific feedback on affected lines  
📊 **Summary Notes**: Generates issue breakdown by severity level  
🔄 **Smart Retry**: Automatically retries if Claude returns invalid JSON  
✅ **Validation**: Comprehensive validation of line numbers and file paths  

## Setup

### 1. Prerequisites
- Python 3.8+
- GitLab account with API access
- Anthropic API key (Claude access)

### 2. Installation

```bash
# Clone or navigate to the project
cd homer

# Create Python virtual environment
python3 -m venv venv

# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows

# Install dependencies
pip install -r requirements.txt

# Create .env file from template
cp .env.example .env
```

### 3. Configure .env

Edit `.env` with your credentials:

```env
ANTHROPIC_API_KEY=sk-ant-...
ANTHROPIC_MODEL=claude-3-opus-20240229
GITLAB_TOKEN=glpat-...
GITLAB_PROJECT_ID=12345678
GITLAB_URL=https://gitlab.com
BASE_BRANCH=main
```

**Getting credentials:**
- **ANTHROPIC_API_KEY**: Get from [Anthropic Console](https://console.anthropic.com)
- **GITLAB_TOKEN**: Create in GitLab Settings → Access Tokens (need `api` scope)
- **GITLAB_PROJECT_ID**: Found in GitLab project Settings → General
- **GITLAB_URL**: Use `https://gitlab.com` for GitLab.com or your self-hosted URL

## Usage

First, activate the virtual environment:

```bash
# Activate virtual environment
source venv/bin/activate  # On macOS/Linux
# or
venv\Scripts\activate     # On Windows
```

Then run the agent:

### Run by MR IID (Recommended)
```bash
python agent.py 42
```

### Run by Branch Name
```bash
python agent.py feature/new-feature
```

The agent will:
1. Fetch the merge request and diff
2. Send to Claude for review
3. Validate the JSON response
4. Post inline comments on affected lines
5. Post a summary note with issue breakdown
3. Validate the JSON response
4. Post inline comments on affected lines
5. Post a summary note with issue breakdown

## JSON Response Format

Claude returns structured feedback:

```json
{
  "summary": "High-level summary of changes",
  "overall_assessment": "approve|request_changes|comment",
  "comments": [
    {
      "file_path": "src/utils.js",
      "start_line": 42,
      "end_line": 42,
      "severity": "low|medium|high",
      "category": "bug|performance|security|readability|architecture|style",
      "comment": "Actionable feedback..."
    }
  ]
}
```

## Architecture

```
GitLab MR Trigger
        ↓
Fetch MR + Diff (GitLab API)
        ↓
Claude Review
        ↓
Validate JSON
        ↓
Post Inline Discussions
        ↓
Post Summary Note
```

## Validation Rules

✅ All required JSON keys present  
✅ Enum values are valid  
✅ Line numbers are integers and `start_line ≤ end_line`  
✅ File paths match the MR diff  
✅ Only references added/modified lines  

## Error Handling

- **Missing env vars**: Exits with error message
- **No MR found**: Exits gracefully if branch/IID not found
- **No changes**: Exits gracefully if MR has no changes
- **Invalid JSON**: Automatically retries with correction prompt
- **API errors**: Logs error and continues with next comment

## Configuration

The agent reads from `.env` file:
- `ANTHROPIC_MODEL`: Claude model version (default: claude-3-opus-20240229)
- `GITLAB_URL`: GitLab instance URL (default: https://gitlab.com)
- `BASE_BRANCH`: Base branch for comparison (default: main)

## Troubleshooting

**Virtual environment issues**
- Make sure virtual environment is activated: `source venv/bin/activate`
- On Windows, use: `venv\Scripts\activate`
- To deactivate later, just type: `deactivate`

**"No open merge request found for branch"**
- Ensure the branch has an open MR
- Check the branch name spelling

**"Missing environment variables"**
- Verify all required vars are in `.env`
- Check file is named `.env` (not `.env.example`)
- Make sure virtual environment is activated before running the agent

**"Invalid JSON" error after retry**
- Check Claude API quota/limits
- Try with a smaller diff manually
- Verify `ANTHROPIC_API_KEY` is correct

**"Unauthorized" from GitLab**
- Verify `GITLAB_TOKEN` is valid
- Ensure token has `api` scope
- Check `GITLAB_PROJECT_ID` is correct

## License
MIT

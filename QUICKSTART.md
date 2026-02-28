# Project Structure

```
homer/
├── INSTRUCTIONS.md          # Original specification
├── README.md               # Complete documentation
├── QUICKSTART.md           # This file - project structure overview
├──
├── agent.py                # Main application
│   ├── validate_env_vars()
│   ├── fetch_merge_request()
│   ├── build_diff_text()
│   ├── create_system_prompt()
│   ├── create_user_prompt()
│   ├── call_claude_for_review()
│   ├── validate_review_json()
│   ├── post_inline_comment()
│   ├── post_summary_note()
│   └── main()
│
├── verify_setup.py         # Setup verification tool
│   ├── test_env_vars()
│   ├── test_imports()
│   ├── test_api_connectivity()
│   └── main()
│
├── quickstart.sh           # Automated setup script
│
├── requirements.txt        # Python dependencies
│   ├── anthropic
│   ├── requests
│   └── python-dotenv
│
├── .env.example            # Environment variables template
├── .env                    # Actual env vars (create from template)
│ └── .gitignore            # Git exclusions
│
└── examples/               # Documentation and examples
    └── EXAMPLES.md         # Example inputs/outputs and schema
```

## File Descriptions

### Core Files

**agent.py** (420 lines)
- Main application entry point
- Handles all GitLab API interactions
- Manages Claude API calls
- Validates JSON responses
- Posts comments and summaries

**verify_setup.py** (130 lines)
- Checks environment variables
- Verifies Python package installations
- Tests API connectivity
- Helps troubleshoot configuration issues

### Configuration

**.env.example**
- Template with all required variables
- Copy to `.env` and fill in your credentials
- Never commit `.env` to git

**requirements.txt**
- Python 3.8+ dependencies
- Install with: `pip install -r requirements.txt`

### Documentation

**README.md**
- Complete usage guide
- Setup instructions
- Troubleshooting section
- Features overview

**examples/EXAMPLES.md**
- Example diffs and Claude responses
- JSON schema reference
- Example GitLab comments
- Tips and best practices

**INSTRUCTIONS.md**
- Original specification
- All requirements outlined
- API endpoint references

## Dependencies

Required Python packages:
- **anthropic**: Claude API client
- **requests**: HTTP library for GitLab API
- **python-dotenv**: Environment variable loading

All specified in `requirements.txt`

## Key Classes and Functions

### CodeComment (dataclass)
Represents a single code review comment with:
- file_path, start_line, end_line
- severity (low/medium/high)
- category (bug/performance/security/readability/architecture/style)
- comment text

### ReviewResponse (dataclass)
Structured response from Claude containing:
- summary
- overall_assessment (approve/request_changes/comment)
- comments list

### Main Functions

**fetch_merge_request()**
- Retrieves MR from GitLab API
- Supports both IID and branch name
- Returns full diff data

**call_claude_for_review()**
- Calls Anthropic API with Homer persona
- Handles JSON validation
- Retries once if validation fails

**validate_review_json()**
- Ensures JSON structure is correct
- Validates all enum values
- Checks line numbers are within diff

**post_inline_comment()**
- Posts comment to specific lines
- Handles single and multi-line comments
- Uses GitLab discussions API

**post_summary_note()**
- Posts final summary review
- Includes issue severity breakdown
- Uses GitLab notes API

## Usage Workflow

1. **Setup**
   ```bash
   # Create and activate virtual environment
   python3 -m venv venv
   source venv/bin/activate          # On macOS/Linux
   # or
   venv\Scripts\activate             # On Windows
   
   # Install dependencies
   pip install -r requirements.txt
   
   # Configure credentials
   cp .env.example .env
   # Edit .env with your API credentials
   ```

2. **Verify**
   ```bash
   # Make sure venv is activated, then:
   python verify_setup.py
   ```

3. **Run Review**
   ```bash
   # Make sure venv is activated, then:
   python agent.py 42                  # MR IID
   python agent.py feature/branch      # Branch name
   ```

4. **View Results**
   - Check GitLab MR for inline comments
   - Check summary note at bottom of MR

5. **Deactivate Virtual Environment (optional)**
   ```bash
   deactivate
   ```

## API Integrations

### GitLab API
- GET `/projects/:id/merge_requests/:iid/changes` - Fetch MR diff
- GET `/projects/:id/merge_requests/:iid` - Get MR details
- POST `/projects/:id/merge_requests/:iid/discussions` - Post inline comments
- POST `/projects/:id/merge_requests/:iid/notes` - Post summary note

### Anthropic API
- POST `/messages` - Send code to Claude for review

## Error Handling

The application gracefully handles:
- Missing environment variables
- Invalid GitLab credentials
- API rate limits
- Invalid JSON from Claude (with automatic retry)
- Missing files in diff
- Invalid line numbers

## Performance

- Single MR review: ~30-60 seconds
- Depends on:
  - Diff size
  - Claude API latency
  - GitLab API availability
  - Network speed

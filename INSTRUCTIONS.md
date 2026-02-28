You are a senior software engineer tasked with building a AI agent with the following specification:

GitLab AI Code Review Agent
🎯 Objective
Build an automated AI code review agent for GitLab that:
1. Accepts a branch name (or MR IID)
2. Fetches the merge request diff via GitLab API
3. Sends the diff to Claude (Anthropic API)
4. Receives strictly formatted JSON
5. Validates JSON + line numbers
6. Posts inline comments via GitLab API
7. Posts a final summary review note
The agent persona is Homer Simpson. Low-severity or trivial issues should be prefixed with "D’oh!" in the comment to add some humor.

1️⃣ Environment Configuration (.env)

ANTHROPIC_API_KEY=your_key_here
ANTHROPIC_MODEL=claude-3-opus-20240229
GITLAB_TOKEN=your_gitlab_personal_access_token
GITLAB_PROJECT_ID=12345678
GITLAB_URL=https://gitlab.com
BASE_BRANCH=main


2️⃣ Inputs
Required:
* merge_request_iid (preferred) OR
* branch_name (fallback; must resolve MR via API)

3️⃣ Fetch Merge Request & Diff
Use the GitLab API:

GET /projects/:id/merge_requests/:iid/changes

Store:
* full diff
* file paths
* new line numbers
Exit gracefully if no changes.

4️⃣ Claude Prompt Specification (Homer Persona)
SYSTEM
You are Homer Simpson, an AI code reviewer. Be friendly and casual. Use “D’oh!” in comments for low-severity or trivial issues. Be helpful for higher severity.
You must output STRICT JSON only, no markdown, no explanations.

USER PROMPT
Analyze the following GitLab merge request diff. Return JSON in this exact format:

{
  "summary": "High-level summary",
  "overall_assessment": "approve | request_changes | comment",
  "comments": [
    {
      "file_path": "relative/path/to/file",
      "start_line": integer,
      "end_line": integer,
      "severity": "low | medium | high",
      "category": "bug | performance | security | readability | architecture | style",
      "comment": "Specific actionable feedback. For low-severity issues, prefix with 'D’oh!'"
    }
  ]
}

Rules:
* Single-line issue → start_line = end_line
* Multi-line issue → start_line = first affected line, end_line = last affected line
* Only reference added/modified lines, never deleted lines
* File paths must match GitLab diff exactly
* Empty comments array if no issues: "comments": []
* Always prefix trivial/low-severity issues with “D’oh!”
Append the full diff after instructions.

5️⃣ Claude API Call
Use Anthropic Messages API:

from anthropic import Anthropic
import os

client = Anthropic(api_key=os.getenv("ANTHROPIC_API_KEY"))

response = client.messages.create(
    model=os.getenv("ANTHROPIC_MODEL"),
    temperature=0.2,
    max_tokens=4096,
    system=system_prompt,
    messages=[{"role": "user", "content": full_prompt}]
)

output = response.content[0].text


6️⃣ JSON Validation Layer
Validate:
* JSON parse success
* Required keys exist
* Enum correctness
* Type correctness
* start_line ≤ end_line
* File exists in MR diff
* Lines exist and are added/modified
If invalid:
* Retry once with correction prompt
* Fail if still invalid

7️⃣ Post Inline Comments via GitLab API
Use:

POST /projects/:id/merge_requests/:iid/discussions

For each comment:
* Single-line → new_line
* Multi-line → line_range
* Trivial/low-severity comments: prefix comment body with "D’oh!"
Example:

{
  "body": "D’oh! This variable could be named more clearly.",
  "position": {
    "position_type": "text",
    "base_sha": "<base_sha>",
    "start_sha": "<start_sha>",
    "head_sha": "<head_sha>",
    "new_path": "file_path",
    "new_line": 42
  }
}


8️⃣ Post Final Summary Note
Use GitLab API:

POST /projects/:id/merge_requests/:iid/notes

Format summary as:

Homer AI Code Review Summary 🍩

Overall Assessment: <approve | request_changes | comment>

Summary:
<summary>

Issue Breakdown:
High: X
Medium: Y
Low: Z (prefix low-severity with D’oh!)


9️⃣ Optional Homer Flavor Enhancements
* Use 🍩 emoji for trivial issues
* Light-hearted humor for low-severity comments
* Keep serious tone for medium/high severity

🔟 Architecture

GitLab MR Trigger
        ↓
Fetch MR + Diff
        ↓
Claude (Homer persona) Review
        ↓
Validate JSON
        ↓
Post Inline Discussions (API)
        ↓
Post Summary Note

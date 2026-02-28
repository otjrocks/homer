"""
Homer Simpson GitLab AI Code Review Agent
Using the Anthropic API, this agent reviews GitLab merge request diffs and provides feedbac. It posts inline comments for issues and a final summary note to the MR.
"""

import json
import os
import re
import sys
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import requests
import anthropic
from anthropic import Anthropic
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY")
ANTHROPIC_MODEL = os.getenv("ANTHROPIC_MODEL", "claude-3-opus-20240229")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_PROJECT_ID = os.getenv("GITLAB_PROJECT_ID")
GITLAB_URL = os.getenv("GITLAB_URL", "https://gitlab.com")
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")

NAME_PREFIX = "[Homer (AI)]"
HOMER_IMAGE_URL = "https://github.com/otjrocks/homer/blob/main/assets/homer.jpg?raw=true"


@dataclass
class CodeComment:
    """Represents a single code review comment"""
    file_path: str
    start_line: int
    end_line: int
    severity: str  # low | medium | high
    category: str  # bug | performance | security | readability | architecture | style
    comment: str


@dataclass
class ReviewResponse:
    """Structured response from Claude"""
    summary: str
    overall_assessment: str  # approve | request_changes | comment
    comments: List[CodeComment]


def validate_env_vars() -> bool:
    """Validate required environment variables"""
    required = ["ANTHROPIC_API_KEY", "GITLAB_TOKEN", "GITLAB_PROJECT_ID"]
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Please set these in your .env file")
        return False
    return True


def fetch_merge_request(merge_request_iid: Optional[int] = None, branch_name: Optional[str] = None) -> Dict[str, Any]:
    """
    Fetch merge request details and diff from GitLab API
    
    Args:
        merge_request_iid: Merge request IID (preferred)
        branch_name: Branch name (fallback)
    
    Returns:
        Dict with MR details including diff
    """
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    
    # If branch name provided, resolve to MR IID
    if branch_name and not merge_request_iid:
        print(f"Resolving branch '{branch_name}' to merge request...")
        mr_url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests"
        params = {"source_branch": branch_name, "state": "opened"}
        response = requests.get(mr_url, headers=headers, params=params)
        response.raise_for_status()
        
        mrs = response.json()
        if not mrs:
            print(f"Error: No open merge request found for branch '{branch_name}'")
            sys.exit(1)
        merge_request_iid = mrs[0]["iid"]
        print(f"Found MR IID: {merge_request_iid}")
    
    if not merge_request_iid:
        print("Error: Must provide either merge_request_iid or branch_name")
        sys.exit(1)
    
    # Fetch MR details and changes
    changes_url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests/{merge_request_iid}/changes"
    response = requests.get(changes_url, headers=headers)
    response.raise_for_status()
    
    mr_data = response.json()
    
    if not mr_data.get("changes"):
        print("No changes found in this merge request")
        sys.exit(0)
    
    print(f"Fetched MR {merge_request_iid} with {len(mr_data['changes'])} changed files")
    
    return mr_data


def build_diff_text(mr_data: Dict[str, Any]) -> str:
    """Build full diff text from MR changes"""
    diff_lines = []
    
    for change in mr_data["changes"]:
        file_path = change["new_path"] or change["old_path"]
        diff_lines.append(f"\n=== {file_path} ===")
        diff_lines.append(change.get("diff", ""))
    
    return "\n".join(diff_lines)

def validate_review_json(raw_response: str) -> Optional[Dict[str, Any]]:
    """
    Validate JSON response from Claude
    
    Args:
        raw_response: Raw text response from Claude
    
    Returns:
        Parsed JSON if valid, None otherwise
    """
    try:
        # Try to extract JSON from response (in case there's extra text)
        json_match = re.search(r'\{.*\}', raw_response, re.DOTALL)
        if not json_match:
            print("Error: No JSON found in response")
            return None
        
        json_str = json_match.group(0)
        data = json.loads(json_str)
        
        # Validate required keys
        required_keys = ["summary", "overall_assessment", "comments"]
        if not all(key in data for key in required_keys):
            print(f"Error: Missing required keys. Expected: {required_keys}")
            return None
        
        # Validate overall_assessment enum
        valid_assessments = ["approve", "request_changes", "comment"]
        if data["overall_assessment"] not in valid_assessments:
            print(f"Error: overall_assessment must be one of {valid_assessments}")
            return None
        
        # Validate comments
        if not isinstance(data["comments"], list):
            print("Error: comments must be a list")
            return None
        
        for comment in data["comments"]:
            required_comment_keys = ["file_path", "start_line", "end_line", "severity", "category", "comment"]
            if not all(key in comment for key in required_comment_keys):
                print(f"Error: Comment missing required keys: {required_comment_keys}")
                return None
            
            # Validate enums
            if comment["severity"] not in ["low", "medium", "high"]:
                print(f"Error: Invalid severity: {comment['severity']}")
                return None
            
            valid_categories = ["bug", "performance", "security", "readability", "architecture", "style"]
            if comment["category"] not in valid_categories:
                print(f"Error: Invalid category: {comment['category']}")
                return None
            
            # Validate line numbers
            if comment["start_line"] > comment["end_line"]:
                print(f"Error: start_line ({comment['start_line']}) > end_line ({comment['end_line']})")
                return None
            
            if not isinstance(comment["start_line"], int) or not isinstance(comment["end_line"], int):
                print("Error: Line numbers must be integers")
                return None
        
        return data
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON - {e}")
        return None


def call_claude_for_review(system_prompt: str, user_prompt: str, retry_count: int = 0) -> Optional[Dict[str, Any]]:
    """
    Call Claude API for code review
    
    Args:
        system_prompt: System prompt with Homer persona
        user_prompt: User prompt with diff
        retry_count: Number of retries (0 = no retries done yet)
    
    Returns:
        Parsed JSON response if valid, None otherwise
    """
    try:
        client = Anthropic(api_key=ANTHROPIC_API_KEY)
    except TypeError as e:
        print(f"Error creating Anthropic client: {e}")
        print("This is often caused by an incompatible 'httpx' version. Please run:")
        print("  pip install 'httpx==0.23.3'  # or pip install -r requirements.txt")
        sys.exit(1)
    
    print(f"Calling Claude for review (attempt {retry_count + 1})...")

    try:
        response = client.messages.create(
            model=ANTHROPIC_MODEL,
            temperature=0.2,
            max_tokens=4096,
            system=system_prompt,
            messages=[{"role": "user", "content": user_prompt}]
        )
    except anthropic.NotFoundError as e:
        print(f"Error: Model '{ANTHROPIC_MODEL}' not found.")
        sys.exit(1)
    except Exception as e:
        print(f"Error calling Anthropic API: {e}")
        return None
    
    raw_output = response.content[0].text
    
    # Validate JSON
    validated = validate_review_json(raw_output)
    
    if validated:
        return validated
    
    # Retry once with correction prompt
    if retry_count == 0:
        print("Retrying with correction prompt...")
        correction_prompt = user_prompt + "\n\nIMPORTANT: You must output ONLY valid JSON. No markdown, no explanations, no extra text. Start with '{' and end with '}'."
        return call_claude_for_review(system_prompt, correction_prompt, retry_count + 1)
    
    print("Error: Failed to get valid JSON response after retry")
    return None


def get_mr_details(merge_request_iid: int) -> Dict[str, Any]:
    """Get merge request details including SHAs for API calls"""
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    mr_url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests/{merge_request_iid}"
    
    response = requests.get(mr_url, headers=headers)
    response.raise_for_status()
    
    return response.json()

def post_inline_comment(merge_request_iid: int, mr_data: Dict[str, Any], comment_data: CodeComment, mr_details: Dict[str, Any]) -> bool:
    """
    Post an inline comment to GitLab MR.

    Prefix comments based on severity:
    - Low: "D'oh!"
    - Medium: "⚠️"
    - High: "❗"
    """
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    # Find the change for this file
    change = None
    for c in mr_data["changes"]:
        file_path = c["new_path"] or c["old_path"]
        if file_path == comment_data.file_path:
            change = c
            break

    if not change:
        print(f"Error: File {comment_data.file_path} not found in MR changes")
        return False

    # Prefix based on severity
    comment_body = comment_data.comment
    if comment_data.severity == "low" and not comment_body.startswith("D'oh!"):
        comment_body = f"D'oh! {comment_body}"
    elif comment_data.severity == "medium" and not comment_body.startswith("⚠️"):
        comment_body = f"⚠️ {comment_body}"
    elif comment_data.severity == "high" and not comment_body.startswith("➡️"):
        comment_body = f"❗ {comment_body}"
    
    comment_body = f"{NAME_PREFIX} {comment_body}"

    # Prepare position data
    if comment_data.start_line == comment_data.end_line:
        # Single-line comment
        position = {
            "position_type": "text",
            "base_sha": change.get("base_sha") or mr_details.get("diff_refs", {}).get("base_sha"),
            "start_sha": change.get("start_sha") or mr_details.get("diff_refs", {}).get("start_sha"),
            "head_sha": change.get("head_sha") or mr_details.get("diff_refs", {}).get("head_sha"),
            "new_path": comment_data.file_path,
            "new_line": comment_data.start_line
        }
    else:
        # Multi-line comment
        position = {
            "position_type": "text",
            "base_sha": change.get("base_sha") or mr_details.get("diff_refs", {}).get("base_sha"),
            "start_sha": change.get("start_sha") or mr_details.get("diff_refs", {}).get("start_sha"),
            "head_sha": change.get("head_sha") or mr_details.get("diff_refs", {}).get("head_sha"),
            "new_path": comment_data.file_path,
            "new_line": comment_data.end_line,
            "start_new_line": comment_data.start_line
        }

    # Post discussion
    url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests/{merge_request_iid}/discussions"
    payload = {
        "body": comment_body,
        "position": position
    }

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✓ Posted comment on {comment_data.file_path}:{comment_data.start_line}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error posting comment: {e}")
        return False

def post_summary_note(merge_request_iid: int, review_data: Dict[str, Any]) -> bool:
    """
    Post a final summary note to GitLab MR with Homer image and severity emojis.
    The Homer image is resized to 150px width for readability.
    """
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    # Count issues by severity
    severity_counts = {"low": 0, "medium": 0, "high": 0}
    for comment in review_data.get("comments", []):
        severity = comment.get("severity", "low")
        if severity in severity_counts:
            severity_counts[severity] += 1

    # Include Homer image (resized) and format summary
    summary_text = load_template(
        "summary_note.txt",
        homer_image_url=HOMER_IMAGE_URL,
        image_width=150,
        overall_assessment=review_data["overall_assessment"].replace("_", " ").title(),
        summary=review_data["summary"],
        high_count=severity_counts["high"],
        medium_count=severity_counts["medium"],
        low_count=severity_counts["low"]
    )

    # Post note
    url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests/{merge_request_iid}/notes"
    payload = {"body": summary_text}

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        print(f"✓ Posted summary note with overall assessment: {review_data['overall_assessment']}")
        return True
    except requests.exceptions.RequestException as e:
        print(f"Error posting summary note: {e}")
        return False

def load_template(file_name: str, **kwargs) -> str:
    template_path = os.path.join(os.path.dirname(__file__), "templates", file_name)
    with open(template_path, "r", encoding="utf-8") as f:
        template = f.read()
    for k, v in kwargs.items():
        template = template.replace(f"{{{k}}}", str(v))
    return template

def main():
    """Main entry point"""
    # Validate environment
    if not validate_env_vars():
        sys.exit(1)
    
    # Parse arguments
    merge_request_iid = None
    branch_name = None
    
    if len(sys.argv) > 1:
        arg = sys.argv[1]
        # Try to parse as integer (IID)
        try:
            merge_request_iid = int(arg)
        except ValueError:
            # Treat as branch name
            branch_name = arg
    else:
        print("Usage: python agent.py <merge_request_iid|branch_name>")
        print("Example: python agent.py 42")
        print("Example: python agent.py feature/new-feature")
        sys.exit(1)
    
    print("🍩 Homer Simpson AI Code Review Agent")
    print("=" * 50)
    
    # Fetch MR and diff
    mr_data = fetch_merge_request(merge_request_iid, branch_name)
    mr_id = mr_data["iid"]
    diff_text = build_diff_text(mr_data)
    
    # Get MR details for posting comments
    mr_details = get_mr_details(mr_id)
    
    # Create prompts
    system_prompt = load_template("system_prompt.txt")
    user_prompt = load_template("user_prompt.txt", diff_text=diff_text)
    
    # Call Claude
    review_result = call_claude_for_review(system_prompt, user_prompt)
    
    if not review_result:
        print("Failed to get valid review from Claude")
        sys.exit(1)
    
    print("\n✓ Received valid review from Claude")
    print(f"Overall Assessment: {review_result['overall_assessment']}")
    print(f"Found {len(review_result['comments'])} issue(s)")
    
    # Post comments
    print("\nPosting inline comments...")
    for comment_dict in review_result["comments"]:
        comment = CodeComment(
            file_path=comment_dict["file_path"],
            start_line=comment_dict["start_line"],
            end_line=comment_dict["end_line"],
            severity=comment_dict["severity"],
            category=comment_dict["category"],
            comment=comment_dict["comment"]
        )
        post_inline_comment(mr_id, mr_data, comment, mr_details)
    
    # Post summary
    print("\nPosting summary note...")
    post_summary_note(mr_id, review_result)
    
    print("\n" + "=" * 50)
    print("✓ Code review complete!")


if __name__ == "__main__":
    main()

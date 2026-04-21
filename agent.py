"""
GitLab AI Code Review Agent
Using the Codex SDK, this agent reviews GitLab merge request diffs and provides feedback. It posts inline comments for issues and a final summary note to the MR.
Supports custom Codex API URLs for local, private, government-hosted, and other endpoints.
"""

import json
import os
import re
import sys
from typing import Optional, Dict, Any, List
from dataclasses import dataclass

import requests
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Configuration
CODEX_API_URL = os.getenv("CODEX_API_URL")
CODEX_API_KEY = os.getenv("CODEX_API_KEY")
CODEX_MODEL = os.getenv("CODEX_MODEL")
GITLAB_TOKEN = os.getenv("GITLAB_TOKEN")
GITLAB_PROJECT_ID = os.getenv("GITLAB_PROJECT_ID")
GITLAB_URL = os.getenv("GITLAB_URL")
BASE_BRANCH = os.getenv("BASE_BRANCH", "main")


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
    """Structured response from Codex API"""
    summary: str
    overall_assessment: str  # approve | request_changes | comment
    comments: List[CodeComment]


def validate_env_vars() -> bool:
    """Validate required environment variables"""
    required = ["CODEX_API_KEY", "GITLAB_TOKEN", "GITLAB_PROJECT_ID"]
    missing = [var for var in required if not os.getenv(var)]
    
    if missing:
        print(f"Error: Missing environment variables: {', '.join(missing)}")
        print("Please set these in your .env file")
        return False
    
    # Validate Codex API URL is set
    if not os.getenv("CODEX_API_URL"):
        print("Warning: CODEX_API_URL not set, using default: http://localhost:8000/v1")
    
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
    Validate JSON response from Codex API
    
    Args:
        raw_response: Raw text response from Codex
    
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
            
            valid_categories = ["bug", "performance", "security", "readability", "architecture", "style", "other"]
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


def call_codex_for_review(system_prompt: str, user_prompt: str, retry_count: int = 0) -> Optional[Dict[str, Any]]:
    """
    Call Codex API for code review via custom endpoint
    
    Args:
        system_prompt: System prompt with Homer persona
        user_prompt: User prompt with diff
        retry_count: Number of retries (0 = no retries done yet)
    
    Returns:
        Parsed JSON response if valid, None otherwise
    """
    print(f"Calling Codex for review (attempt {retry_count + 1})...")
    
    # Prepare request headers
    headers = {
        "Content-Type": "application/json",
    }
    
    if CODEX_API_KEY:
        headers["Authorization"] = f"Bearer {CODEX_API_KEY}"
    
    # Prepare request payload (OpenAI-compatible format)
    payload = {
        "model": CODEX_MODEL,
        "messages": [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_prompt}
        ],
        "temperature": 0.2,
        "max_completion_tokens": 4096,
    }
    
    try:
        response = requests.post(
            f"{CODEX_API_URL}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )
        response.raise_for_status()
        
        result = response.json()
        
        # Extract text from response (OpenAI-compatible format)
        if "choices" in result and len(result["choices"]) > 0:
            choice = result["choices"][0]
            if "message" in choice and "content" in choice["message"]:
                raw_output = choice["message"]["content"]
            else:
                print(f"Error: Unexpected Codex API response format: {result}")
                return None
        else:
            print(f"Error: No choices in Codex API response: {result}")
            return None
        
    except requests.exceptions.Timeout:
        print(f"Error: Codex API request timed out at {CODEX_API_URL}")
        return None
    except requests.exceptions.ConnectionError:
        print(f"Error: Cannot connect to Codex API at {CODEX_API_URL}")
        return None
    except requests.exceptions.HTTPError as e:
        # Include response body for debugging
        try:
            error_details = e.response.json()
            print(f"Error calling Codex API: {e}")
            print(f"API Response: {error_details}")
        except:
            print(f"Error calling Codex API: {e}")
            print(f"Response body: {e.response.text}")
        return None
    except requests.exceptions.RequestException as e:
        print(f"Error calling Codex API: {e}")
        return None
    except ValueError as e:
        print(f"Error parsing Codex API response: {e}")
        return None
    
    # Validate JSON
    validated = validate_review_json(raw_output)
    
    if validated:
        return validated
    
    # Retry once with correction prompt
    if retry_count == 0:
        print("Retrying with correction prompt...")
        correction_prompt = user_prompt + "\n\nIMPORTANT: You must output ONLY valid JSON. No markdown, no explanations, no extra text. Start with '{' and end with '}'." 
        return call_codex_for_review(system_prompt, correction_prompt, retry_count + 1)
    
    print("Error: Failed to get valid JSON response after retry")
    return None


def get_mr_details(merge_request_iid: int) -> Dict[str, Any]:
    """Get merge request details including SHAs for API calls"""
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}
    mr_url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests/{merge_request_iid}"
    
    response = requests.get(mr_url, headers=headers)
    response.raise_for_status()
    
    return response.json()

def post_inline_comment(merge_request_iid, mr_data, comment_data, mr_details):
    """
    Post an inline comment to GitLab MR.
    If posting with line numbers fails, retry as a general file comment.
    """
    headers = {"PRIVATE-TOKEN": GITLAB_TOKEN}

    # Find the file change
    change = next(
        (c for c in mr_data["changes"] if (c["new_path"] or c["old_path"]) == comment_data.file_path),
        None
    )
    if not change:
        print(f"Error: File {comment_data.file_path} not found in MR changes")
        return False

    # Map severity to emoji
    prefix = {
        "low": "ℹ️",
        "medium": "⚠️",
        "high": "❗"
    }.get(comment_data.severity.lower(), "")

    # Format comment with markdown for readability
    comment_body = (
        f"Homer: {prefix} {comment_data.comment}\n\n"
        f"> **Severity:** {comment_data.severity.upper()}\n\n"
        f"> **Category:** {comment_data.category.upper()}\n\n"
        f"> _AI-generated comment_"
    )

    # Build initial position (line-level comment)
    position = {
        "position_type": "text",
        "base_sha": change.get("base_sha") or mr_details.get("diff_refs", {}).get("base_sha"),
        "start_sha": change.get("start_sha") or mr_details.get("diff_refs", {}).get("start_sha"),
        "head_sha": change.get("head_sha") or mr_details.get("diff_refs", {}).get("head_sha"),
        "new_path": comment_data.file_path
    }

    if comment_data.start_line is not None and comment_data.end_line is not None:
        if comment_data.start_line != comment_data.end_line:
            position["start_new_line"] = comment_data.start_line
        position["new_line"] = comment_data.end_line
    elif comment_data.start_line is not None or comment_data.end_line is not None:
        position["new_line"] = comment_data.start_line if comment_data.start_line is not None else comment_data.end_line

    url = f"{GITLAB_URL}/api/v4/projects/{GITLAB_PROJECT_ID}/merge_requests/{merge_request_iid}/discussions"

    # Try posting with lines first
    payload = {"body": comment_body}
    if "new_line" in position:
        payload["position"] = position

    try:
        response = requests.post(url, headers=headers, json=payload)
        response.raise_for_status()
        line_info = f"{position.get('start_new_line','')}-{position.get('new_line','')}" if "start_new_line" in position else position.get("new_line", "general")
        print(f"✓ Posted comment on {comment_data.file_path}:{line_info}")
        return True
    except requests.exceptions.RequestException as e:
        # If posting with line numbers fails, try general comment
        print(f"Warning: Failed to post inline comment with lines, retrying as general comment. Error: {e}")
        try:
            general_payload = {"body": comment_body}
            response = requests.post(url, headers=headers, json=general_payload)
            response.raise_for_status()
            print(f"✓ Posted general comment on {comment_data.file_path}")
            return True
        except requests.exceptions.RequestException as e2:
            print(f"Error posting general comment: {e2}")
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

    # Format summary
    summary_text = load_template(
        "summary_note.txt",
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

    print("\n" * 3)
    print("Homer - AI Code Review Agent")
    print("🍩" * 50)
    print("\n")
    
    # Fetch MR and diff
    mr_data = fetch_merge_request(merge_request_iid, branch_name)
    mr_id = mr_data["iid"]
    diff_text = build_diff_text(mr_data)
    
    # Get MR details for posting comments
    mr_details = get_mr_details(mr_id)
    
    # Create prompts
    system_prompt = load_template("system_prompt.txt")
    user_prompt = load_template("user_prompt.txt", diff_text=diff_text)
    
    # Call Codex
    review_result = call_codex_for_review(system_prompt, user_prompt)
    
    if not review_result:
        print("Failed to get valid review from Codex")
        sys.exit(1)
    
    print("\n✓ Received valid review from Codex")
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
    
    print("\n" + "🍩" * 50)
    print("✓ Code review complete!")


if __name__ == "__main__":
    main()

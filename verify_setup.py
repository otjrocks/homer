#!/usr/bin/env python3
"""
Quick setup verification script
Tests that all dependencies and API credentials are configured correctly
"""

import os
import sys
from dotenv import load_dotenv

def test_env_vars():
    """Test environment variables are loaded"""
    print("Testing environment variables...")
    load_dotenv()
    
    required = {
        "ANTHROPIC_API_KEY": "Anthropic API key (starts with sk-ant-)",
        "GITLAB_TOKEN": "GitLab personal access token (starts with glpat-)",
        "GITLAB_PROJECT_ID": "GitLab project ID (numeric)",
    }
    
    optional = {
        "ANTHROPIC_MODEL": "Claude model version (default: claude-3-opus-20240229)",
        "GITLAB_URL": "GitLab URL (default: https://gitlab.com)",
        "BASE_BRANCH": "Base branch (default: main)",
    }
    
    missing = []
    for var, description in required.items():
        if os.getenv(var):
            print(f"✓ {var} is set")
        else:
            print(f"✗ {var} is missing")
            print(f"  Description: {description}")
            missing.append(var)
    
    for var, description in optional.items():
        value = os.getenv(var, "default")
        print(f"✓ {var} = {value}")
    
    return len(missing) == 0


def test_imports():
    """Test required packages are installed"""
    print("\nTesting Python packages...")
    
    packages = {
        "anthropic": "Anthropic API client",
        "requests": "HTTP requests library",
        "dotenv": "dotenv for environment loading",
    }
    
    missing = []
    for package, description in packages.items():
        try:
            __import__(package)
            print(f"✓ {package} is installed")
        except ImportError:
            print(f"✗ {package} is missing")
            print(f"  Description: {description}")
            missing.append(package)
    
    return len(missing) == 0


def test_api_connectivity():
    """Test API connectivity (optional)"""
    print("\nTesting API connectivity...")
    
    try:
        import requests
        from anthropic import Anthropic
    except ImportError:
        print("⚠ Skipping API tests (packages not installed)")
        return True
    
    # Test Anthropic API
    api_key = os.getenv("ANTHROPIC_API_KEY")
    if api_key:
        try:
            client = Anthropic(api_key=api_key)
            # Just test that client initializes
            print("✓ Anthropic API client initialized")
        except Exception as e:
            print(f"✗ Anthropic API error: {e}")
            return False
    else:
        print("⚠ Skipping Anthropic test (no API key)")
    
    # Test GitLab API
    token = os.getenv("GITLAB_TOKEN")
    project_id = os.getenv("GITLAB_PROJECT_ID")
    gitlab_url = os.getenv("GITLAB_URL", "https://gitlab.com")
    
    if token and project_id:
        try:
            headers = {"PRIVATE-TOKEN": token}
            response = requests.get(
                f"{gitlab_url}/api/v4/projects/{project_id}",
                headers=headers,
                timeout=5
            )
            if response.status_code == 200:
                print("✓ GitLab API connection successful")
            else:
                print(f"✗ GitLab API returned {response.status_code}")
                print(f"  Check your token and project ID")
                return False
        except requests.exceptions.RequestException as e:
            print(f"✗ GitLab API error: {e}")
            return False
    else:
        print("⚠ Skipping GitLab test (no token/project ID)")
    
    return True


def main():
    """Run all tests"""
    print("=" * 60)
    print("Homer Simpson AI Code Review Agent - Setup Verification")
    print("=" * 60)
    
    all_pass = True
    
    all_pass &= test_env_vars()
    all_pass &= test_imports()
    all_pass &= test_api_connectivity()
    
    print("\n" + "=" * 60)
    if all_pass:
        print("✓ All checks passed! You're ready to run the agent.")
        print("\nUsage:")
        print("  python agent.py 42              # Review MR #42")
        print("  python agent.py feature/branch  # Review MR on branch")
        return 0
    else:
        print("✗ Some checks failed. Please review the errors above.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

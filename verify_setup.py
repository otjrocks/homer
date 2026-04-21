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
        "CODEX_API_KEY": "Codex API key",
        "GITLAB_TOKEN": "GitLab personal access token (starts with glpat-)",
        "GITLAB_PROJECT_ID": "GitLab project ID (numeric)",
    }
    
    optional = {
        "CODEX_API_URL": "Codex API URL (default: http://localhost:8000/v1)",
        "CODEX_MODEL": "Codex model name (default: codex-review)",
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
    except ImportError:
        print("⚠ Skipping API tests (packages not installed)")
        return True
    
    # Test Codex API
    api_url = os.getenv("CODEX_API_URL", "http://localhost:8000/v1")
    api_key = os.getenv("CODEX_API_KEY")
    
    if api_url and api_url.startswith("http"):
        try:
            headers = {}
            if api_key:
                headers["Authorization"] = f"Bearer {api_key}"
            
            # Try to reach the Codex API endpoint
            response = requests.get(
                f"{api_url}/models",
                headers=headers,
                timeout=5
            )
            
            # Accept various response codes as indicators the endpoint exists
            if response.status_code in [200, 404, 401, 403]:
                print(f"✓ Codex API endpoint is reachable ({api_url})")
            else:
                print(f"⚠ Codex API returned status {response.status_code}")
        except requests.exceptions.Timeout:
            print(f"⚠ Codex API request timed out at {api_url}")
            print("   Endpoint may still work, but is slow to respond")
        except requests.exceptions.ConnectionError:
            print(f"⚠ Cannot connect to Codex API at {api_url}")
            print("   Make sure CODEX_API_URL is correct and the endpoint is running")
        except Exception as e:
            print(f"⚠ Codex API connection error: {e}")
    else:
        print(f"⚠ Invalid or missing CODEX_API_URL: {api_url}")
    
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
        print("\nConfigured Codex Endpoint:")
        codex_url = os.getenv("CODEX_API_URL", "http://localhost:8000/v1")
        print(f"  - {codex_url}")
        return 0
    else:
        print("✗ Some checks failed. Please review the errors above.")
        print("\nFor setup help, see .env.example for configuration examples.")
        return 1


if __name__ == "__main__":
    sys.exit(main())

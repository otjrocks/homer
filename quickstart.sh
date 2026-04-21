#!/usr/bin/env bash
# Quick start script for Homer Simpson AI Code Review Agent

set -e

echo "🍩 Homer Simpson AI Code Review Agent - Quick Start"
echo "=================================================="
echo ""

# Check Python
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 not found. Please install Python 3.8 or higher."
    exit 1
fi

python_version=$(python3 --version | awk '{print $2}')
echo "✓ Found Python $python_version"

# Create virtual environment
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
else
    echo "✓ Virtual environment already exists"
fi

# Activate virtual environment
echo "Activating virtual environment..."
source venv/bin/activate

# Install dependencies
echo "Installing dependencies..."
pip install -r requirements.txt > /dev/null

# Check dependencies installed
echo "\nChecking dependencies..."
python -c "import requests; print('✓ requests:', requests.__version__)" 2>/dev/null || echo "✗ requests not installed"


# Check for .env file
if [ ! -f ".env" ]; then
    echo ""
    echo "⚠️  .env file not found!"
    echo "Creating .env from template..."
    cp .env.example .env
    echo "✓ Created .env file"
    echo ""
    echo "📋 Please edit .env with your Codex API credentials:"
    echo "   - CODEX_API_URL: Your custom Codex API endpoint"
    echo "   - CODEX_API_KEY: API key for authentication"
    echo "   - CODEX_MODEL: Model name at your endpoint"
    echo "   - GITLAB_TOKEN: GitLab personal access token"
    echo "   - GITLAB_PROJECT_ID: GitLab project ID"
    echo ""
    echo "   See .env.example for examples (local, government-hosted, private deployments)"
else
    echo "✓ .env file exists"
fi

# Run verification
echo ""
echo "Running setup verification..."
python3 verify_setup.py

echo ""
echo "✓ Setup complete!"
echo ""
echo "Virtual environment is now ACTIVE (venv)"
echo ""
echo "Next steps:"
echo "1. Edit .env with your API credentials (if you haven't already)"
echo "2. Run: python agent.py <mr_iid or branch_name>"
echo ""
echo "Examples:"
echo "  python agent.py 42                    # Review MR #42"
echo "  python agent.py feature/my-feature    # Review branch"
echo ""
echo "When finished, deactivate the virtual environment:"
echo "  deactivate"
echo ""

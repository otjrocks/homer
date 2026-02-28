.PHONY: help setup install verify test clean run

help:
	@echo "Homer Simpson AI Code Review Agent"
	@echo "===================================="
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  make setup        - Complete setup (install deps, create .env)"
	@echo "  make install      - Install Python dependencies"
	@echo "  make verify       - Verify setup and API connectivity"
	@echo "  make run MR=42    - Run review on MR #42"
	@echo "  make test         - Check Python syntax"
	@echo "  make clean        - Remove cache files and virtual env"
	@echo ""
	@echo "Examples:"
	@echo "  make run MR=42"
	@echo "  make run BRANCH=feature/new-feature"
	@echo "  make verify"
	@echo ""

setup: install
	@if [ ! -f .env ]; then \
		echo "Creating .env from template..."; \
		cp .env.example .env; \
		echo "✓ Created .env - please edit with your credentials"; \
	fi
	@echo ""
	@make verify

install:
	@if [ ! -d venv ]; then \
		echo "Creating virtual environment..."; \
		python3 -m venv venv; \
	fi
	@. venv/bin/activate && pip install -r requirements.txt

verify:
	@. venv/bin/activate && python3 verify_setup.py

test:
	@echo "Testing Python syntax..."
	@python3 -m py_compile agent.py verify_setup.py
	@echo "✓ Syntax check passed"

run:
	@if [ -z "$(MR)$(BRANCH)" ]; then \
		echo "Error: Must provide MR or BRANCH"; \
		echo "Usage: make run MR=42"; \
		echo "       make run BRANCH=feature/branch"; \
		exit 1; \
	fi
	@. venv/bin/activate && python3 agent.py $(if $(MR),$(MR),$(BRANCH))

clean:
	@echo "Cleaning up..."
	@rm -rf venv __pycache__ .pytest_cache .coverage *.pyc
	@find . -type d -name __pycache__ -exec rm -rf {} + 2>/dev/null || true
	@find . -type f -name "*.pyc" -delete
	@echo "✓ Cleaned up cache and virtual environment"

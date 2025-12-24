#!/bin/bash
# Run all code quality checks

set -e

echo "================================"
echo "Running Code Quality Checks"
echo "================================"

echo ""
echo "1. Formatting check (black)..."
uv run black --check .

echo ""
echo "2. Import sorting check (isort)..."
uv run isort --check-only .

echo ""
echo "3. Linting (flake8)..."
uv run flake8 backend/ main.py

echo ""
echo "4. Type checking (mypy)..."
uv run mypy backend/ main.py

echo ""
echo "5. Running tests..."
uv run pytest backend/tests/ -v --cov=backend --cov-report=term-missing

echo ""
echo "================================"
echo "All quality checks passed!"
echo "================================"

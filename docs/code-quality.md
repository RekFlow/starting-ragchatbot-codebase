# Code Quality Guidelines

This document outlines the code quality standards and tools used in this project.

## Tools Overview

### Black - Code Formatter
- **Purpose**: Automatically formats Python code to ensure consistency
- **Configuration**: Line length of 100 characters
- **Usage**: `uv run black .`
- **Check only**: `uv run black --check .`

### isort - Import Sorter
- **Purpose**: Organizes and sorts import statements
- **Configuration**: Compatible with black profile
- **Usage**: `uv run isort .`
- **Check only**: `uv run isort --check-only .`

### Flake8 - Linter
- **Purpose**: Checks for code style issues and potential bugs
- **Plugins**:
  - `flake8-docstrings`: Ensures proper docstring formatting
  - `flake8-bugbear`: Finds common bugs and design problems
- **Configuration**: See `.flake8` file
- **Usage**: `uv run flake8 backend/ main.py`

### Mypy - Type Checker
- **Purpose**: Static type checking for Python
- **Configuration**: See `[tool.mypy]` in `pyproject.toml`
- **Usage**: `uv run mypy backend/ main.py`

## Quick Reference

### Before Committing

1. **Format your code:**
   ```bash
   ./scripts/format.sh
   ```

2. **Run quality checks:**
   ```bash
   ./scripts/quality.sh
   ```

### Common Commands

```bash
# Format code
uv run black .
uv run isort .

# Check formatting without modifying
uv run black --check .
uv run isort --check-only .

# Lint code
uv run flake8 backend/ main.py

# Type check
uv run mypy backend/ main.py

# Run tests with coverage
uv run pytest backend/tests/ -v --cov=backend
```

## Configuration Files

- **pyproject.toml**: Contains configuration for black, isort, and mypy
- **.flake8**: Configuration for flake8 linting
- **.pre-commit-config.yaml**: Pre-commit hooks configuration (optional)

## Code Style Guidelines

### Line Length
- Maximum line length: 100 characters
- Black will automatically enforce this

### Imports
- Organized in three groups: standard library, third-party, local
- Sorted alphabetically within each group
- isort handles this automatically

### Docstrings
- Use Google-style docstrings
- Required for all public modules, classes, and functions
- Example:
  ```python
  def function(arg1: str, arg2: int) -> bool:
      """Brief description of function.

      Args:
          arg1: Description of arg1
          arg2: Description of arg2

      Returns:
          Description of return value
      """
      pass
  ```

### Type Hints
- Use type hints for function signatures
- Not strictly enforced but encouraged
- Example:
  ```python
  def process_data(data: List[str]) -> Dict[str, int]:
      pass
  ```

## Ignoring Checks

### Flake8
To ignore specific errors on a line:
```python
# noqa: E501  # ignore line-too-long
```

### Mypy
To ignore type checking on a line:
```python
# type: ignore
```

### Black
Prevent black from formatting a section:
```python
# fmt: off
code_that_should_not_be_formatted()
# fmt: on
```

## Pre-commit Hooks

Optional but recommended for automatic quality checks:

```bash
pip install pre-commit
pre-commit install
```

This will run black, isort, and flake8 automatically before each commit.

## CI/CD Integration

The quality checks should be integrated into your CI/CD pipeline:

```yaml
# Example for GitHub Actions
- name: Run quality checks
  run: |
    uv sync --extra dev
    ./scripts/quality.sh
```

## Troubleshooting

### Black and Flake8 conflicts
- The configuration is set up to avoid conflicts
- E203 and W503 are ignored in flake8 for black compatibility

### Import sorting issues
- Make sure to run isort after black
- The `format.sh` script runs them in the correct order

### Type checking errors
- mypy is configured to be lenient (`ignore_missing_imports = true`)
- You can gradually increase strictness as the codebase matures

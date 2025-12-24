# Course Materials RAG System

A Retrieval-Augmented Generation (RAG) system designed to answer questions about course materials using semantic search and AI-powered responses.

## Overview

This application is a full-stack web application that enables users to query course materials and receive intelligent, context-aware responses. It uses ChromaDB for vector storage, Anthropic's Claude for AI generation, and provides a web interface for interaction.


## Prerequisites

- Python 3.13 or higher
- uv (Python package manager)
- An Anthropic API key (for Claude AI)
- **For Windows**: Use Git Bash to run the application commands - [Download Git for Windows](https://git-scm.com/downloads/win)

## Installation

1. **Install uv** (if not already installed)
   ```bash
   curl -LsSf https://astral.sh/uv/install.sh | sh
   ```

2. **Install Python dependencies**
   ```bash
   uv sync
   ```

3. **Set up environment variables**
   
   Create a `.env` file in the root directory:
   ```bash
   ANTHROPIC_API_KEY=your_anthropic_api_key_here
   ```

## Running the Application

### Quick Start

Use the provided shell script:
```bash
chmod +x run.sh
./run.sh
```

### Manual Start

```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

The application will be available at:
- Web Interface: `http://localhost:8000`
- API Documentation: `http://localhost:8000/docs`

## Development

### Code Quality Tools

This project uses several code quality tools to maintain consistency and catch issues early:

- **black**: Code formatter (line length: 100)
- **isort**: Import sorter (compatible with black)
- **flake8**: Linting tool with plugins for docstrings and bug detection
- **mypy**: Static type checker

### Installing Development Dependencies

```bash
uv sync --extra dev
```

### Running Code Quality Checks

**Format code automatically:**
```bash
./scripts/format.sh
# or manually:
uv run black .
uv run isort .
```

**Run linting:**
```bash
./scripts/lint.sh
# or manually:
uv run flake8 backend/ main.py
uv run mypy backend/ main.py
```

**Run all quality checks:**
```bash
./scripts/quality.sh
```

This will run:
1. Black formatting check
2. isort import sorting check
3. flake8 linting
4. mypy type checking
5. pytest with coverage

### Pre-commit Hooks (Optional)

To automatically run quality checks before each commit:

```bash
# Install pre-commit (if not using uv)
pip install pre-commit

# Install the git hooks
pre-commit install

# Run manually on all files
pre-commit run --all-files
```

### Running Tests

```bash
uv run pytest backend/tests/ -v --cov=backend --cov-report=term-missing
```


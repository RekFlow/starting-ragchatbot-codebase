# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Retrieval-Augmented Generation (RAG) system for querying course materials. It uses ChromaDB for vector storage, Anthropic's Claude Sonnet 4 for AI generation, and FastAPI for the backend API with a vanilla JavaScript frontend.

## Package Management

This project uses **uv** (not pip) for all Python operations:
- Install dependencies: `uv sync`
- Run Python files: `uv run python script.py`
- Add dependencies: `uv add package-name`
- Run the application: `cd backend && uv run uvicorn app:app --reload --port 8000`

## Running the Application

From the root directory:
```bash
cd backend
uv run uvicorn app:app --reload --port 8000
```

Or use the shell script from root:
```bash
./run.sh
```

The application will be available at:
- Web Interface: http://localhost:8000
- API Documentation: http://localhost:8000/docs

## Environment Setup

Required `.env` file in root directory:
```
ANTHROPIC_API_KEY=your_api_key_here
```

## Architecture Overview

### Request Flow
1. Frontend sends POST to `/api/query` with user question and optional session_id
2. FastAPI endpoint creates/retrieves session, calls RAGSystem.query()
3. RAGSystem orchestrates: gets conversation history → calls AIGenerator with tools
4. AIGenerator sends request to Claude API with CourseSearchTool available
5. Claude decides whether to use the search tool based on the query
6. If tool used: ToolManager executes search via VectorStore → returns results to Claude
7. Claude synthesizes final response from tool results and/or general knowledge
8. Response flows back through layers with sources from tool usage
9. Frontend displays answer with optional sources and updates session

### Core Components

**RAGSystem** (`rag_system.py`): Main orchestrator that coordinates all components
- Manages document loading from `../docs` folder (automatically on startup)
- Handles query flow: history retrieval → AI generation with tools → source tracking
- Provides course analytics (count and titles)

**VectorStore** (`vector_store.py`): ChromaDB wrapper with dual collection strategy
- **course_catalog**: Stores course titles/metadata for name resolution via semantic search
- **course_content**: Stores text chunks for semantic content retrieval
- Search flow: resolve course name (if provided) → build filter → search content
- Metadata: course_title, lesson_number, chunk_index for each chunk

**AIGenerator** (`ai_generator.py`): Anthropic Claude API interface
- Manages tool calling workflow with Claude Sonnet 4
- Handles conversation history (last N exchanges from SessionManager)
- System prompt defines Claude as course assistant with search capabilities

**ToolManager & CourseSearchTool** (`search_tools.py`): Tool-based search architecture
- CourseSearchTool: Defines search interface for Claude (query, course_name, lesson_number params)
- Claude decides when to search vs. use general knowledge
- ToolManager tracks sources for frontend display

**DocumentProcessor** (`document_processor.py`): Text processing and chunking
- Expected format: First 3 lines are course metadata (title, link, instructor)
- Lesson markers: "Lesson N: Title" (case-insensitive) with optional "Lesson Link:" on next line
- Chunking: Sentence-based with configurable size (800 chars) and overlap (100 chars)
- Context enhancement: Prepends "Course X Lesson Y content:" to chunks for better retrieval

**SessionManager** (`session_manager.py`): Conversation history per session
- Maintains last N message pairs (configurable via MAX_HISTORY in config)
- Enables follow-up questions with context

### Data Models (`models.py`)
- **Course**: title (unique ID), course_link, instructor, lessons[]
- **Lesson**: lesson_number, title, lesson_link
- **CourseChunk**: content, course_title, lesson_number, chunk_index

### Configuration (`config.py`)
Key settings loaded from environment:
- ANTHROPIC_MODEL: `claude-sonnet-4-20250514`
- EMBEDDING_MODEL: `all-MiniLM-L6-v2` (sentence-transformers)
- CHUNK_SIZE: 800 characters
- CHUNK_OVERLAP: 100 characters
- MAX_RESULTS: 5 search results
- MAX_HISTORY: 2 conversation exchanges
- CHROMA_PATH: `./chroma_db` (relative to backend/)

## Vector Database Schema

The vector database has two collections:

**course_catalog**:
- Stores course titles for name resolution
- Metadata: title, instructor, course_link, lesson_count, lessons_json (serialized list of lessons with lesson_number, lesson_title, lesson_link)

**course_content**:
- Stores text chunks for semantic search
- Metadata: course_title, lesson_number, chunk_index

## Document Format

Expected course document format:
```
Course Title: [title]
Course Link: [url]
Course Instructor: [name]

Lesson 0: [lesson title]
Lesson Link: [optional url]
[lesson content...]

Lesson 1: [next lesson title]
[content...]
```

Supported file types: .txt, .pdf, .docx

## API Endpoints

**POST /api/query**
- Request: `{ "query": string, "session_id": string (optional) }`
- Response: `{ "answer": string, "sources": string[], "session_id": string }`

**GET /api/courses**
- Response: `{ "total_courses": int, "course_titles": string[] }`

## Windows Development Note

This project is designed to work on Windows using Git Bash for running commands (not PowerShell). The README specifically mentions this requirement for proper command compatibility.

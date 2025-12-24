"""
Pytest configuration and shared fixtures for RAG chatbot tests.

This module provides:
- Sample data fixtures (courses, chunks, documents)
- Mock fixtures (ChromaDB, Anthropic API, SearchResults)
- Temporary directory fixtures
- Test configuration
"""

import sys
from pathlib import Path
from typing import List
from unittest.mock import MagicMock, Mock

import pytest

# Add backend to Python path for imports
backend_path = Path(__file__).parent.parent
sys.path.insert(0, str(backend_path))

from config import Config
from models import Course, CourseChunk, Lesson
from vector_store import SearchResults, VectorStore

# ============================================================================
# Pytest Configuration
# ============================================================================


def pytest_configure(config):
    """Configure pytest with custom markers"""
    config.addinivalue_line("markers", "unit: Unit tests (fast, isolated)")
    config.addinivalue_line(
        "markers", "integration: Integration tests (slower, use real components)"
    )
    config.addinivalue_line("markers", "slow: Slow tests that can be skipped")


@pytest.fixture(autouse=True)
def disable_chroma_telemetry(monkeypatch):
    """Automatically disable ChromaDB telemetry for all tests"""
    monkeypatch.setenv("ANONYMIZED_TELEMETRY", "False")


# ============================================================================
# Sample Data Fixtures
# ============================================================================


@pytest.fixture
def sample_course():
    """Basic course with 3 lessons for testing"""
    return Course(
        title="Introduction to RAG Systems",
        course_link="https://example.com/rag-course",
        instructor="John Doe",
        lessons=[
            Lesson(
                lesson_number=0, title="Introduction", lesson_link="https://example.com/lesson0"
            ),
            Lesson(
                lesson_number=1, title="Vector Stores", lesson_link="https://example.com/lesson1"
            ),
            Lesson(
                lesson_number=2,
                title="Retrieval Techniques",
                lesson_link="https://example.com/lesson2",
            ),
        ],
    )


@pytest.fixture
def sample_course_chunks(sample_course):
    """Pre-generated course chunks for testing"""
    return [
        CourseChunk(
            content="Lesson 0 content: RAG stands for Retrieval-Augmented Generation. It combines retrieval with generation.",
            course_title=sample_course.title,
            lesson_number=0,
            chunk_index=0,
        ),
        CourseChunk(
            content="Vector stores enable semantic search over documents using embeddings.",
            course_title=sample_course.title,
            lesson_number=1,
            chunk_index=1,
        ),
        CourseChunk(
            content="Retrieval techniques include dense retrieval, sparse retrieval, and hybrid approaches.",
            course_title=sample_course.title,
            lesson_number=2,
            chunk_index=2,
        ),
    ]


@pytest.fixture
def sample_course_document():
    """Sample course document text in expected format"""
    return """Course Title: Introduction to RAG Systems
Course Link: https://example.com/rag-course
Course Instructor: John Doe

Lesson 0: Introduction
Lesson Link: https://example.com/lesson0
RAG stands for Retrieval-Augmented Generation. It combines retrieval with generation to create more accurate and contextual responses. This approach leverages external knowledge bases.

Lesson 1: Vector Stores
Lesson Link: https://example.com/lesson1
Vector stores enable semantic search over documents using embeddings. They convert text into high-dimensional vectors that capture semantic meaning. This allows for similarity-based retrieval.

Lesson 2: Retrieval Techniques
Lesson Link: https://example.com/lesson2
Retrieval techniques include dense retrieval, sparse retrieval, and hybrid approaches. Dense retrieval uses neural embeddings, while sparse retrieval uses keyword matching. Hybrid methods combine both.
"""


@pytest.fixture
def another_course():
    """Another course for multi-course testing"""
    return Course(
        title="Advanced Machine Learning",
        course_link="https://example.com/ml-course",
        instructor="Jane Smith",
        lessons=[
            Lesson(
                lesson_number=0,
                title="Neural Networks",
                lesson_link="https://example.com/ml-lesson0",
            )
        ],
    )


# ============================================================================
# Temporary Directory Fixtures
# ============================================================================


@pytest.fixture
def temp_chroma_path(tmp_path):
    """Temporary ChromaDB directory that auto-cleans"""
    chroma_dir = tmp_path / "test_chroma"
    chroma_dir.mkdir()
    yield str(chroma_dir)
    # Cleanup happens automatically via tmp_path


@pytest.fixture
def test_config(tmp_path):
    """Test configuration with temporary paths"""
    config = Config()
    config.CHROMA_PATH = str(tmp_path / "chroma_db")
    config.ANTHROPIC_API_KEY = "test-api-key"
    config.MAX_RESULTS = 5
    config.CHUNK_SIZE = 800
    config.CHUNK_OVERLAP = 100
    config.MAX_HISTORY = 2
    return config


# ============================================================================
# Mock ChromaDB Fixtures
# ============================================================================


@pytest.fixture
def mock_chroma_collection():
    """Mock ChromaDB collection with controlled responses"""
    mock_collection = MagicMock()

    # Default query response (empty)
    mock_collection.query.return_value = {"documents": [[]], "metadatas": [[]], "distances": [[]]}

    # Default get response (empty)
    mock_collection.get.return_value = {"ids": [], "documents": [], "metadatas": []}

    return mock_collection


@pytest.fixture
def mock_chroma_client(mock_chroma_collection):
    """Mock ChromaDB client that returns mock collections"""
    mock_client = MagicMock()
    mock_client.get_or_create_collection.return_value = mock_chroma_collection
    return mock_client


@pytest.fixture
def mock_embedding_function():
    """Mock embedding function that returns deterministic vectors"""
    mock_func = MagicMock()
    # Return consistent 384-dimensional vectors (MiniLM default)
    mock_func.return_value = lambda texts: [[0.1 + i * 0.01] * 384 for i in range(len(texts))]
    return mock_func


# ============================================================================
# Mock SearchResults Fixtures
# ============================================================================


@pytest.fixture
def mock_search_results():
    """Mock successful search results"""
    return SearchResults(
        documents=[
            "RAG systems combine retrieval with generation.",
            "Vector stores enable semantic search.",
        ],
        metadata=[
            {"course_title": "Introduction to RAG Systems", "lesson_number": 0, "chunk_index": 0},
            {"course_title": "Introduction to RAG Systems", "lesson_number": 1, "chunk_index": 1},
        ],
        distances=[0.15, 0.25],
        error=None,
    )


@pytest.fixture
def mock_empty_search_results():
    """Mock empty search results"""
    return SearchResults.empty("No relevant content found.")


@pytest.fixture
def mock_error_search_results():
    """Mock search results with error"""
    return SearchResults.empty("Search error: connection failed")


# ============================================================================
# Mock Anthropic API Fixtures
# ============================================================================


@pytest.fixture
def mock_anthropic_client():
    """Mocked Anthropic client with basic text response"""
    mock_client = Mock()

    # Create mock response
    mock_response = Mock()
    mock_response.content = [Mock(text="This is a test response.", type="text")]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = Mock(input_tokens=100, output_tokens=50)

    mock_client.messages = Mock()
    mock_client.messages.create = Mock(return_value=mock_response)

    return mock_client


@pytest.fixture
def mock_anthropic_tool_use_response():
    """Mock response with tool use"""
    mock_response = Mock()

    # Create tool use block
    tool_use_block = Mock()
    tool_use_block.type = "tool_use"
    tool_use_block.id = "tool_123"
    tool_use_block.name = "search_course_content"
    tool_use_block.input = {"query": "RAG systems", "course_name": "Introduction"}

    mock_response.content = [tool_use_block]
    mock_response.stop_reason = "tool_use"
    mock_response.usage = Mock(input_tokens=100, output_tokens=30)

    return mock_response


@pytest.fixture
def mock_anthropic_final_response():
    """Mock final response after tool execution"""
    mock_response = Mock()
    mock_response.content = [
        Mock(
            text="Based on the search results, RAG stands for Retrieval-Augmented Generation.",
            type="text",
        )
    ]
    mock_response.stop_reason = "end_turn"
    mock_response.usage = Mock(input_tokens=200, output_tokens=60)

    return mock_response


@pytest.fixture
def mock_anthropic_outline_tool_response():
    """Mock response using the course outline tool"""
    mock_response = Mock()

    tool_use_block = Mock()
    tool_use_block.type = "tool_use"
    tool_use_block.id = "tool_456"
    tool_use_block.name = "get_course_outline"
    tool_use_block.input = {"course_name": "Introduction to RAG"}

    mock_response.content = [tool_use_block]
    mock_response.stop_reason = "tool_use"
    mock_response.usage = Mock(input_tokens=80, output_tokens=25)

    return mock_response


@pytest.fixture
def mock_anthropic_two_round_responses():
    """Mock responses for 2-round sequential tool calling"""
    # Round 1: Tool use (get_course_outline)
    tool_response_1 = Mock()
    tool_response_1.stop_reason = "tool_use"
    tool_response_1.content = [
        Mock(type="tool_use", id="tool_1", name="get_course_outline", input={"course_name": "RAG"})
    ]
    tool_response_1.usage = Mock(input_tokens=100, output_tokens=30)

    # Round 2: Tool use (search_course_content)
    tool_response_2 = Mock()
    tool_response_2.stop_reason = "tool_use"
    tool_response_2.content = [
        Mock(
            type="tool_use",
            id="tool_2",
            name="search_course_content",
            input={"query": "embeddings", "course_name": "RAG"},
        )
    ]
    tool_response_2.usage = Mock(input_tokens=150, output_tokens=35)

    # Final: Text response
    final_response = Mock()
    final_response.stop_reason = "end_turn"
    final_response.content = [Mock(text="Final answer synthesizing both results", type="text")]
    final_response.usage = Mock(input_tokens=200, output_tokens=60)

    return [tool_response_1, tool_response_2, final_response]


@pytest.fixture
def mock_anthropic_max_rounds_responses():
    """Mock responses for testing max rounds limit (3 tool uses, max 2 rounds)"""
    # Round 1: Tool use
    tool_response_1 = Mock()
    tool_response_1.stop_reason = "tool_use"
    tool_response_1.content = [
        Mock(type="tool_use", id="tool_1", name="search_course_content", input={"query": "test1"})
    ]

    # Round 2: Tool use
    tool_response_2 = Mock()
    tool_response_2.stop_reason = "tool_use"
    tool_response_2.content = [
        Mock(type="tool_use", id="tool_2", name="search_course_content", input={"query": "test2"})
    ]

    # Round 3: Tool use (should trigger max rounds limit)
    tool_response_3 = Mock()
    tool_response_3.stop_reason = "tool_use"
    tool_response_3.content = [
        Mock(type="tool_use", id="tool_3", name="search_course_content", input={"query": "test3"})
    ]

    # Forced final response (without tools)
    final_response = Mock()
    final_response.stop_reason = "end_turn"
    final_response.content = [Mock(text="Forced final answer after max rounds", type="text")]

    return [tool_response_1, tool_response_2, tool_response_3, final_response]


# ============================================================================
# Helper Fixtures
# ============================================================================


@pytest.fixture
def mock_vector_store(mock_chroma_client, temp_chroma_path):
    """VectorStore with mocked ChromaDB client"""
    from unittest.mock import patch

    with patch("chromadb.PersistentClient", return_value=mock_chroma_client):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            store = VectorStore(temp_chroma_path, "all-MiniLM-L6-v2", max_results=5)
            yield store


@pytest.fixture
def sample_chroma_query_response():
    """Sample ChromaDB query response structure"""
    return {
        "documents": [
            [
                "RAG systems combine retrieval with generation.",
                "Vector stores enable semantic search.",
            ]
        ],
        "metadatas": [
            [
                {
                    "course_title": "Introduction to RAG Systems",
                    "lesson_number": 0,
                    "chunk_index": 0,
                },
                {
                    "course_title": "Introduction to RAG Systems",
                    "lesson_number": 1,
                    "chunk_index": 1,
                },
            ]
        ],
        "distances": [[0.15, 0.25]],
        "ids": [["chunk_0", "chunk_1"]],
    }


@pytest.fixture
def sample_chroma_get_response(sample_course):
    """Sample ChromaDB get response for course catalog"""
    import json

    lessons_json = json.dumps(
        [
            {
                "lesson_number": lesson.lesson_number,
                "lesson_title": lesson.title,
                "lesson_link": lesson.lesson_link,
            }
            for lesson in sample_course.lessons
        ]
    )

    return {
        "ids": [sample_course.title],
        "documents": [sample_course.title],
        "metadatas": [
            {
                "title": sample_course.title,
                "instructor": sample_course.instructor,
                "course_link": sample_course.course_link,
                "lessons_json": lessons_json,
                "lesson_count": len(sample_course.lessons),
            }
        ],
    }


# ============================================================================
# FastAPI Test Fixtures
# ============================================================================

@pytest.fixture
def test_app():
    """Create a test FastAPI app without static file mounting"""
    from fastapi import FastAPI, HTTPException, Request
    from fastapi.middleware.cors import CORSMiddleware
    from pydantic import BaseModel
    from typing import List, Optional, Dict

    # Create test app
    app = FastAPI(title="Course Materials RAG System - Test", root_path="")

    # Add CORS middleware
    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_credentials=True,
        allow_methods=["*"],
        allow_headers=["*"],
    )

    # Pydantic models (same as in app.py)
    class QueryRequest(BaseModel):
        query: str
        session_id: Optional[str] = None

    class QueryResponse(BaseModel):
        answer: str
        sources: List[Dict[str, Optional[str]]]
        session_id: str

    class CourseStats(BaseModel):
        total_courses: int
        course_titles: List[str]

    @app.post("/api/query", response_model=QueryResponse)
    async def query_documents(request_body: QueryRequest, request: Request):
        """Process a query and return response with sources"""
        try:
            mock_rag = request.app.state.mock_rag
            session_id = request_body.session_id
            if not session_id:
                session_id = mock_rag.session_manager.create_session()

            answer, sources = mock_rag.query(request_body.query, session_id)

            return QueryResponse(
                answer=answer,
                sources=sources,
                session_id=session_id
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/api/courses", response_model=CourseStats)
    async def get_course_stats(request: Request):
        """Get course analytics and statistics"""
        try:
            mock_rag = request.app.state.mock_rag
            analytics = mock_rag.get_course_analytics()
            return CourseStats(
                total_courses=analytics["total_courses"],
                course_titles=analytics["course_titles"]
            )
        except Exception as e:
            raise HTTPException(status_code=500, detail=str(e))

    @app.get("/")
    async def root():
        """Root endpoint for health check"""
        return {"status": "ok", "message": "RAG System API"}

    # Initialize app state
    app.state.mock_rag = None

    return app


@pytest.fixture
def mock_rag_system(test_config):
    """Mock RAG system for API testing"""
    mock_rag = Mock()

    # Mock session manager
    mock_rag.session_manager = Mock()
    mock_rag.session_manager.create_session.return_value = "test-session-123"

    # Mock query method
    mock_rag.query.return_value = (
        "This is a test answer about RAG systems.",
        [
            {"text": "Source 1 text", "url": "https://example.com/lesson1"},
            {"text": "Source 2 text", "url": "https://example.com/lesson2"}
        ]
    )

    # Mock analytics method
    mock_rag.get_course_analytics.return_value = {
        "total_courses": 2,
        "course_titles": ["Introduction to RAG Systems", "Advanced Machine Learning"]
    }

    return mock_rag


@pytest.fixture
def api_client(test_app, mock_rag_system):
    """Create test client with mocked RAG system"""
    from fastapi.testclient import TestClient

    # Inject mock RAG system into app state
    test_app.state.mock_rag = mock_rag_system

    client = TestClient(test_app)
    yield client

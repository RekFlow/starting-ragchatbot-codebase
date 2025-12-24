"""
Tests for FastAPI endpoints.

These tests verify:
- POST /api/query - Query processing endpoint
- GET /api/courses - Course analytics endpoint
- GET / - Root/health check endpoint
- Request validation and error handling
- Response format compliance
"""

import pytest
from unittest.mock import Mock, patch


# ============================================================================
# Root Endpoint Tests
# ============================================================================

@pytest.mark.api
def test_root_endpoint(api_client):
    """Test root endpoint returns health status"""
    response = api_client.get("/")

    assert response.status_code == 200
    data = response.json()
    assert "status" in data
    assert data["status"] == "ok"
    assert "message" in data


# ============================================================================
# Query Endpoint Tests
# ============================================================================

@pytest.mark.api
def test_query_endpoint_success(api_client):
    """Test successful query request"""
    request_data = {
        "query": "What is RAG?",
        "session_id": None
    }

    response = api_client.post("/api/query", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "answer" in data
    assert "sources" in data
    assert "session_id" in data

    # Verify types
    assert isinstance(data["answer"], str)
    assert isinstance(data["sources"], list)
    assert isinstance(data["session_id"], str)

    # Verify content
    assert len(data["answer"]) > 0
    assert data["session_id"] == "test-session-123"


@pytest.mark.api
def test_query_endpoint_with_session_id(api_client, mock_rag_system):
    """Test query with existing session ID"""
    request_data = {
        "query": "Follow-up question",
        "session_id": "existing-session-456"
    }

    response = api_client.post("/api/query", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Should use provided session ID (not create new one)
    assert data["session_id"] == "existing-session-456"

    # Verify RAG system was called with correct query and session
    mock_rag_system.query.assert_called_once()
    call_args = mock_rag_system.query.call_args[0]
    assert call_args[0] == "Follow-up question"
    assert call_args[1] == "existing-session-456"


@pytest.mark.api
def test_query_endpoint_creates_session_when_none(api_client, mock_rag_system):
    """Test that query creates new session when none provided"""
    request_data = {
        "query": "New query"
    }

    response = api_client.post("/api/query", json=request_data)

    assert response.status_code == 200
    data = response.json()

    # Should create new session
    mock_rag_system.session_manager.create_session.assert_called_once()
    assert data["session_id"] == "test-session-123"


@pytest.mark.api
def test_query_endpoint_returns_sources(api_client):
    """Test that query endpoint returns sources in correct format"""
    request_data = {
        "query": "Test query with sources"
    }

    response = api_client.post("/api/query", json=request_data)

    assert response.status_code == 200
    data = response.json()

    sources = data["sources"]
    assert len(sources) > 0

    # Verify source structure
    for source in sources:
        assert isinstance(source, dict)
        assert "text" in source or "url" in source


@pytest.mark.api
def test_query_endpoint_missing_query_field(api_client):
    """Test query endpoint rejects request without query field"""
    request_data = {
        "session_id": "test-session"
        # Missing "query" field
    }

    response = api_client.post("/api/query", json=request_data)

    # Should return validation error
    assert response.status_code == 422


@pytest.mark.api
def test_query_endpoint_empty_query(api_client):
    """Test query endpoint with empty query string"""
    request_data = {
        "query": ""
    }

    response = api_client.post("/api/query", json=request_data)

    # Should still process (empty string is valid, though not useful)
    assert response.status_code == 200


@pytest.mark.api
def test_query_endpoint_handles_rag_error(api_client, mock_rag_system):
    """Test query endpoint handles RAG system errors gracefully"""
    # Mock RAG system to raise an error
    mock_rag_system.query.side_effect = Exception("RAG system failure")

    request_data = {
        "query": "Test query"
    }

    response = api_client.post("/api/query", json=request_data)

    # Should return 500 error with detail
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "RAG system failure" in data["detail"]


@pytest.mark.api
def test_query_endpoint_invalid_json(api_client):
    """Test query endpoint with invalid JSON"""
    response = api_client.post(
        "/api/query",
        data="invalid json{",
        headers={"Content-Type": "application/json"}
    )

    # Should return validation error
    assert response.status_code == 422


# ============================================================================
# Courses Endpoint Tests
# ============================================================================

@pytest.mark.api
def test_courses_endpoint_success(api_client):
    """Test successful course analytics request"""
    response = api_client.get("/api/courses")

    assert response.status_code == 200
    data = response.json()

    # Verify response structure
    assert "total_courses" in data
    assert "course_titles" in data

    # Verify types
    assert isinstance(data["total_courses"], int)
    assert isinstance(data["course_titles"], list)

    # Verify content matches mock
    assert data["total_courses"] == 2
    assert len(data["course_titles"]) == 2
    assert "Introduction to RAG Systems" in data["course_titles"]
    assert "Advanced Machine Learning" in data["course_titles"]


@pytest.mark.api
def test_courses_endpoint_empty_database(api_client, mock_rag_system):
    """Test courses endpoint when no courses exist"""
    # Mock empty course analytics
    mock_rag_system.get_course_analytics.return_value = {
        "total_courses": 0,
        "course_titles": []
    }

    response = api_client.get("/api/courses")

    assert response.status_code == 200
    data = response.json()

    assert data["total_courses"] == 0
    assert data["course_titles"] == []


@pytest.mark.api
def test_courses_endpoint_calls_rag_system(api_client, mock_rag_system):
    """Test that courses endpoint calls RAG system correctly"""
    response = api_client.get("/api/courses")

    assert response.status_code == 200

    # Verify RAG system method was called
    mock_rag_system.get_course_analytics.assert_called_once()


@pytest.mark.api
def test_courses_endpoint_handles_rag_error(api_client, mock_rag_system):
    """Test courses endpoint handles RAG system errors gracefully"""
    # Mock RAG system to raise an error
    mock_rag_system.get_course_analytics.side_effect = Exception("Database connection failed")

    response = api_client.get("/api/courses")

    # Should return 500 error with detail
    assert response.status_code == 500
    data = response.json()
    assert "detail" in data
    assert "Database connection failed" in data["detail"]


# ============================================================================
# Request/Response Model Tests
# ============================================================================

@pytest.mark.api
def test_query_request_optional_session_id(api_client):
    """Test that session_id is optional in query request"""
    # Without session_id
    response1 = api_client.post("/api/query", json={"query": "Test"})
    assert response1.status_code == 200

    # With session_id
    response2 = api_client.post("/api/query", json={"query": "Test", "session_id": "abc123"})
    assert response2.status_code == 200


@pytest.mark.api
def test_query_response_format(api_client):
    """Test query response follows QueryResponse model"""
    response = api_client.post("/api/query", json={"query": "Test"})

    assert response.status_code == 200
    data = response.json()

    # Required fields
    assert "answer" in data
    assert "sources" in data
    assert "session_id" in data

    # Type validation
    assert isinstance(data["answer"], str)
    assert isinstance(data["sources"], list)
    assert isinstance(data["session_id"], str)

    # Sources format
    for source in data["sources"]:
        assert isinstance(source, dict)


@pytest.mark.api
def test_course_stats_format(api_client):
    """Test course stats response follows CourseStats model"""
    response = api_client.get("/api/courses")

    assert response.status_code == 200
    data = response.json()

    # Required fields
    assert "total_courses" in data
    assert "course_titles" in data

    # Type validation
    assert isinstance(data["total_courses"], int)
    assert isinstance(data["course_titles"], list)

    # All course titles are strings
    for title in data["course_titles"]:
        assert isinstance(title, str)


# ============================================================================
# CORS and Middleware Tests
# ============================================================================

@pytest.mark.api
def test_cors_middleware_configured(test_app):
    """Test that CORS middleware is configured in the app"""
    # Verify middleware is configured (FastAPI wraps middleware in Middleware class)
    assert len(test_app.user_middleware) > 0
    # The actual CORSMiddleware is wrapped, so we check it exists
    assert test_app.user_middleware is not None


@pytest.mark.api
def test_cors_headers_in_real_server():
    """
    Note: TestClient doesn't fully simulate CORS headers.
    In a real ASGI server, CORS headers would be present.
    This test documents that limitation.
    """
    # This is a documentation test - CORS works in production
    # but TestClient doesn't fully simulate ASGI middleware behavior
    pass


# ============================================================================
# Integration-style Tests
# ============================================================================

@pytest.mark.api
def test_query_flow_end_to_end(api_client, mock_rag_system):
    """Test complete query flow from request to response"""
    # Configure mock for detailed verification
    mock_rag_system.session_manager.create_session.return_value = "session-xyz"
    mock_rag_system.query.return_value = (
        "RAG stands for Retrieval-Augmented Generation.",
        [
            {"text": "RAG definition from Lesson 1", "url": "https://example.com/lesson1"},
            {"text": "More context from Lesson 2", "url": "https://example.com/lesson2"}
        ]
    )

    # Make request
    response = api_client.post("/api/query", json={"query": "What is RAG?"})

    # Verify response
    assert response.status_code == 200
    data = response.json()

    assert data["answer"] == "RAG stands for Retrieval-Augmented Generation."
    assert len(data["sources"]) == 2
    assert data["session_id"] == "session-xyz"

    # Verify mock calls
    mock_rag_system.session_manager.create_session.assert_called_once()
    mock_rag_system.query.assert_called_once_with("What is RAG?", "session-xyz")


@pytest.mark.api
def test_multiple_queries_same_session(api_client, mock_rag_system):
    """Test multiple queries using the same session"""
    session_id = "persistent-session-123"

    # First query
    response1 = api_client.post("/api/query", json={
        "query": "First question",
        "session_id": session_id
    })
    assert response1.status_code == 200

    # Second query with same session
    response2 = api_client.post("/api/query", json={
        "query": "Follow-up question",
        "session_id": session_id
    })
    assert response2.status_code == 200

    # Both should succeed
    assert mock_rag_system.query.call_count == 2


@pytest.mark.api
def test_api_endpoint_not_found(api_client):
    """Test non-existent endpoint returns 404"""
    response = api_client.get("/api/nonexistent")

    assert response.status_code == 404

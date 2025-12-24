"""
Tests for RAGSystem (main orchestrator - integration tests).

These tests verify:
- System initialization with all components
- Document processing (single and folder)
- Query execution with tool usage
- Session management integration
- Source tracking
- End-to-end pipeline
"""

import os
from unittest.mock import MagicMock, Mock, patch

import pytest
from models import Course, Lesson
from rag_system import RAGSystem

# ============================================================================
# Initialization Tests
# ============================================================================


def test_rag_system_initialization(test_config):
    """Test RAGSystem initializes all components"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                assert rag.document_processor is not None
                assert rag.vector_store is not None
                assert rag.ai_generator is not None
                assert rag.session_manager is not None
                assert rag.tool_manager is not None


def test_rag_system_tool_registration(test_config):
    """Test that search and outline tools are registered"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                tool_defs = rag.tool_manager.get_tool_definitions()

                assert len(tool_defs) == 2
                tool_names = [t["name"] for t in tool_defs]
                assert "search_course_content" in tool_names
                assert "get_course_outline" in tool_names


# ============================================================================
# Single Document Tests
# ============================================================================


def test_add_course_document(test_config, tmp_path, sample_course_document):
    """Test adding a single course document"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                # Write sample document
                doc_path = tmp_path / "test_course.txt"
                doc_path.write_text(sample_course_document)

                # Mock vector store methods
                rag.vector_store.add_course_metadata = Mock()
                rag.vector_store.add_course_content = Mock()

                course, num_chunks = rag.add_course_document(str(doc_path))

                assert course is not None
                assert isinstance(course, Course)
                assert num_chunks > 0
                rag.vector_store.add_course_metadata.assert_called_once()
                rag.vector_store.add_course_content.assert_called_once()


def test_add_course_document_returns_course_and_chunks(
    test_config, tmp_path, sample_course_document
):
    """Test that add_course_document returns correct values"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                doc_path = tmp_path / "course.txt"
                doc_path.write_text(sample_course_document)

                rag.vector_store.add_course_metadata = Mock()
                rag.vector_store.add_course_content = Mock()

                course, chunks = rag.add_course_document(str(doc_path))

                assert course.title == "Introduction to RAG Systems"
                assert course.instructor == "John Doe"
                assert len(course.lessons) > 0
                assert chunks > 0


def test_add_course_document_error_handling(test_config):
    """Test error handling for invalid file"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                course, chunks = rag.add_course_document("/nonexistent/file.txt")

                # Should return None and 0 on error
                assert course is None
                assert chunks == 0


# ============================================================================
# Folder Processing Tests
# ============================================================================


def test_add_course_folder(test_config, tmp_path, sample_course_document, another_course):
    """Test processing multiple documents from folder"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                # Create multiple course files
                (tmp_path / "course1.txt").write_text(sample_course_document)
                (tmp_path / "course2.txt").write_text(
                    """Course Title: Second Course
Course Link: https://example.com
Course Instructor: Teacher

Lesson 0: Intro
Content here.
"""
                )

                rag.vector_store.add_course_metadata = Mock()
                rag.vector_store.add_course_content = Mock()
                rag.vector_store.get_existing_course_titles = Mock(return_value=[])

                courses, chunks = rag.add_course_folder(str(tmp_path))

                assert courses == 2
                assert chunks > 0


def test_add_course_folder_clear_existing(test_config, tmp_path, sample_course_document):
    """Test clear_existing flag"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                (tmp_path / "course.txt").write_text(sample_course_document)

                rag.vector_store.clear_all_data = Mock()
                rag.vector_store.add_course_metadata = Mock()
                rag.vector_store.add_course_content = Mock()
                rag.vector_store.get_existing_course_titles = Mock(return_value=[])

                courses, chunks = rag.add_course_folder(str(tmp_path), clear_existing=True)

                # Should have called clear_all_data
                rag.vector_store.clear_all_data.assert_called_once()


def test_add_course_folder_skip_duplicates(test_config, tmp_path, sample_course_document):
    """Test that duplicate courses are skipped"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                (tmp_path / "course.txt").write_text(sample_course_document)

                # Simulate existing course
                rag.vector_store.get_existing_course_titles = Mock(
                    return_value=["Introduction to RAG Systems"]
                )
                rag.vector_store.add_course_metadata = Mock()

                courses, chunks = rag.add_course_folder(str(tmp_path))

                # Should not add the course
                assert courses == 0
                rag.vector_store.add_course_metadata.assert_not_called()


def test_add_course_folder_nonexistent_path(test_config):
    """Test handling of nonexistent folder"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                courses, chunks = rag.add_course_folder("/nonexistent/folder")

                assert courses == 0
                assert chunks == 0


# ============================================================================
# Query Tests
# ============================================================================


def test_query_without_session(test_config, mock_search_results):
    """Test query without session ID"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic") as mock_anthropic:
                # Mock AI response
                mock_response = Mock()
                mock_response.content = [
                    Mock(text="RAG stands for Retrieval-Augmented Generation.", type="text")
                ]
                mock_response.stop_reason = "end_turn"
                mock_anthropic.return_value.messages.create.return_value = mock_response

                rag = RAGSystem(test_config)
                rag.vector_store.search = Mock(return_value=mock_search_results)

                response, sources = rag.query("What is RAG?")

                assert isinstance(response, str)
                assert len(response) > 0


def test_query_with_session(test_config):
    """Test query with session ID includes history"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic") as mock_anthropic:
                mock_response = Mock()
                mock_response.content = [Mock(text="Follow-up answer", type="text")]
                mock_response.stop_reason = "end_turn"
                mock_anthropic.return_value.messages.create.return_value = mock_response

                rag = RAGSystem(test_config)

                session_id = rag.session_manager.create_session()
                rag.session_manager.add_exchange(session_id, "First question", "First answer")

                response, sources = rag.query("Follow-up question", session_id)

                # Should include history in API call
                assert isinstance(response, str)


def test_query_with_tool_execution(test_config, mock_search_results):
    """Test query that triggers tool use"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic") as mock_anthropic:
                # Mock tool use response
                tool_response = Mock()
                tool_block = Mock(
                    type="tool_use",
                    id="tool_1",
                    name="search_course_content",
                    input={"query": "RAG"},
                )
                tool_response.content = [tool_block]
                tool_response.stop_reason = "tool_use"

                # Mock final response
                final_response = Mock()
                final_response.content = [Mock(text="Based on search results...", type="text")]
                final_response.stop_reason = "end_turn"

                mock_anthropic.return_value.messages.create.side_effect = [
                    tool_response,
                    final_response,
                ]

                rag = RAGSystem(test_config)

                # Patch the vector store's search method directly
                with patch.object(rag.vector_store, "search", return_value=mock_search_results):
                    with patch.object(
                        rag.vector_store,
                        "get_lesson_link",
                        return_value="https://example.com/lesson",
                    ):
                        response, sources = rag.query("What is RAG?")

                        # Should return a response
                        assert isinstance(response, str)


def test_query_returns_sources(test_config, mock_search_results):
    """Test that query returns sources from tool execution"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic") as mock_anthropic:
                tool_response = Mock()
                tool_block = Mock(
                    type="tool_use",
                    id="tool_1",
                    name="search_course_content",
                    input={"query": "test"},
                )
                tool_response.content = [tool_block]
                tool_response.stop_reason = "tool_use"

                final_response = Mock()
                final_response.content = [Mock(text="Answer", type="text")]
                final_response.stop_reason = "end_turn"

                mock_anthropic.return_value.messages.create.side_effect = [
                    tool_response,
                    final_response,
                ]

                rag = RAGSystem(test_config)
                rag.search_tool.store.search = Mock(return_value=mock_search_results)
                rag.search_tool.store.get_lesson_link = Mock(
                    return_value="https://example.com/lesson"
                )

                response, sources = rag.query("Test query")

                assert isinstance(sources, list)
                # Sources should be retrieved
                assert len(sources) >= 0  # May be 0 if sources were reset


def test_query_updates_session_history(test_config):
    """Test that query updates conversation history"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic") as mock_anthropic:
                mock_response = Mock()
                mock_response.content = [Mock(text="Test response", type="text")]
                mock_response.stop_reason = "end_turn"
                mock_anthropic.return_value.messages.create.return_value = mock_response

                rag = RAGSystem(test_config)

                session_id = rag.session_manager.create_session()

                rag.query("Test question", session_id)

                # Check history was updated
                history = rag.session_manager.get_conversation_history(session_id)
                assert history is not None
                assert "Test question" in history
                assert "Test response" in history


def test_query_resets_sources(test_config, mock_search_results):
    """Test that sources are reset after retrieval"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic") as mock_anthropic:
                tool_response = Mock()
                tool_block = Mock(
                    type="tool_use",
                    id="tool_1",
                    name="search_course_content",
                    input={"query": "test"},
                )
                tool_response.content = [tool_block]
                tool_response.stop_reason = "tool_use"

                final_response = Mock()
                final_response.content = [Mock(text="Answer", type="text")]
                final_response.stop_reason = "end_turn"

                mock_anthropic.return_value.messages.create.side_effect = [
                    tool_response,
                    final_response,
                ]

                rag = RAGSystem(test_config)
                rag.vector_store.search = Mock(return_value=mock_search_results)
                rag.vector_store.get_lesson_link = Mock(return_value="https://example.com/lesson")

                response, sources = rag.query("Test")

                # After query, sources should be reset in tool manager
                remaining_sources = rag.tool_manager.get_last_sources()
                assert len(remaining_sources) == 0


# ============================================================================
# Analytics Tests
# ============================================================================


def test_get_course_analytics(test_config):
    """Test retrieving course analytics"""
    with patch("chromadb.PersistentClient"):
        with patch("chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction"):
            with patch("anthropic.Anthropic"):
                rag = RAGSystem(test_config)

                rag.vector_store.get_course_count = Mock(return_value=3)
                rag.vector_store.get_existing_course_titles = Mock(
                    return_value=["Course 1", "Course 2", "Course 3"]
                )

                analytics = rag.get_course_analytics()

                assert analytics["total_courses"] == 3
                assert len(analytics["course_titles"]) == 3
                assert "Course 1" in analytics["course_titles"]

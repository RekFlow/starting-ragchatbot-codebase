"""
Tests for search tools (CourseSearchTool, CourseOutlineTool, ToolManager).

These tests verify:
- Tool definition schemas
- Tool execution with various parameters
- Result formatting
- Source tracking
- Error handling
- Tool registration and management
"""

import pytest
from unittest.mock import Mock, MagicMock
from search_tools import CourseSearchTool, CourseOutlineTool, ToolManager, Tool
from vector_store import SearchResults, VectorStore


# ============================================================================
# CourseSearchTool Tests
# ============================================================================

def test_course_search_tool_definition():
    """Test CourseSearchTool returns correct tool definition"""
    mock_store = Mock(spec=VectorStore)
    tool = CourseSearchTool(mock_store)

    definition = tool.get_tool_definition()

    assert definition["name"] == "search_course_content"
    assert "description" in definition
    assert "input_schema" in definition
    assert definition["input_schema"]["type"] == "object"
    assert "query" in definition["input_schema"]["properties"]
    assert "query" in definition["input_schema"]["required"]


def test_course_search_tool_required_params():
    """Test that query is required parameter"""
    mock_store = Mock(spec=VectorStore)
    tool = CourseSearchTool(mock_store)

    definition = tool.get_tool_definition()

    assert "required" in definition["input_schema"]
    assert "query" in definition["input_schema"]["required"]
    # course_name and lesson_number should be optional
    assert "course_name" not in definition["input_schema"]["required"]
    assert "lesson_number" not in definition["input_schema"]["required"]


def test_course_search_tool_execute_basic(mock_search_results):
    """Test execute with query only"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson0"

    tool = CourseSearchTool(mock_store)
    result = tool.execute(query="RAG systems")

    mock_store.search.assert_called_once_with(
        query="RAG systems",
        course_name=None,
        lesson_number=None
    )
    assert "RAG systems" in result or "Introduction to RAG Systems" in result


def test_course_search_tool_execute_with_course_filter(mock_search_results):
    """Test execute with course_name filter"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson0"

    tool = CourseSearchTool(mock_store)
    result = tool.execute(query="vector stores", course_name="Introduction")

    mock_store.search.assert_called_once_with(
        query="vector stores",
        course_name="Introduction",
        lesson_number=None
    )
    assert isinstance(result, str)


def test_course_search_tool_execute_with_lesson_filter(mock_search_results):
    """Test execute with lesson_number filter"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson1"

    tool = CourseSearchTool(mock_store)
    result = tool.execute(query="retrieval", lesson_number=1)

    mock_store.search.assert_called_once_with(
        query="retrieval",
        course_name=None,
        lesson_number=1
    )


def test_course_search_tool_execute_with_both_filters(mock_search_results):
    """Test execute with both course_name and lesson_number"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson2"

    tool = CourseSearchTool(mock_store)
    result = tool.execute(query="embeddings", course_name="RAG Course", lesson_number=2)

    mock_store.search.assert_called_once_with(
        query="embeddings",
        course_name="RAG Course",
        lesson_number=2
    )


def test_course_search_tool_execute_empty_results():
    """Test execute with no results"""
    mock_store = Mock(spec=VectorStore)
    empty_results = SearchResults(documents=[], metadata=[], distances=[], error=None)
    mock_store.search.return_value = empty_results

    tool = CourseSearchTool(mock_store)
    result = tool.execute(query="nonexistent topic")

    assert "No relevant content found" in result


def test_course_search_tool_execute_error_results():
    """Test execute when search returns error"""
    mock_store = Mock(spec=VectorStore)
    error_results = SearchResults.empty("Search error: connection failed")
    mock_store.search.return_value = error_results

    tool = CourseSearchTool(mock_store)
    result = tool.execute(query="test query")

    assert "Search error: connection failed" in result


def test_course_search_tool_formats_results_with_headers(mock_search_results):
    """Test that results are formatted with course and lesson headers"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson0"

    tool = CourseSearchTool(mock_store)
    result = tool.execute(query="test")

    # Should include course title in formatted output
    assert "Introduction to RAG Systems" in result
    # Should include lesson information
    assert "Lesson" in result


def test_course_search_tool_tracks_sources(mock_search_results):
    """Test that tool tracks sources in last_sources"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson0"

    tool = CourseSearchTool(mock_store)
    tool.execute(query="test")

    assert len(tool.last_sources) > 0
    assert all('text' in source for source in tool.last_sources)
    assert all('url' in source for source in tool.last_sources)


def test_course_search_tool_retrieves_lesson_links(mock_search_results):
    """Test that tool retrieves lesson links from vector store"""
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/test-lesson"

    tool = CourseSearchTool(mock_store)
    tool.execute(query="test")

    # Should have called get_lesson_link for each result
    assert mock_store.get_lesson_link.called
    # Check sources include URLs
    assert any(source['url'] == "https://example.com/test-lesson" for source in tool.last_sources)


def test_course_search_tool_empty_results_no_sources():
    """Test that empty results don't create sources"""
    mock_store = Mock(spec=VectorStore)
    empty_results = SearchResults(documents=[], metadata=[], distances=[], error=None)
    mock_store.search.return_value = empty_results

    tool = CourseSearchTool(mock_store)
    tool.execute(query="test")

    assert len(tool.last_sources) == 0


# ============================================================================
# CourseOutlineTool Tests
# ============================================================================

def test_course_outline_tool_definition():
    """Test CourseOutlineTool returns correct definition"""
    mock_store = Mock(spec=VectorStore)
    tool = CourseOutlineTool(mock_store)

    definition = tool.get_tool_definition()

    assert definition["name"] == "get_course_outline"
    assert "description" in definition
    assert "input_schema" in definition
    assert "course_name" in definition["input_schema"]["properties"]
    assert "course_name" in definition["input_schema"]["required"]


def test_course_outline_tool_execute_found():
    """Test execute when course outline is found"""
    mock_store = Mock(spec=VectorStore)
    mock_outline = {
        'course_title': 'Test Course',
        'course_link': 'https://example.com/course',
        'instructor': 'John Doe',
        'lessons': [
            {'lesson_number': 0, 'lesson_title': 'Intro'},
            {'lesson_number': 1, 'lesson_title': 'Advanced'}
        ]
    }
    mock_store.get_course_outline.return_value = mock_outline

    tool = CourseOutlineTool(mock_store)
    result = tool.execute(course_name="Test Course")

    mock_store.get_course_outline.assert_called_once_with("Test Course")
    assert "Test Course" in result
    assert "John Doe" in result
    assert "Intro" in result
    assert "Advanced" in result


def test_course_outline_tool_execute_not_found():
    """Test execute when course is not found"""
    mock_store = Mock(spec=VectorStore)
    mock_store.get_course_outline.return_value = None

    tool = CourseOutlineTool(mock_store)
    result = tool.execute(course_name="Nonexistent Course")

    assert "No course found matching 'Nonexistent Course'" in result


def test_course_outline_tool_execute_partial_match():
    """Test execute with partial course name (semantic matching)"""
    mock_store = Mock(spec=VectorStore)
    mock_outline = {
        'course_title': 'Introduction to Machine Learning',
        'course_link': 'https://example.com/ml',
        'instructor': 'Jane Smith',
        'lessons': [
            {'lesson_number': 0, 'lesson_title': 'Basics'}
        ]
    }
    mock_store.get_course_outline.return_value = mock_outline

    tool = CourseOutlineTool(mock_store)
    result = tool.execute(course_name="ML")  # Partial name

    # Should still find and format the course
    assert "Introduction to Machine Learning" in result
    assert "Jane Smith" in result


def test_course_outline_tool_format_complete():
    """Test formatting with all fields present"""
    mock_store = Mock(spec=VectorStore)
    mock_outline = {
        'course_title': 'Complete Course',
        'course_link': 'https://example.com/complete',
        'instructor': 'Dr. Complete',
        'lessons': [
            {'lesson_number': 0, 'lesson_title': 'Lesson Zero'},
            {'lesson_number': 1, 'lesson_title': 'Lesson One'},
            {'lesson_number': 2, 'lesson_title': 'Lesson Two'}
        ]
    }
    mock_store.get_course_outline.return_value = mock_outline

    tool = CourseOutlineTool(mock_store)
    result = tool.execute(course_name="Complete")

    assert "Course: Complete Course" in result
    assert "Course Link: https://example.com/complete" in result
    assert "Instructor: Dr. Complete" in result
    assert "Lesson 0: Lesson Zero" in result
    assert "Lesson 1: Lesson One" in result
    assert "Lesson 2: Lesson Two" in result
    assert "3 total" in result


def test_course_outline_tool_format_no_lessons():
    """Test formatting when course has no lessons"""
    mock_store = Mock(spec=VectorStore)
    mock_outline = {
        'course_title': 'No Lessons Course',
        'course_link': 'https://example.com/course',
        'instructor': 'Teacher',
        'lessons': []
    }
    mock_store.get_course_outline.return_value = mock_outline

    tool = CourseOutlineTool(mock_store)
    result = tool.execute(course_name="No Lessons")

    assert "No Lessons Course" in result
    assert "No lessons found" in result


def test_course_outline_tool_format_missing_optional_fields():
    """Test formatting when optional fields are missing"""
    mock_store = Mock(spec=VectorStore)
    mock_outline = {
        'course_title': 'Minimal Course',
        'lessons': [
            {'lesson_number': 0, 'lesson_title': 'Only Lesson'}
        ]
    }
    # Missing course_link and instructor
    mock_store.get_course_outline.return_value = mock_outline

    tool = CourseOutlineTool(mock_store)
    result = tool.execute(course_name="Minimal")

    assert "Course: Minimal Course" in result
    assert "Only Lesson" in result
    # Should not include missing fields


# ============================================================================
# ToolManager Tests
# ============================================================================

def test_tool_manager_register_tool():
    """Test registering a single tool"""
    manager = ToolManager()
    mock_store = Mock(spec=VectorStore)
    tool = CourseSearchTool(mock_store)

    manager.register_tool(tool)

    assert "search_course_content" in manager.tools


def test_tool_manager_register_multiple_tools():
    """Test registering multiple tools"""
    manager = ToolManager()
    mock_store = Mock(spec=VectorStore)

    search_tool = CourseSearchTool(mock_store)
    outline_tool = CourseOutlineTool(mock_store)

    manager.register_tool(search_tool)
    manager.register_tool(outline_tool)

    assert "search_course_content" in manager.tools
    assert "get_course_outline" in manager.tools
    assert len(manager.tools) == 2


def test_tool_manager_get_tool_definitions():
    """Test getting all tool definitions"""
    manager = ToolManager()
    mock_store = Mock(spec=VectorStore)

    manager.register_tool(CourseSearchTool(mock_store))
    manager.register_tool(CourseOutlineTool(mock_store))

    definitions = manager.get_tool_definitions()

    assert len(definitions) == 2
    assert all('name' in defn for defn in definitions)
    assert any(defn['name'] == 'search_course_content' for defn in definitions)
    assert any(defn['name'] == 'get_course_outline' for defn in definitions)


def test_tool_manager_get_tool_definitions_empty():
    """Test getting definitions when no tools registered"""
    manager = ToolManager()

    definitions = manager.get_tool_definitions()

    assert definitions == []


def test_tool_manager_execute_tool(mock_search_results):
    """Test executing a tool by name"""
    manager = ToolManager()
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson"

    manager.register_tool(CourseSearchTool(mock_store))

    result = manager.execute_tool("search_course_content", query="test")

    assert isinstance(result, str)
    mock_store.search.assert_called_once()


def test_tool_manager_execute_tool_not_found():
    """Test executing non-existent tool"""
    manager = ToolManager()

    result = manager.execute_tool("nonexistent_tool", query="test")

    assert "Tool 'nonexistent_tool' not found" in result


def test_tool_manager_execute_tool_with_kwargs(mock_search_results):
    """Test executing tool with multiple keyword arguments"""
    manager = ToolManager()
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = None

    manager.register_tool(CourseSearchTool(mock_store))

    result = manager.execute_tool(
        "search_course_content",
        query="embeddings",
        course_name="ML Course",
        lesson_number=3
    )

    mock_store.search.assert_called_once_with(
        query="embeddings",
        course_name="ML Course",
        lesson_number=3
    )


def test_tool_manager_get_last_sources(mock_search_results):
    """Test retrieving sources from last search"""
    manager = ToolManager()
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson"

    manager.register_tool(CourseSearchTool(mock_store))
    manager.execute_tool("search_course_content", query="test")

    sources = manager.get_last_sources()

    assert len(sources) > 0


def test_tool_manager_get_last_sources_empty():
    """Test getting sources when no searches performed"""
    manager = ToolManager()

    sources = manager.get_last_sources()

    assert sources == []


def test_tool_manager_reset_sources(mock_search_results):
    """Test resetting sources"""
    manager = ToolManager()
    mock_store = Mock(spec=VectorStore)
    mock_store.search.return_value = mock_search_results
    mock_store.get_lesson_link.return_value = "https://example.com/lesson"

    manager.register_tool(CourseSearchTool(mock_store))
    manager.execute_tool("search_course_content", query="test")

    assert len(manager.get_last_sources()) > 0

    manager.reset_sources()

    assert len(manager.get_last_sources()) == 0

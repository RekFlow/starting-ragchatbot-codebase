"""
Tests for VectorStore (ChromaDB vector storage and search).

These tests verify:
- Initialization and collection creation
- Course metadata storage and retrieval
- Course content storage
- Search with filters
- Course name resolution
- Course outline retrieval
- SearchResults handling
- Data management
"""

import pytest
from unittest.mock import Mock, MagicMock, patch, call
from vector_store import VectorStore, SearchResults
from models import Course, Lesson, CourseChunk


# ============================================================================
# Initialization Tests
# ============================================================================

@patch('chromadb.PersistentClient')
@patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction')
def test_vector_store_initialization(mock_embedding, mock_client, temp_chroma_path):
    """Test VectorStore initialization creates collections"""
    mock_collection = MagicMock()
    mock_client.return_value.get_or_create_collection.return_value = mock_collection

    store = VectorStore(temp_chroma_path, "all-MiniLM-L6-v2", max_results=5)

    assert store.max_results == 5
    # Should create two collections
    assert mock_client.return_value.get_or_create_collection.call_count == 2


@patch('chromadb.PersistentClient')
@patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction')
def test_vector_store_with_custom_max_results(mock_embedding, mock_client, temp_chroma_path):
    """Test configuration of max_results"""
    mock_client.return_value.get_or_create_collection.return_value = MagicMock()

    store = VectorStore(temp_chroma_path, "model", max_results=10)

    assert store.max_results == 10


# ============================================================================
# Course Metadata Tests
# ============================================================================

def test_add_course_metadata(mock_vector_store, sample_course):
    """Test adding course metadata to catalog"""
    mock_vector_store.course_catalog.add = MagicMock()

    mock_vector_store.add_course_metadata(sample_course)

    mock_vector_store.course_catalog.add.assert_called_once()
    call_args = mock_vector_store.course_catalog.add.call_args

    # Verify course title is used as document and ID
    assert sample_course.title in call_args[1]['documents']
    assert sample_course.title in call_args[1]['ids']


def test_add_course_metadata_with_lessons(mock_vector_store, sample_course):
    """Test that lesson metadata is serialized as JSON"""
    import json
    mock_vector_store.course_catalog.add = MagicMock()

    mock_vector_store.add_course_metadata(sample_course)

    call_args = mock_vector_store.course_catalog.add.call_args
    metadata = call_args[1]['metadatas'][0]

    # Should have lessons_json field
    assert 'lessons_json' in metadata
    # Should be valid JSON
    lessons = json.loads(metadata['lessons_json'])
    assert len(lessons) == len(sample_course.lessons)
    assert lessons[0]['lesson_number'] == 0


def test_get_existing_course_titles(mock_vector_store):
    """Test retrieving stored course titles"""
    mock_vector_store.course_catalog.get.return_value = {
        'ids': ['Course 1', 'Course 2', 'Course 3']
    }

    titles = mock_vector_store.get_existing_course_titles()

    assert len(titles) == 3
    assert 'Course 1' in titles


def test_get_course_count(mock_vector_store):
    """Test counting courses in catalog"""
    mock_vector_store.course_catalog.get.return_value = {
        'ids': ['Course 1', 'Course 2']
    }

    count = mock_vector_store.get_course_count()

    assert count == 2


def test_get_all_courses_metadata(mock_vector_store, sample_chroma_get_response):
    """Test retrieving and parsing all course metadata"""
    mock_vector_store.course_catalog.get.return_value = sample_chroma_get_response

    metadata_list = mock_vector_store.get_all_courses_metadata()

    assert len(metadata_list) > 0
    assert 'lessons' in metadata_list[0]
    assert isinstance(metadata_list[0]['lessons'], list)
    # lessons_json should be removed
    assert 'lessons_json' not in metadata_list[0]


def test_get_course_link(mock_vector_store):
    """Test retrieving course URL"""
    mock_vector_store.course_catalog.get.return_value = {
        'metadatas': [{'course_link': 'https://example.com/course'}]
    }

    link = mock_vector_store.get_course_link("Test Course")

    assert link == "https://example.com/course"


def test_get_lesson_link(mock_vector_store):
    """Test retrieving lesson URL"""
    import json
    lessons_json = json.dumps([
        {'lesson_number': 0, 'lesson_title': 'Intro', 'lesson_link': 'https://example.com/l0'},
        {'lesson_number': 1, 'lesson_title': 'Advanced', 'lesson_link': 'https://example.com/l1'}
    ])

    mock_vector_store.course_catalog.get.return_value = {
        'metadatas': [{'lessons_json': lessons_json}]
    }

    link = mock_vector_store.get_lesson_link("Test Course", 1)

    assert link == "https://example.com/l1"


def test_get_course_link_nonexistent(mock_vector_store):
    """Test getting link for nonexistent course"""
    mock_vector_store.course_catalog.get.return_value = {'metadatas': []}

    link = mock_vector_store.get_course_link("Nonexistent")

    assert link is None


# ============================================================================
# Course Content Tests
# ============================================================================

def test_add_course_content(mock_vector_store, sample_course_chunks):
    """Test adding course content chunks"""
    mock_vector_store.course_content.add = MagicMock()

    mock_vector_store.add_course_content(sample_course_chunks)

    mock_vector_store.course_content.add.assert_called_once()
    call_args = mock_vector_store.course_content.add.call_args

    assert len(call_args[1]['documents']) == len(sample_course_chunks)
    assert len(call_args[1]['metadatas']) == len(sample_course_chunks)
    assert len(call_args[1]['ids']) == len(sample_course_chunks)


def test_add_course_content_unique_ids(mock_vector_store, sample_course_chunks):
    """Test that chunk IDs are unique"""
    mock_vector_store.course_content.add = MagicMock()

    mock_vector_store.add_course_content(sample_course_chunks)

    call_args = mock_vector_store.course_content.add.call_args
    ids = call_args[1]['ids']

    # All IDs should be unique
    assert len(ids) == len(set(ids))


def test_add_course_content_empty_list(mock_vector_store):
    """Test adding empty chunk list"""
    mock_vector_store.course_content.add = MagicMock()

    mock_vector_store.add_course_content([])

    # Should not call add
    mock_vector_store.course_content.add.assert_not_called()


# ============================================================================
# Search Tests
# ============================================================================

def test_search_basic(mock_vector_store, sample_chroma_query_response):
    """Test basic search without filters"""
    mock_vector_store.course_content.query.return_value = sample_chroma_query_response

    results = mock_vector_store.search("RAG systems")

    mock_vector_store.course_content.query.assert_called_once()
    assert len(results.documents) > 0
    assert results.error is None


def test_search_with_course_filter(temp_chroma_path, sample_chroma_query_response):
    """Test search with course name filter"""
    with patch('chromadb.PersistentClient') as mock_client_class:
        with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
            mock_catalog = MagicMock()
            mock_content = MagicMock()

            # Mock course resolution
            mock_catalog.query.return_value = {
                'documents': [['Test Course']],
                'metadatas': [[{'title': 'Test Course'}]]
            }
            mock_content.query.return_value = sample_chroma_query_response

            mock_client = MagicMock()
            mock_client.get_or_create_collection.side_effect = [mock_catalog, mock_content]
            mock_client_class.return_value = mock_client

            store = VectorStore(temp_chroma_path, "model", max_results=5)

            results = store.search("test query", course_name="Test")

            # Should query course content with filter
            call_args = mock_content.query.call_args
            assert call_args[1]['where'] == {'course_title': 'Test Course'}


def test_search_with_lesson_filter(mock_vector_store, sample_chroma_query_response):
    """Test search with lesson number filter"""
    mock_vector_store.course_content.query.return_value = sample_chroma_query_response

    results = mock_vector_store.search("test query", lesson_number=2)

    call_args = mock_vector_store.course_content.query.call_args
    assert call_args[1]['where'] == {'lesson_number': 2}


def test_search_with_both_filters(temp_chroma_path, sample_chroma_query_response):
    """Test search with both course and lesson filters"""
    with patch('chromadb.PersistentClient') as mock_client_class:
        with patch('chromadb.utils.embedding_functions.SentenceTransformerEmbeddingFunction'):
            mock_catalog = MagicMock()
            mock_content = MagicMock()

            mock_catalog.query.return_value = {
                'documents': [['Course']],
                'metadatas': [[{'title': 'Course'}]]
            }
            mock_content.query.return_value = sample_chroma_query_response

            mock_client = MagicMock()
            mock_client.get_or_create_collection.side_effect = [mock_catalog, mock_content]
            mock_client_class.return_value = mock_client

            store = VectorStore(temp_chroma_path, "model", max_results=5)

            results = store.search("query", course_name="Course", lesson_number=1)

            call_args = mock_content.query.call_args
            expected_filter = {
                '$and': [
                    {'course_title': 'Course'},
                    {'lesson_number': 1}
                ]
            }
            assert call_args[1]['where'] == expected_filter


def test_search_with_limit(mock_vector_store, sample_chroma_query_response):
    """Test search with custom result limit"""
    mock_vector_store.course_content.query.return_value = sample_chroma_query_response

    results = mock_vector_store.search("query", limit=3)

    call_args = mock_vector_store.course_content.query.call_args
    assert call_args[1]['n_results'] == 3


def test_search_nonexistent_course_returns_error(mock_vector_store):
    """Test search with invalid course name"""
    # Mock course resolution failure
    mock_vector_store.course_catalog.query.return_value = {
        'documents': [[]],
        'metadatas': [[]]
    }

    results = mock_vector_store.search("query", course_name="Nonexistent")

    assert results.error is not None
    assert "No course found" in results.error
    assert results.is_empty()


def test_search_empty_results(mock_vector_store):
    """Test search that returns no results"""
    mock_vector_store.course_content.query.return_value = {
        'documents': [[]],
        'metadatas': [[]],
        'distances': [[]]
    }

    results = mock_vector_store.search("obscure query")

    assert len(results.documents) == 0
    assert results.is_empty()


def test_search_exception_handling(mock_vector_store):
    """Test search handles ChromaDB exceptions"""
    mock_vector_store.course_content.query.side_effect = Exception("Connection failed")

    results = mock_vector_store.search("query")

    assert results.error is not None
    assert "Search error" in results.error
    assert results.is_empty()


# ============================================================================
# Course Resolution Tests
# ============================================================================

def test_resolve_course_name_exact_match(mock_vector_store):
    """Test exact course name matching"""
    mock_vector_store.course_catalog.query.return_value = {
        'documents': [['Exact Course Title']],
        'metadatas': [[{'title': 'Exact Course Title'}]]
    }

    title = mock_vector_store._resolve_course_name("Exact Course Title")

    assert title == "Exact Course Title"


def test_resolve_course_name_semantic_match(mock_vector_store):
    """Test semantic/partial course name matching"""
    mock_vector_store.course_catalog.query.return_value = {
        'documents': [['Introduction to Machine Learning']],
        'metadatas': [[{'title': 'Introduction to Machine Learning'}]]
    }

    title = mock_vector_store._resolve_course_name("ML course")

    assert title == "Introduction to Machine Learning"


def test_resolve_course_name_no_match(mock_vector_store):
    """Test course resolution when no match found"""
    mock_vector_store.course_catalog.query.return_value = {
        'documents': [[]],
        'metadatas': [[]]
    }

    title = mock_vector_store._resolve_course_name("Nonexistent")

    assert title is None


# ============================================================================
# Filter Building Tests
# ============================================================================

def test_build_filter_no_params(mock_vector_store):
    """Test filter building with no parameters"""
    filter_dict = mock_vector_store._build_filter(None, None)

    assert filter_dict is None


def test_build_filter_course_only(mock_vector_store):
    """Test filter with only course title"""
    filter_dict = mock_vector_store._build_filter("Test Course", None)

    assert filter_dict == {'course_title': 'Test Course'}


def test_build_filter_lesson_only(mock_vector_store):
    """Test filter with only lesson number"""
    filter_dict = mock_vector_store._build_filter(None, 3)

    assert filter_dict == {'lesson_number': 3}


def test_build_filter_both(mock_vector_store):
    """Test filter with both course and lesson"""
    filter_dict = mock_vector_store._build_filter("Course", 2)

    assert '$and' in filter_dict
    assert {'course_title': 'Course'} in filter_dict['$and']
    assert {'lesson_number': 2} in filter_dict['$and']


# ============================================================================
# Course Outline Tests
# ============================================================================

def test_get_course_outline_found(mock_vector_store):
    """Test successful course outline retrieval"""
    import json
    lessons_json = json.dumps([
        {'lesson_number': 0, 'lesson_title': 'Intro', 'lesson_link': 'https://example.com/l0'}
    ])

    mock_vector_store.course_catalog.query.return_value = {
        'documents': [['Test Course']],
        'metadatas': [[{
            'title': 'Test Course',
            'course_link': 'https://example.com/course',
            'instructor': 'Teacher',
            'lessons_json': lessons_json
        }]]
    }

    outline = mock_vector_store.get_course_outline("Test")

    assert outline is not None
    assert outline['course_title'] == 'Test Course'
    assert outline['instructor'] == 'Teacher'
    assert len(outline['lessons']) == 1


def test_get_course_outline_with_lessons(mock_vector_store):
    """Test outline includes parsed lesson data"""
    import json
    lessons_json = json.dumps([
        {'lesson_number': 0, 'lesson_title': 'First'},
        {'lesson_number': 1, 'lesson_title': 'Second'}
    ])

    mock_vector_store.course_catalog.query.return_value = {
        'documents': [['Course']],
        'metadatas': [[{'title': 'Course', 'lessons_json': lessons_json}]]
    }

    outline = mock_vector_store.get_course_outline("Course")

    assert len(outline['lessons']) == 2
    assert outline['lessons'][0]['lesson_title'] == 'First'
    assert outline['lessons'][1]['lesson_number'] == 1


def test_get_course_outline_not_found(mock_vector_store):
    """Test outline retrieval when course doesn't exist"""
    mock_vector_store.course_catalog.query.return_value = {
        'documents': [[]],
        'metadatas': [[]]
    }

    outline = mock_vector_store.get_course_outline("Nonexistent")

    assert outline is None


def test_get_course_outline_partial_name(mock_vector_store):
    """Test semantic matching for outline retrieval"""
    import json
    mock_vector_store.course_catalog.query.return_value = {
        'documents': [['Full Course Name']],
        'metadatas': [[{
            'title': 'Full Course Name',
            'lessons_json': json.dumps([])
        }]]
    }

    outline = mock_vector_store.get_course_outline("Partial")

    assert outline is not None
    assert outline['course_title'] == 'Full Course Name'


# ============================================================================
# SearchResults Tests
# ============================================================================

def test_search_results_from_chroma():
    """Test SearchResults factory from ChromaDB response"""
    chroma_response = {
        'documents': [['doc1', 'doc2']],
        'metadatas': [[{'key': 'val1'}, {'key': 'val2'}]],
        'distances': [[0.1, 0.2]]
    }

    results = SearchResults.from_chroma(chroma_response)

    assert len(results.documents) == 2
    assert len(results.metadata) == 2
    assert len(results.distances) == 2
    assert results.error is None


def test_search_results_empty():
    """Test empty SearchResults factory"""
    results = SearchResults.empty("Test error message")

    assert len(results.documents) == 0
    assert results.error == "Test error message"
    assert results.is_empty()


def test_search_results_is_empty_check():
    """Test is_empty() method"""
    empty = SearchResults(documents=[], metadata=[], distances=[])
    not_empty = SearchResults(documents=['doc'], metadata=[{}], distances=[0.1])

    assert empty.is_empty()
    assert not not_empty.is_empty()


# ============================================================================
# Data Management Tests
# ============================================================================

def test_clear_all_data(mock_vector_store):
    """Test clearing all data from collections"""
    mock_vector_store.client.delete_collection = MagicMock()
    mock_vector_store.client.get_or_create_collection = MagicMock(return_value=MagicMock())

    mock_vector_store.clear_all_data()

    # Should delete both collections
    assert mock_vector_store.client.delete_collection.call_count == 2


def test_clear_all_data_recreates_collections(mock_vector_store):
    """Test that collections are recreated after clearing"""
    mock_new_collection = MagicMock()
    mock_vector_store.client.delete_collection = MagicMock()
    mock_vector_store.client.get_or_create_collection = MagicMock(return_value=mock_new_collection)

    mock_vector_store.clear_all_data()

    # Should recreate collections
    assert mock_vector_store.client.get_or_create_collection.call_count == 2
    assert mock_vector_store.course_catalog == mock_new_collection
    assert mock_vector_store.course_content == mock_new_collection

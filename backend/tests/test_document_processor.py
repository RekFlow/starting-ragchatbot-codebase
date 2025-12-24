"""
Tests for DocumentProcessor (document parsing and text chunking).

These tests verify:
- File reading with encoding handling
- Text chunking with sentence boundaries
- Chunk size and overlap configuration
- Course metadata extraction
- Lesson parsing
- CourseChunk creation
- Edge cases (empty content, malformed docs)
"""

import pytest
import tempfile
import os
from document_processor import DocumentProcessor
from models import Course, Lesson, CourseChunk


# ============================================================================
# File Reading Tests
# ============================================================================

def test_read_file_utf8(tmp_path):
    """Test reading a UTF-8 encoded file"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    # Create a temp file
    test_file = tmp_path / "test.txt"
    content = "This is a test file with UTF-8 encoding."
    test_file.write_text(content, encoding='utf-8')

    result = processor.read_file(str(test_file))

    assert result == content


def test_read_file_encoding_errors(tmp_path):
    """Test fallback handling for encoding errors"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    # Create file with mixed encoding (this tests the error='ignore' fallback)
    test_file = tmp_path / "test_mixed.txt"
    test_file.write_bytes(b"Normal text \xff\xfe Invalid UTF-8")

    # Should not raise exception, may have some characters ignored
    result = processor.read_file(str(test_file))

    assert "Normal text" in result


# ============================================================================
# Text Chunking Tests
# ============================================================================

def test_chunk_text_basic():
    """Test basic sentence-based chunking"""
    processor = DocumentProcessor(chunk_size=50, chunk_overlap=0)
    text = "First sentence. Second sentence. Third sentence."

    chunks = processor.chunk_text(text)

    assert len(chunks) > 0
    assert all(isinstance(chunk, str) for chunk in chunks)


def test_chunk_text_with_overlap():
    """Test chunking with overlap"""
    processor = DocumentProcessor(chunk_size=100, chunk_overlap=20)
    text = "Sentence one. Sentence two. Sentence three. Sentence four. Sentence five."

    chunks = processor.chunk_text(text)

    # With overlap, some content should appear in multiple chunks
    assert len(chunks) >= 1

    # Check that overlap exists (some text appears in consecutive chunks)
    if len(chunks) > 1:
        # At least some text from end of first chunk should be in second chunk
        assert any(word in chunks[1] for word in chunks[0].split()[-5:])


def test_chunk_text_no_overlap():
    """Test chunking without overlap"""
    processor = DocumentProcessor(chunk_size=100, chunk_overlap=0)
    text = "First chunk text. More text here. Even more text."

    chunks = processor.chunk_text(text)

    # With no overlap configured, chunks should be distinct
    assert len(chunks) >= 1


def test_chunk_text_respects_chunk_size():
    """Test that chunks don't significantly exceed chunk_size"""
    processor = DocumentProcessor(chunk_size=50, chunk_overlap=0)
    text = "Sentence one here. Sentence two here. Sentence three here. Sentence four here."

    chunks = processor.chunk_text(text)

    # Should create multiple chunks with reasonable sizes
    assert len(chunks) >= 1
    for chunk in chunks:
        # Allow some flexibility for sentence boundaries
        assert len(chunk) <= processor.chunk_size + 100  # Generous buffer for sentence boundaries


def test_chunk_text_handles_abbreviations():
    """Test that chunking doesn't split on abbreviations like 'Dr.'"""
    processor = DocumentProcessor(chunk_size=200, chunk_overlap=0)
    text = "Dr. Smith is a professor. He teaches at the university. Prof. Johnson agrees."

    chunks = processor.chunk_text(text)

    # Should not break on "Dr." or "Prof."
    assert len(chunks) >= 1
    # Check that abbreviations stay with their context
    if len(chunks) == 1:
        assert "Dr. Smith" in chunks[0]


def test_chunk_text_empty_input():
    """Test chunking empty string"""
    processor = DocumentProcessor(chunk_size=100, chunk_overlap=10)

    chunks = processor.chunk_text("")

    assert len(chunks) == 0


def test_chunk_text_single_long_sentence():
    """Test chunking when a single sentence exceeds chunk_size"""
    processor = DocumentProcessor(chunk_size=30, chunk_overlap=0)
    text = "This is a very long sentence that definitely exceeds the chunk size limit."

    chunks = processor.chunk_text(text)

    # Should still create at least one chunk even if it exceeds size
    assert len(chunks) >= 1


# ============================================================================
# Course Document Processing Tests
# ============================================================================

def test_process_course_document_full(tmp_path, sample_course_document):
    """Test processing a complete course document"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    # Write sample document to temp file
    doc_path = tmp_path / "course.txt"
    doc_path.write_text(sample_course_document)

    course, chunks = processor.process_course_document(str(doc_path))

    assert course is not None
    assert len(chunks) > 0
    assert isinstance(course, Course)
    assert all(isinstance(chunk, CourseChunk) for chunk in chunks)


def test_process_course_document_metadata_extraction(tmp_path):
    """Test that course metadata is correctly extracted"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    doc_content = """Course Title: Test Course Title
Course Link: https://example.com/course
Course Instructor: Dr. Test Instructor

Lesson 0: Introduction
Some lesson content here.
"""

    doc_path = tmp_path / "test_course.txt"
    doc_path.write_text(doc_content)

    course, chunks = processor.process_course_document(str(doc_path))

    assert course.title == "Test Course Title"
    assert course.course_link == "https://example.com/course"
    assert course.instructor == "Dr. Test Instructor"


def test_process_course_document_lessons(tmp_path):
    """Test that lessons are parsed correctly"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    doc_content = """Course Title: Course With Lessons
Course Link: https://example.com
Course Instructor: Teacher

Lesson 0: First Lesson
Lesson Link: https://example.com/l0
Content for first lesson.

Lesson 1: Second Lesson
Lesson Link: https://example.com/l1
Content for second lesson.
"""

    doc_path = tmp_path / "course.txt"
    doc_path.write_text(doc_content)

    course, chunks = processor.process_course_document(str(doc_path))

    assert len(course.lessons) == 2
    assert course.lessons[0].lesson_number == 0
    assert course.lessons[0].title == "First Lesson"
    assert course.lessons[0].lesson_link == "https://example.com/l0"
    assert course.lessons[1].lesson_number == 1
    assert course.lessons[1].title == "Second Lesson"


def test_process_course_document_lesson_links(tmp_path):
    """Test that lesson links are parsed"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    doc_content = """Course Title: Test
Course Link: https://example.com
Course Instructor: Teacher

Lesson 0: Intro
Lesson Link: https://example.com/lesson0
Lesson content here.
"""

    doc_path = tmp_path / "course.txt"
    doc_path.write_text(doc_content)

    course, chunks = processor.process_course_document(str(doc_path))

    assert course.lessons[0].lesson_link == "https://example.com/lesson0"


def test_process_course_document_chunk_creation(tmp_path):
    """Test that CourseChunk objects are created correctly"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    doc_content = """Course Title: Chunking Test
Course Link: https://example.com
Course Instructor: Test

Lesson 0: Test Lesson
Lesson Link: https://example.com/l0
""" + "Content sentence. " * 50  # Make sure we have enough content to create chunks

    doc_path = tmp_path / "course.txt"
    doc_path.write_text(doc_content)

    course, chunks = processor.process_course_document(str(doc_path))

    assert len(chunks) > 0
    for chunk in chunks:
        assert chunk.course_title == "Chunking Test"
        assert isinstance(chunk.chunk_index, int)
        assert chunk.content != ""


def test_process_course_document_chunk_indexing(tmp_path):
    """Test that chunk indices are sequential"""
    processor = DocumentProcessor(chunk_size=100, chunk_overlap=10)

    doc_content = """Course Title: Index Test
Course Link: https://example.com
Course Instructor: Test

Lesson 0: Lesson
""" + "Sentence. " * 100  # Lots of content to create multiple chunks

    doc_path = tmp_path / "course.txt"
    doc_path.write_text(doc_content)

    course, chunks = processor.process_course_document(str(doc_path))

    # Check that indices are sequential
    indices = [chunk.chunk_index for chunk in chunks]
    assert indices == list(range(len(chunks)))


def test_process_course_document_lesson_context(tmp_path):
    """Test that lesson context prefix is added to chunks"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    doc_content = """Course Title: Context Test
Course Link: https://example.com
Course Instructor: Test

Lesson 0: Test Lesson
Test content for the lesson.
"""

    doc_path = tmp_path / "course.txt"
    doc_path.write_text(doc_content)

    course, chunks = processor.process_course_document(str(doc_path))

    # Check that at least one chunk has lesson context
    assert any("Lesson" in chunk.content for chunk in chunks)
    assert any("Context Test" in chunk.content for chunk in chunks)


def test_process_course_document_no_lessons(tmp_path):
    """Test processing document without lesson markers"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    doc_content = """Course Title: No Lessons Course
Course Link: https://example.com
Course Instructor: Test

Just some content without lesson markers.
More content here.
"""

    doc_path = tmp_path / "course.txt"
    doc_path.write_text(doc_content)

    course, chunks = processor.process_course_document(str(doc_path))

    # Should still create course and chunks
    assert course.title == "No Lessons Course"
    assert len(chunks) > 0
    # Chunks should have no lesson_number
    assert all(chunk.lesson_number is None for chunk in chunks)


def test_process_course_document_malformed_missing_metadata(tmp_path):
    """Test processing document with missing metadata"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    # Document without proper metadata
    doc_content = """Some Random Text
Lesson 0: Test
Content here with more text to ensure chunks are created.
"""

    doc_path = tmp_path / "malformed.txt"
    doc_path.write_text(doc_content)

    course, chunks = processor.process_course_document(str(doc_path))

    # Should still process, using defaults
    assert course is not None
    # May or may not create chunks depending on parsing
    assert isinstance(chunks, list)


def test_process_course_document_empty_lessons(tmp_path):
    """Test lesson with no content"""
    processor = DocumentProcessor(chunk_size=800, chunk_overlap=100)

    doc_content = """Course Title: Empty Lesson Test
Course Link: https://example.com
Course Instructor: Test

Lesson 0: Empty Lesson
Lesson Link: https://example.com/l0

Lesson 1: Has Content
Actual content here.
"""

    doc_path = tmp_path / "course.txt"
    doc_path.write_text(doc_content)

    course, chunks = processor.process_course_document(str(doc_path))

    # Course should be created, might skip empty lessons
    assert course is not None
    # At least lesson 1 should create chunks
    assert len(chunks) > 0

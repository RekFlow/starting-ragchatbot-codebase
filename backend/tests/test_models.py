"""
Tests for Pydantic models (Course, Lesson, CourseChunk).

These tests verify:
- Model creation and validation
- Optional fields handling
- Type checking and constraints
"""

import pytest
from models import Course, CourseChunk, Lesson
from pydantic import ValidationError

# ============================================================================
# Lesson Model Tests
# ============================================================================


def test_lesson_creation():
    """Test creating a valid Lesson"""
    lesson = Lesson(
        lesson_number=1, title="Introduction to Testing", lesson_link="https://example.com/lesson1"
    )

    assert lesson.lesson_number == 1
    assert lesson.title == "Introduction to Testing"
    assert lesson.lesson_link == "https://example.com/lesson1"


def test_lesson_optional_link():
    """Test Lesson without optional lesson_link"""
    lesson = Lesson(lesson_number=2, title="Advanced Topics")

    assert lesson.lesson_number == 2
    assert lesson.title == "Advanced Topics"
    assert lesson.lesson_link is None


def test_lesson_validation_errors():
    """Test Lesson validation with invalid types"""
    with pytest.raises(ValidationError):
        Lesson(lesson_number="not_a_number", title="Test")  # Should be int

    with pytest.raises(ValidationError):
        Lesson(lesson_number=1, title=123)  # Should be string


# ============================================================================
# Course Model Tests
# ============================================================================


def test_course_creation():
    """Test creating a valid Course with lessons"""
    lessons = [
        Lesson(lesson_number=0, title="Intro", lesson_link="https://example.com/l0"),
        Lesson(lesson_number=1, title="Basics", lesson_link="https://example.com/l1"),
    ]

    course = Course(
        title="Test Course",
        course_link="https://example.com/course",
        instructor="Test Instructor",
        lessons=lessons,
    )

    assert course.title == "Test Course"
    assert course.course_link == "https://example.com/course"
    assert course.instructor == "Test Instructor"
    assert len(course.lessons) == 2
    assert course.lessons[0].title == "Intro"
    assert course.lessons[1].lesson_number == 1


def test_course_optional_fields():
    """Test Course without optional course_link and instructor"""
    course = Course(title="Minimal Course")

    assert course.title == "Minimal Course"
    assert course.course_link is None
    assert course.instructor is None
    assert course.lessons == []


def test_course_empty_lessons():
    """Test Course with empty lessons list"""
    course = Course(
        title="Course Without Lessons", course_link="https://example.com/course", lessons=[]
    )

    assert course.title == "Course Without Lessons"
    assert len(course.lessons) == 0


def test_course_validation():
    """Test Course validation with invalid types"""
    with pytest.raises(ValidationError):
        Course(title=12345)  # Should be string

    with pytest.raises(ValidationError):
        Course(title="Valid Title", lessons="not_a_list")  # Should be List[Lesson]


# ============================================================================
# CourseChunk Model Tests
# ============================================================================


def test_course_chunk_creation():
    """Test creating a valid CourseChunk"""
    chunk = CourseChunk(
        content="This is sample course content about RAG systems.",
        course_title="Introduction to RAG",
        lesson_number=1,
        chunk_index=5,
    )

    assert chunk.content == "This is sample course content about RAG systems."
    assert chunk.course_title == "Introduction to RAG"
    assert chunk.lesson_number == 1
    assert chunk.chunk_index == 5


def test_course_chunk_optional_lesson_number():
    """Test CourseChunk without optional lesson_number"""
    chunk = CourseChunk(
        content="General course content not tied to a specific lesson.",
        course_title="General Course",
        chunk_index=0,
    )

    assert chunk.content == "General course content not tied to a specific lesson."
    assert chunk.course_title == "General Course"
    assert chunk.lesson_number is None
    assert chunk.chunk_index == 0


def test_course_chunk_validation():
    """Test CourseChunk validation with invalid fields"""
    with pytest.raises(ValidationError):
        CourseChunk(content=123, course_title="Test", chunk_index=0)  # Should be string

    with pytest.raises(ValidationError):
        CourseChunk(
            content="Valid content", course_title="Test", chunk_index="not_an_int"  # Should be int
        )

    with pytest.raises(ValidationError):
        CourseChunk(
            content="Valid content",
            course_title="Test",
            lesson_number="not_an_int",  # Should be int or None
            chunk_index=0,
        )

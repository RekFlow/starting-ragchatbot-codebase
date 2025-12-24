"""
Tests for SessionManager (conversation history management).

These tests verify:
- Session creation with unique IDs
- Message addition (user/assistant)
- Exchange addition (Q&A pairs)
- History limit enforcement
- Conversation history formatting
- Session clearing
"""

import pytest
from session_manager import Message, SessionManager

# ============================================================================
# Session Creation Tests
# ============================================================================


def test_create_session_returns_id():
    """Test that creating a session returns a session ID"""
    manager = SessionManager()
    session_id = manager.create_session()

    assert session_id is not None
    assert isinstance(session_id, str)
    assert session_id.startswith("session_")


def test_create_multiple_sessions_unique_ids():
    """Test that multiple sessions get unique IDs"""
    manager = SessionManager()
    session1 = manager.create_session()
    session2 = manager.create_session()
    session3 = manager.create_session()

    assert session1 != session2
    assert session2 != session3
    assert session1 != session3


# ============================================================================
# Message Management Tests
# ============================================================================


def test_add_message():
    """Test adding a single message to history"""
    manager = SessionManager()
    session_id = manager.create_session()

    manager.add_message(session_id, "user", "Hello!")

    assert session_id in manager.sessions
    assert len(manager.sessions[session_id]) == 1
    assert manager.sessions[session_id][0].role == "user"
    assert manager.sessions[session_id][0].content == "Hello!"


def test_add_message_creates_session_if_not_exists():
    """Test that adding a message auto-creates session"""
    manager = SessionManager()
    new_session_id = "test_session_123"

    manager.add_message(new_session_id, "user", "Test message")

    assert new_session_id in manager.sessions
    assert len(manager.sessions[new_session_id]) == 1


def test_add_exchange():
    """Test adding a complete Q&A exchange"""
    manager = SessionManager()
    session_id = manager.create_session()

    manager.add_exchange(
        session_id, "What is RAG?", "RAG stands for Retrieval-Augmented Generation."
    )

    assert len(manager.sessions[session_id]) == 2
    assert manager.sessions[session_id][0].role == "user"
    assert manager.sessions[session_id][0].content == "What is RAG?"
    assert manager.sessions[session_id][1].role == "assistant"
    assert (
        manager.sessions[session_id][1].content == "RAG stands for Retrieval-Augmented Generation."
    )


# ============================================================================
# History Limit Tests
# ============================================================================


def test_history_limit_truncation():
    """Test that history is truncated when exceeding max_history"""
    manager = SessionManager(max_history=2)  # 2 exchanges = 4 messages max
    session_id = manager.create_session()

    # Add 3 exchanges (6 messages total)
    manager.add_exchange(session_id, "Question 1", "Answer 1")
    manager.add_exchange(session_id, "Question 2", "Answer 2")
    manager.add_exchange(session_id, "Question 3", "Answer 3")

    # Should only keep last 2 exchanges (4 messages)
    assert len(manager.sessions[session_id]) == 4
    # First exchange should be removed
    messages = manager.sessions[session_id]
    assert messages[0].content == "Question 2"
    assert messages[1].content == "Answer 2"
    assert messages[2].content == "Question 3"
    assert messages[3].content == "Answer 3"


def test_history_preserves_recent_messages():
    """Test that recent messages are preserved when truncating"""
    manager = SessionManager(max_history=1)  # 1 exchange = 2 messages max
    session_id = manager.create_session()

    manager.add_message(session_id, "user", "Old message 1")
    manager.add_message(session_id, "assistant", "Old response 1")
    manager.add_message(session_id, "user", "Recent message")

    # Should keep last 2 messages
    assert len(manager.sessions[session_id]) == 2
    assert manager.sessions[session_id][0].content == "Old response 1"
    assert manager.sessions[session_id][1].content == "Recent message"


# ============================================================================
# History Retrieval Tests
# ============================================================================


def test_get_conversation_history_formatting():
    """Test conversation history formatting"""
    manager = SessionManager()
    session_id = manager.create_session()

    manager.add_exchange(session_id, "What is a vector?", "A vector is a mathematical object.")

    history = manager.get_conversation_history(session_id)

    assert history is not None
    assert "User: What is a vector?" in history
    assert "Assistant: A vector is a mathematical object." in history


def test_get_conversation_history_empty():
    """Test getting history from empty session returns None"""
    manager = SessionManager()
    session_id = manager.create_session()

    history = manager.get_conversation_history(session_id)

    assert history is None


def test_get_conversation_history_nonexistent_session():
    """Test getting history from nonexistent session returns None"""
    manager = SessionManager()

    history = manager.get_conversation_history("nonexistent_session")

    assert history is None


def test_get_conversation_history_none_session_id():
    """Test getting history with None session_id returns None"""
    manager = SessionManager()

    history = manager.get_conversation_history(None)

    assert history is None


# ============================================================================
# Session Clearing Tests
# ============================================================================


def test_clear_session():
    """Test clearing a session empties message list"""
    manager = SessionManager()
    session_id = manager.create_session()

    manager.add_exchange(session_id, "Question", "Answer")
    assert len(manager.sessions[session_id]) == 2

    manager.clear_session(session_id)

    assert session_id in manager.sessions
    assert len(manager.sessions[session_id]) == 0


def test_clear_nonexistent_session_no_error():
    """Test clearing nonexistent session doesn't raise error"""
    manager = SessionManager()

    # Should not raise exception
    manager.clear_session("nonexistent_session")

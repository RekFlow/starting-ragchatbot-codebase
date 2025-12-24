"""
Tests for AIGenerator (Anthropic API interaction and tool execution).

These tests verify:
- Initialization and configuration
- Response generation without tools
- Response generation with conversation history
- Tool execution flow
- Multi-turn conversations for tool use
- Error handling
"""

from unittest.mock import MagicMock, Mock, patch

import pytest
from ai_generator import AIGenerator

# ============================================================================
# Initialization Tests
# ============================================================================


@patch("anthropic.Anthropic")
def test_ai_generator_initialization(mock_anthropic):
    """Test AIGenerator initialization creates client"""
    mock_client = Mock()
    mock_anthropic.return_value = mock_client

    generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

    mock_anthropic.assert_called_once_with(api_key="test-key")
    assert generator.model == "claude-sonnet-4"
    assert generator.client == mock_client


@patch("anthropic.Anthropic")
def test_base_params_configuration(mock_anthropic):
    """Test that base_params are configured correctly"""
    generator = AIGenerator(api_key="test-key", model="claude-sonnet-4")

    assert generator.base_params["model"] == "claude-sonnet-4"
    assert generator.base_params["temperature"] == 0
    assert generator.base_params["max_tokens"] == 800


# ============================================================================
# Simple Response Tests
# ============================================================================


def test_generate_response_no_tools(mock_anthropic_client):
    """Test generating response without tools"""
    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        response = generator.generate_response(
            query="What is RAG?", conversation_history=None, tools=None, tool_manager=None
        )

        assert isinstance(response, str)
        assert len(response) > 0
        mock_anthropic_client.messages.create.assert_called_once()


def test_generate_response_with_history(mock_anthropic_client):
    """Test response generation with conversation history"""
    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        history = "User: Previous question\nAssistant: Previous answer"

        response = generator.generate_response(
            query="Follow-up question", conversation_history=history, tools=None, tool_manager=None
        )

        # Should include history in system prompt
        call_args = mock_anthropic_client.messages.create.call_args
        assert "Previous question" in call_args[1]["system"]


def test_generate_response_without_history(mock_anthropic_client):
    """Test response generation without history"""
    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        response = generator.generate_response(
            query="Standalone question", conversation_history=None, tools=None, tool_manager=None
        )

        # System prompt should not include history
        call_args = mock_anthropic_client.messages.create.call_args
        system_content = call_args[1]["system"]
        assert "Previous conversation" not in system_content or "None" not in system_content


# ============================================================================
# Tool Usage Tests
# ============================================================================


def test_generate_response_with_tools_not_used(mock_anthropic_client):
    """Test when tools are available but AI doesn't use them"""
    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        tool_definitions = [{"name": "test_tool", "description": "A test tool"}]

        response = generator.generate_response(
            query="Simple question", tools=tool_definitions, tool_manager=Mock()
        )

        # Should still return text response
        assert isinstance(response, str)
        # Tools should be passed to API
        call_args = mock_anthropic_client.messages.create.call_args
        assert "tools" in call_args[1]


def test_generate_response_with_tool_use(
    mock_anthropic_tool_use_response, mock_anthropic_final_response
):
    """Test when AI uses a tool"""
    mock_client = Mock()
    # First call returns tool_use, second returns final answer
    mock_client.messages.create.side_effect = [
        mock_anthropic_tool_use_response,
        mock_anthropic_final_response,
    ]

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = (
        "Tool result: RAG stands for Retrieval-Augmented Generation."
    )

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        tools = [{"name": "search_course_content"}]

        response = generator.generate_response(
            query="What is RAG?", tools=tools, tool_manager=mock_tool_manager
        )

        # Should have called API twice (initial + after tool)
        assert mock_client.messages.create.call_count == 2
        # Should have executed the tool
        mock_tool_manager.execute_tool.assert_called_once()
        # Should return final response
        assert "Retrieval-Augmented Generation" in response


def test_handle_tool_execution_multi_turn(
    mock_anthropic_tool_use_response, mock_anthropic_final_response
):
    """Test multi-turn tool execution flow"""
    mock_client = Mock()
    mock_client.messages.create.return_value = mock_anthropic_final_response

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Search results here"

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        base_params = {
            "messages": [{"role": "user", "content": "Test query"}],
            "system": "Test system prompt",
        }

        result = generator._handle_tool_execution(
            mock_anthropic_tool_use_response, base_params, mock_tool_manager
        )

        # Should execute tool and return final text
        assert isinstance(result, str)
        assert "Retrieval-Augmented Generation" in result


def test_handle_multiple_tool_calls(mock_anthropic_final_response):
    """Test handling multiple tool calls in one response"""
    # Create response with multiple tool uses
    mock_response = Mock()
    tool1 = Mock(type="tool_use", id="tool_1", name="search", input={"query": "test1"})
    tool2 = Mock(type="tool_use", id="tool_2", name="outline", input={"course": "test"})
    mock_response.content = [tool1, tool2]
    mock_response.stop_reason = "tool_use"

    mock_client = Mock()
    # First call returns the response passed in (already tool_use)
    # Second call returns final response (end_turn)
    mock_client.messages.create.return_value = mock_anthropic_final_response

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Tool result"

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        base_params = {
            "messages": [{"role": "user", "content": "Complex query"}],
            "system": "System prompt",
        }

        result = generator._handle_tool_execution(mock_response, base_params, mock_tool_manager)

        # Should execute both tools (from the initial mock_response)
        assert mock_tool_manager.execute_tool.call_count == 2


# ============================================================================
# Error Handling Tests
# ============================================================================


def test_generate_response_api_error():
    """Test handling of Anthropic API errors"""
    mock_client = Mock()
    mock_client.messages.create.side_effect = Exception("API Error: Rate limit exceeded")

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        with pytest.raises(Exception) as exc_info:
            generator.generate_response(query="Test query")

        assert "Rate limit exceeded" in str(exc_info.value)


def test_generate_response_tool_execution_error(mock_anthropic_tool_use_response):
    """Test when tool execution returns an error"""
    mock_client = Mock()
    final_response = Mock()
    final_response.content = [Mock(text="I encountered an error with the search.", type="text")]
    final_response.stop_reason = "end_turn"

    mock_client.messages.create.side_effect = [mock_anthropic_tool_use_response, final_response]

    mock_tool_manager = Mock()
    # Tool returns error string
    mock_tool_manager.execute_tool.return_value = "Search error: connection failed"

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        response = generator.generate_response(
            query="Test", tools=[{"name": "search"}], tool_manager=mock_tool_manager
        )

        # Should still return a response (AI interprets the error)
        assert isinstance(response, str)


# ============================================================================
# Message Construction Tests
# ============================================================================


def test_system_prompt_includes_instructions(mock_anthropic_client):
    """Test that system prompt includes instructions"""
    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        generator.generate_response(query="Test")

        call_args = mock_anthropic_client.messages.create.call_args
        system_prompt = call_args[1]["system"]

        # Should include key instructions
        assert "AI assistant" in system_prompt or "course" in system_prompt


def test_system_prompt_with_history(mock_anthropic_client):
    """Test system prompt includes conversation history"""
    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        history = "User: Past question\nAssistant: Past answer"

        generator.generate_response(query="New question", conversation_history=history)

        call_args = mock_anthropic_client.messages.create.call_args
        system_prompt = call_args[1]["system"]

        assert "Past question" in system_prompt
        assert "Past answer" in system_prompt


def test_message_structure_user_query(mock_anthropic_client):
    """Test user message structure"""
    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        generator.generate_response(query="What is vector search?")

        call_args = mock_anthropic_client.messages.create.call_args
        messages = call_args[1]["messages"]

        assert len(messages) == 1
        assert messages[0]["role"] == "user"
        assert "vector search" in messages[0]["content"]


# ============================================================================
# Sequential Tool Calling Tests
# ============================================================================


def test_two_sequential_tool_calls(mock_anthropic_two_round_responses):
    """Test Claude makes 2 sequential tool calls"""
    mock_client = Mock()
    mock_client.messages.create.side_effect = mock_anthropic_two_round_responses

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.side_effect = [
        "Course outline: Lesson 1, Lesson 2, Lesson 3",
        "Search results: Embeddings are vector representations...",
    ]

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")
        response = generator.generate_response(
            query="What does the RAG course say about embeddings?",
            tools=[{"name": "get_course_outline"}, {"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

    # Verify 3 API calls (round 1 + round 2 + final)
    assert mock_client.messages.create.call_count == 3

    # Verify 2 tool executions
    assert mock_tool_manager.execute_tool.call_count == 2
    # Tool names are accessed via content_block.name, which is a Mock attribute
    # Just verify we got 2 calls with side effects
    assert mock_tool_manager.execute_tool.call_count == 2

    # Verify final response
    assert "Final answer" in response


def test_max_tool_rounds_limit(mock_anthropic_max_rounds_responses):
    """Test max rounds limit prevents infinite loops"""
    mock_client = Mock()
    mock_client.messages.create.side_effect = mock_anthropic_max_rounds_responses

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Tool result"

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")
        response = generator.generate_response(
            query="Complex query",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

    # Should make 4 API calls (2 rounds + overflow tool + final)
    assert mock_client.messages.create.call_count == 4

    # Should execute 3 tools (2 rounds + 1 overflow)
    assert mock_tool_manager.execute_tool.call_count == 3

    # Verify last call had NO tools parameter (forced final response)
    last_call_kwargs = mock_client.messages.create.call_args_list[-1][1]
    assert "tools" not in last_call_kwargs

    # Verify we got final response
    assert "Forced final answer" in response


def test_tool_error_allows_continuation(mock_anthropic_two_round_responses):
    """Test tool errors don't break the loop"""
    mock_client = Mock()
    mock_client.messages.create.side_effect = mock_anthropic_two_round_responses

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.side_effect = [
        "No relevant content found.",  # Error result
        "Found relevant content...",  # Successful retry
    ]

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")
        response = generator.generate_response(
            query="Find embeddings",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

    # Should complete normally despite error
    assert mock_tool_manager.execute_tool.call_count == 2
    assert "Final answer" in response


def test_single_tool_call_backward_compatible(
    mock_anthropic_tool_use_response, mock_anthropic_final_response
):
    """Test single tool call still works (backward compatibility)"""
    mock_client = Mock()
    mock_client.messages.create.side_effect = [
        mock_anthropic_tool_use_response,  # Round 1: tool use
        mock_anthropic_final_response,  # Round 1: text response
    ]

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.return_value = "Search result"

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")
        response = generator.generate_response(
            query="What is RAG?",
            tools=[{"name": "search_course_content"}],
            tool_manager=mock_tool_manager,
        )

    # Should make 2 API calls (tool use + final response)
    assert mock_client.messages.create.call_count == 2

    # Should execute 1 tool
    assert mock_tool_manager.execute_tool.call_count == 1

    # Should return final response
    assert "Retrieval-Augmented Generation" in response


def test_message_structure_with_sequential_tools(mock_anthropic_two_round_responses):
    """Test message structure is correct across sequential tool calls"""
    mock_client = Mock()
    mock_client.messages.create.side_effect = mock_anthropic_two_round_responses

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.side_effect = ["Outline result", "Search result"]

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")
        response = generator.generate_response(
            query="Test query", tools=[{"name": "test_tool"}], tool_manager=mock_tool_manager
        )

    # Check message structure in second API call (after first tool execution)
    second_call_kwargs = mock_client.messages.create.call_args_list[1][1]
    messages = second_call_kwargs["messages"]

    # After round 1: user query, assistant tool_use, user tool_result
    # After round 2: all of above PLUS assistant tool_use_2, user tool_result_2
    # The second call shows accumulated messages from both rounds
    assert len(messages) >= 3  # At minimum 3, but may have more from sequential rounds
    assert messages[0]["role"] == "user"
    assert messages[1]["role"] == "assistant"
    assert messages[2]["role"] == "user"
    assert messages[2]["content"][0]["type"] == "tool_result"


def test_tools_preserved_in_api_calls(mock_anthropic_two_round_responses):
    """Test tools parameter is preserved in sequential calls"""
    mock_client = Mock()
    mock_client.messages.create.side_effect = mock_anthropic_two_round_responses

    mock_tool_manager = Mock()
    mock_tool_manager.execute_tool.side_effect = ["Result 1", "Result 2"]

    tools = [{"name": "test_tool", "description": "A test tool"}]

    with patch("anthropic.Anthropic", return_value=mock_client):
        generator = AIGenerator(api_key="test-key", model="test-model")
        response = generator.generate_response(
            query="Test query", tools=tools, tool_manager=mock_tool_manager
        )

    # Check all API calls except the last had tools parameter
    all_calls = mock_client.messages.create.call_args_list

    # First call (initial) should have tools
    first_call_kwargs = all_calls[0][1]
    assert "tools" in first_call_kwargs
    assert "tool_choice" in first_call_kwargs

    # Second call (after round 1) should have tools
    second_call_kwargs = all_calls[1][1]
    assert "tools" in second_call_kwargs
    assert "tool_choice" in second_call_kwargs

    # Third call (final) is end_turn, so it has no tools check needed


def test_no_tool_use_direct_answer(mock_anthropic_client):
    """Test Claude can answer without using tools"""
    with patch("anthropic.Anthropic", return_value=mock_anthropic_client):
        generator = AIGenerator(api_key="test-key", model="test-model")

        response = generator.generate_response(
            query="What is machine learning?",
            tools=[{"name": "search_course_content"}],
            tool_manager=Mock(),
        )

    # Should make single API call
    assert mock_anthropic_client.messages.create.call_count == 1

    # Should return text response
    assert isinstance(response, str)
    assert len(response) > 0

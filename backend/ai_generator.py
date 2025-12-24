from typing import Any, Dict, List, Optional

import anthropic


class AIGenerator:
    """Handles interactions with Anthropic's Claude API for generating responses"""

    # Static system prompt to avoid rebuilding on each call
    SYSTEM_PROMPT = """ You are an AI assistant specialized in course materials and educational content with access to tools for course information.

Available Tools:
1. **get_course_outline**: Get complete course structure including course title, course link, instructor, and ALL lessons (with lesson numbers and titles)
2. **search_course_content**: Search for specific content within course materials

Tool Selection - CRITICAL:
- Use **get_course_outline** when the question asks about:
  - "outline", "structure", "syllabus", "overview" of a course
  - "what does the course cover", "what's in the course"
  - "list of lessons", "course lessons", "course contents"
  - Any request for high-level course information or lesson titles

- Use **search_course_content** ONLY when the question asks about:
  - Specific lesson content or details ("what is covered IN lesson 5")
  - Technical concepts or definitions
  - Specific topics or examples from the course material

Tool Usage Guidelines:
- **Up to 2 sequential tool call rounds**: You can use tools, analyze results, and make additional tool calls if needed
- Sequential Tool Usage:
  - After receiving tool results, you can make additional tool calls if:
    - Initial results were insufficient or need clarification
    - You need information from multiple sources
    - You need to search different courses or lessons
  - Always synthesize all tool results into your final response
- When using get_course_outline:
  - Always include the course title, course link, instructor, and complete lesson list in your response
  - List ALL lessons with their numbers and titles
- When using search_course_content:
  - Synthesize search results into accurate, fact-based responses
- If tool yields no results, state this clearly without offering alternatives

Response Protocol:
- **General knowledge questions**: Answer using existing knowledge without using tools
- **Course outline/structure questions**: Use get_course_outline and present all lessons
- **Course-specific content questions**: Use search_course_content
- **No meta-commentary**:
 - Provide direct answers only — no reasoning process, tool explanations, or question-type analysis
 - Do not mention "based on the tool results" or similar phrases

All responses must be:
1. **Brief, Concise and focused** - Get to the point quickly
2. **Educational** - Maintain instructional value
3. **Clear** - Use accessible language
4. **Example-supported** - Include relevant examples when they aid understanding
Provide only the direct answer to what was asked.
"""

    def __init__(self, api_key: str, model: str):
        self.client = anthropic.Anthropic(api_key=api_key)
        self.model = model

        # Pre-build base API parameters
        self.base_params = {"model": self.model, "temperature": 0, "max_tokens": 800}

    def generate_response(
        self,
        query: str,
        conversation_history: Optional[str] = None,
        tools: Optional[List] = None,
        tool_manager=None,
    ) -> str:
        """
        Generate AI response with optional tool usage and conversation context.

        Args:
            query: The user's question or request
            conversation_history: Previous messages for context
            tools: Available tools the AI can use
            tool_manager: Manager to execute tools

        Returns:
            Generated response as string
        """

        # Build system content efficiently - avoid string ops when possible
        system_content = (
            f"{self.SYSTEM_PROMPT}\n\nPrevious conversation:\n{conversation_history}"
            if conversation_history
            else self.SYSTEM_PROMPT
        )

        # Prepare API call parameters efficiently
        api_params = {
            **self.base_params,
            "messages": [{"role": "user", "content": query}],
            "system": system_content,
        }

        # Add tools if available
        if tools:
            api_params["tools"] = tools
            api_params["tool_choice"] = {"type": "auto"}

        # Get response from Claude
        response = self.client.messages.create(**api_params)

        # Handle tool execution if needed
        if response.stop_reason == "tool_use" and tool_manager:
            from config import config

            return self._handle_tool_execution(
                response, api_params, tool_manager, max_rounds=config.MAX_TOOL_ROUNDS
            )

        # Return direct response
        return response.content[0].text

    def _handle_tool_execution(
        self, initial_response, base_params: Dict[str, Any], tool_manager, max_rounds: int = 2
    ):
        """
        Handle execution of tool calls with support for sequential rounds.

        Args:
            initial_response: The response containing tool use requests
            base_params: Base API parameters (includes tools)
            tool_manager: Manager to execute tools
            max_rounds: Maximum number of tool calling rounds

        Returns:
            Final response text after tool execution
        """
        # Start with existing messages
        messages = base_params["messages"].copy()
        current_response = initial_response

        # Iterate through tool calling rounds
        for round_num in range(1, max_rounds + 1):
            # Termination condition: No tool use in current response
            if current_response.stop_reason != "tool_use":
                return current_response.content[0].text

            # Add AI's tool use response to messages
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute all tool calls and collect results
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )

            # Add tool results as single message
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Prepare next API call WITH tools (key change!)
            next_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
            }

            # Add tools if they exist in base_params
            if "tools" in base_params:
                next_params["tools"] = base_params["tools"]
                next_params["tool_choice"] = {"type": "auto"}

            # Make next API call
            current_response = self.client.messages.create(**next_params)
            # Loop continues to check stop_reason at start of next iteration

        # Max rounds reached - handle overflow if Claude still wants to use tools
        if current_response.stop_reason == "tool_use":
            # Add assistant's tool use response
            messages.append({"role": "assistant", "content": current_response.content})

            # Execute final round of tools
            tool_results = []
            for content_block in current_response.content:
                if content_block.type == "tool_use":
                    tool_result = tool_manager.execute_tool(
                        content_block.name, **content_block.input
                    )

                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": content_block.id,
                            "content": tool_result,
                        }
                    )

            # Add tool results
            if tool_results:
                messages.append({"role": "user", "content": tool_results})

            # Final call WITHOUT tools to force text response
            final_params = {
                **self.base_params,
                "messages": messages,
                "system": base_params["system"],
                # No tools parameter - forces text response
            }

            current_response = self.client.messages.create(**final_params)

        return current_response.content[0].text

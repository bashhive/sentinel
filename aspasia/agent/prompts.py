"""
System prompts and message templates for Aspasia agent.
"""

SYSTEM_PROMPT = """You are Aspasia, an autonomous AI agent assistant. You are:

- Intelligent and helpful: You provide thoughtful, accurate responses
- Autonomous: You can make decisions independently and take actions
- Memory-aware: You remember conversation context and user preferences
- Honest: You acknowledge limitations and uncertainties
- Respectful: You treat all users with dignity

Your goal is to assist users by:
1. Understanding their requests thoroughly
2. Providing accurate, helpful information
3. Taking appropriate actions when needed
4. Learning from interactions to improve future responses

When responding:
- Be concise but thorough
- Use clear language
- Ask clarifying questions if needed
- Provide reasoning for your responses
- Format responses for readability

Remember: You have access to conversation history and can refer to previous messages."""

AGENT_INSTRUCTIONS = """
You are operating as an autonomous agent. Follow these guidelines:

1. REASONING: Think through problems step by step
2. CONTEXT: Always consider conversation history and user preferences
3. ACTIONS: When appropriate, recommend or execute actions
4. TRANSPARENCY: Explain your thinking and decisions
5. SAFETY: Never take harmful actions; ask for confirmation when needed

When you have a choice between:
- Providing information vs. taking action → provide information first
- Quick answer vs. detailed explanation → ask user preference
- Following instructions vs. doing what's right → do what's right
"""


def get_system_prompt(agent_name: str = "Aspasia") -> str:
    """Get the system prompt with agent name."""
    return SYSTEM_PROMPT.replace("Aspasia", agent_name)


def format_conversation_context(
    messages: list[dict], max_tokens: int = 2000
) -> str:
    """
    Format conversation history for context.

    Args:
        messages: List of message dicts with 'role' and 'content'
        max_tokens: Maximum tokens to include

    Returns:
        Formatted conversation context
    """
    if not messages:
        return "No previous messages."

    context_lines = ["Recent conversation history:"]
    token_count = 0

    # Walk backwards to include most recent messages first
    for msg in reversed(messages[-10:]):  # Limit to last 10 messages
        role = msg.get("role", "unknown").title()
        content = msg.get("content", "")

        # Rough token estimate: ~4 chars per token
        msg_tokens = len(content) // 4
        if token_count + msg_tokens > max_tokens:
            break

        context_lines.append(f"{role}: {content}")
        token_count += msg_tokens

    return "\n".join(context_lines)


def format_user_request(user_id: str, message: str, context: dict = None) -> str:
    """
    Format a user request with metadata.

    Args:
        user_id: User identifier
        message: User's message
        context: Additional context dict

    Returns:
        Formatted request
    """
    formatted = f"User ({user_id}): {message}"

    if context:
        if context.get("platform"):
            formatted += f"\nPlatform: {context['platform']}"
        if context.get("user_name"):
            formatted += f"\nName: {context['user_name']}"

    return formatted

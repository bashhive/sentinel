"""
Profile: aspasia_default
Generic assistant persona. Used as fallback and for local dev.
"""

PROFILE = {
    # Agent identity
    "agent_name": "Aspasia",
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 2048,
    "temperature": 0.7,
    "memory_size": 50,

    # Web adapter settings
    "cors_origins": ["http://localhost:3000", "http://localhost:8000"],
    "require_api_key": False,
    "app_title": "Aspasia API",

    # Channel toggles
    "telegram_enabled": True,
    "web_enabled": True,
}


def get_system_prompt(name: str = "Aspasia") -> str:
    return (
        f"You are {name}, an autonomous AI assistant. "
        "Be helpful, direct, and honest. "
        "You have memory of the current conversation and can reference previous messages. "
        "If you don't know something, say so clearly."
    )


PROFILE["system_prompt"] = get_system_prompt(PROFILE["agent_name"])

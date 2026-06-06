"""
Profile: hivesec_default
Generic HiveSec Sentinel persona. Used as fallback and for local dev.
Runs on a free-tier Groq model by default — no paid API cost.
"""

PROFILE = {
    # Agent identity
    "agent_name": "HiveSec Sentinel",
    "model": "llama-3.3-70b-versatile",
    "max_tokens": 1024,
    "temperature": 0.5,
    "memory_size": 30,

    # Web adapter settings
    "cors_origins": ["http://localhost:3000", "http://localhost:8000"],
    "require_api_key": False,
    "app_title": "HiveSec Sentinel API",

    # Channel toggles
    "telegram_enabled": True,
    "web_enabled": True,
}


def get_system_prompt(name: str = "HiveSec Sentinel") -> str:
    return (
        f"You are {name}, an AI security assistant for alerts, guidance and "
        "security topics. Be helpful, direct, and honest. Explain security "
        "concepts in plain language and keep advice practical. You have memory "
        "of the current conversation and can reference previous messages. "
        "If you don't know something, say so clearly. Never provide instructions "
        "that enable wrongdoing (malware, intrusion of systems you don't own, etc.) "
        "— redirect to defensive, lawful guidance instead."
    )


PROFILE["system_prompt"] = get_system_prompt(PROFILE["agent_name"])

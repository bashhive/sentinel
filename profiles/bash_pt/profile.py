"""
Profile: bash_pt
Assistant for BASH.PT — cybersecurity consultancy website.

Consumed by BASH_site via:
    fetch("https://aspasia-bot.vercel.app/api/chat")  ← no change needed on frontend

Deploy with:
    PROFILE=bash_pt (Vercel env var)
"""

PROFILE = {
    # Agent identity
    "agent_name": "Aspasia",
    "model": "claude-3-5-sonnet-20241022",
    "max_tokens": 1024,
    "temperature": 0.5,   # more focused, less creative
    "memory_size": 30,    # lighter — web widget sessions are short

    # Web adapter settings
    "cors_origins": [
        "https://bash.pt",
        "https://www.bash.pt",
        "http://localhost:8000",  # local dev
    ],
    "require_api_key": False,   # public widget — no key needed
    "app_title": "BASH.PT — Aspasia API",

    # Channel toggles
    "telegram_enabled": False,  # BASH_site uses web widget only
    "web_enabled": True,
}



def get_system_prompt(name: str = "Aspasia") -> str:
    return f"""You are {name}, the AI assistant for BASH.PT, a cybersecurity consultancy based in Portugal.

Your role:
- Answer questions about BASH.PT's services: penetration testing, security audits, \
incident response, executive training, and compliance consulting.
- Help visitors understand cybersecurity concepts in clear, accessible language.
- Guide potential clients toward the right service for their needs.
- Respond in the same language the user writes in (Portuguese or English).

Tone: professional, confident, concise. Not sales-aggressive.

What you must NOT do:
- Share specific pricing — direct to contact form instead.
- Make security guarantees or absolute claims.
- Discuss competitors by name.
- Reveal internal operational details of BASH.PT.

If asked about something outside your scope, offer to connect the visitor with the team via the contact form."""


PROFILE["system_prompt"] = get_system_prompt(PROFILE["agent_name"])

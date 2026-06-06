# HiveSec Sentinel — site bot

Multi-site reusable **AI security assistant**. One codebase, multiple personas and
deployments via **profiles**.

- **Brand:** BashHive
- **Bot:** HiveSec Sentinel
- **Telegram:** [@hivesecsentinelbot](https://t.me/hivesecsentinelbot)
- **Tagline:** *"AI security assistant for alerts, guidance and security topics."*

> The git repo / Vercel project are still named `aspasia-bot` for continuity
> (the BASH site fetches `https://aspasia-bot.vercel.app/api/chat`). The product,
> persona and code are now **HiveSec Sentinel**. The name *Aspasia* is reserved
> for the separate autonomous financial agent (`~/Code/Aspasia`).

## No paid API cost

The default LLM path talks to an **OpenAI-compatible endpoint over plain httpx** —
no vendor SDK, no Anthropic bill. Out of the box it points at **Groq's free tier**
(`llama-3.3-70b-versatile`, which supports tool-calling). Switch providers with two
env vars (`LLM_BASE_URL`, `GROQ_API_KEY`/`LLM_API_KEY`) — Gemini's OpenAI endpoint,
OpenRouter, or a local server all work. The paid Anthropic backend is still
available but optional (`LLM_PROVIDER=anthropic`, `pip install '.[anthropic]'`).

## Architecture

```
aspasia_bot/                # (folder kept; product = HiveSec Sentinel)
├── core/                   # Zero coupling — pure agent logic
│   ├── agent.py            # Agent (process_message, tool loop, health, stats)
│   ├── llm_client.py       # Provider-neutral client + Groq/Anthropic + make_client()
│   ├── session.py          # MemorySystem — per-user conversation history
│   ├── session_redis.py    # Optional Redis-backed sessions
│   └── tools.py            # ToolRegistry — extensible, safe calculate (ast)
│
├── adapters/               # One per channel
│   ├── telegram/handler.py # TelegramAdapter(token, agent)
│   └── web/app.py          # create_app(agent, cors_origins, ...) → FastAPI
│
├── profiles/               # One per site/bot deployment
│   ├── bash_pt/            # HiveSec Sentinel for the BASH / BashHive site (+ tools)
│   └── hivesec_default/    # Generic fallback persona
│
├── config/base.py          # BaseConfig (pydantic-settings) — infra + provider only
└── main.py                 # Entry point: loads profile, wires core + adapters
```

The `Agent` speaks one internal block dialect (Anthropic-style: `text` / `tool_use` /
`tool_result`). `core/llm_client.py` translates that to/from the OpenAI Chat
Completions format at the boundary, so the tool-use loop is provider-agnostic.

## Quickstart

```bash
pip install -e ".[dev]"
cp .env.example .env
# Edit .env: set GROQ_API_KEY (free at https://console.groq.com) and PROFILE

PROFILE=bash_pt python main.py
```

## Profiles

A profile is a dict in `profiles/<name>/profile.py`:

| Key | Type | Description |
|-----|------|-------------|
| `agent_name` | str | Bot display name |
| `system_prompt` | str | Full system prompt injected into the model |
| `model` | str | Model ID (e.g. `llama-3.3-70b-versatile`) |
| `max_tokens` | int | Response token cap |
| `temperature` | float | Sampling temperature |
| `memory_size` | int | Max messages per user session |
| `cors_origins` | list[str] | Allowed origins for web adapter |
| `require_api_key` | bool | Enable X-API-Key header guard |
| `app_title` | str | FastAPI title |
| `telegram_enabled` | bool | Mount Telegram adapter |
| `web_enabled` | bool | Mount web adapter (must be True) |
| `register_tools` | callable | Optional hook to add site-specific tools |

### Adding a new site

1. Create `profiles/<site>/profile.py` — copy from `hivesec_default`
2. Set `agent_name`, `system_prompt`, `cors_origins`, channel toggles
3. Add `profiles/<site>/.env.example`
4. Deploy with `PROFILE=<site>`

No changes to `core/` or `adapters/`.

## API endpoints (web adapter)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | — | Service info |
| GET | `/api/health` | — | LLM + agent health check |
| GET | `/api/status` | — | Agent stats |
| POST | `/api/chat` | optional key | Send message, get response |
| GET | `/api/history?session_id=` | optional key | Conversation history |
| POST | `/api/reset` | optional key | Clear session |
| POST | `/api/telegram` | — | Telegram webhook receiver |

## BASH / BashHive site integration

`BASH_site/public_html/index.html` calls:

```js
fetch("https://aspasia-bot.vercel.app/api/chat", { ... })  // reads data.message
```

No frontend change required. Deploy with Vercel env vars:

```
PROFILE=bash_pt
LLM_PROVIDER=groq
GROQ_API_KEY=gsk_...
```

## Tests

```bash
pytest tests/ -v   # no network, no real API calls (LLM client is mocked)
```

## Security notes

- `core/tools.py`: `calculate` uses an `ast` whitelist — no `eval()` builtins.
- CORS origins are profile-scoped — no `allow_origins=["*"]` in production profiles.
- Optional API-key guard via `require_api_key` + `web_api_key` in the profile.
- Tokens (`GROQ_API_KEY`, `TELEGRAM_BOT_TOKEN`) live in `.env`, never in profile source.

> **Note:** `docs/API.md`, `docs/ARCHITECTURE.md`, `docs/DEPLOYMENT.md`, and
> `docs/TELEGRAM.md` describe the older `aspasia/...` v1 layout and are partly
> out of date. This README is the source of truth for the current architecture.

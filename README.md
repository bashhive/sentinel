# aspasia_bot

Multi-site reusable AI bot. One codebase, multiple personas and deployments via **profiles**.

## Architecture

```
aspasia_bot/
├── core/                  # Zero coupling — pure agent logic
│   ├── agent.py           # Agent class (process_message, health_check, stats)
│   ├── claude_client.py   # Async/sync Anthropic SDK wrapper
│   ├── session.py         # MemorySystem — per-user conversation history
│   └── tools.py           # ToolRegistry — extensible, safe calculate (ast)
│
├── adapters/              # One per channel
│   ├── telegram/
│   │   └── handler.py     # TelegramAdapter(token, agent)
│   └── web/
│       └── app.py         # create_app(agent, cors_origins, ...) → FastAPI
│
├── profiles/              # One per site/bot deployment
│   ├── bash_pt/
│   │   ├── profile.py     # PROFILE dict: persona, cors, toggles
│   │   └── .env.example
│   └── aspasia_default/
│       ├── profile.py
│       └── .env.example
│
├── config/
│   └── base.py            # BaseConfig (pydantic-settings) — infra only
│
├── main.py                # Entry point: loads profile, wires core + adapters
├── pyproject.toml
└── .env.example
```

## Quickstart

```bash
# Install
pip install -e ".[dev]"

# Configure
cp .env.example .env
# Edit .env: set ANTHROPIC_API_KEY and PROFILE

# Run (default profile)
python main.py

# Run bash_pt profile
PROFILE=bash_pt python main.py
```

## Profiles

A profile is a dict in `profiles/<name>/profile.py` that controls:

| Key | Type | Description |
|-----|------|-------------|
| `agent_name` | str | Bot display name |
| `system_prompt` | str | Full system prompt injected into Claude |
| `model` | str | Claude model ID |
| `max_tokens` | int | Response token cap |
| `temperature` | float | Sampling temperature |
| `memory_size` | int | Max messages per user session |
| `cors_origins` | list[str] | Allowed origins for web adapter |
| `require_api_key` | bool | Enable X-API-Key header guard |
| `app_title` | str | FastAPI title |
| `telegram_enabled` | bool | Mount Telegram adapter |
| `web_enabled` | bool | Mount web adapter (must be True) |


## Adding a new site

1. Create `profiles/<site>/profile.py` — copy from `aspasia_default`
2. Set `agent_name`, `system_prompt`, `cors_origins`, channel toggles
3. Add `profiles/<site>/.env.example`
4. Deploy with `PROFILE=<site>` env var

That's it. No changes to `core/` or `adapters/`.

## API endpoints (web adapter)

| Method | Path | Auth | Description |
|--------|------|------|-------------|
| GET | `/` | — | Service info |
| GET | `/api/health` | — | Claude + agent health check |
| GET | `/api/status` | — | Agent stats |
| POST | `/api/chat` | optional key | Send message, get response |
| GET | `/api/history?session_id=` | optional key | Conversation history |
| POST | `/api/reset` | optional key | Clear session |
| POST | `/api/telegram` | — | Telegram webhook receiver |

## BASH_site integration

`BASH_site/public_html/index.html` already calls:
```js
fetch("https://aspasia-bot.vercel.app/api/chat", { ... })
```
No change needed on the frontend.

Deploy `aspasia_bot` to Vercel with:
```
PROFILE=bash_pt
ANTHROPIC_API_KEY=...
```

## Vercel deployment

```bash
vercel --prod
# Set env vars in Vercel dashboard:
#   ANTHROPIC_API_KEY, PROFILE=bash_pt
```

## Running tests

```bash
pytest tests/ -v
```

## Memory / session backend

Default: in-process dict (resets on restart).  
To add persistence: subclass `core.session.MemorySystem` and override store/fetch methods (Redis, SQLite, etc.). Inject via `Agent(memory=YourBackend())`.

## Security notes

- `core/tools.py`: `calculate` uses `ast.parse` whitelist — no `eval()` builtins
- CORS origins are profile-scoped — no `allow_origins=["*"]` in production profiles
- API key guard available via `require_api_key` + `web_api_key` in profile
- `telegram_bot_token` lives in `.env`, never in profile source code

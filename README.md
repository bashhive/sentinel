# Aspasia - Autonomous AI Bot

An autonomous agentic AI assistant deployable on Telegram and as a web service.

## Features

- **Autonomous Agent Logic** - Powered by Claude API
- **Telegram Bot** - Real-time messaging integration
- **Web API** - REST endpoints for website integration
- **Configuration System** - Easy setup and management
- **Production-Ready** - Structured, documented, deployable

## Project Structure

```
Aspasia/
├── README.md
├── requirements.txt        # Python dependencies
├── config.py              # Configuration management
├── main.py                # Entry point
├── agent/                 # Core agent logic
│   ├── __init__.py
│   ├── core.py           # Main agent class
│   └── tools.py          # Tools/functions agent can use
├── telegram/             # Telegram bot handler
│   ├── __init__.py
│   └── bot.py            # Telegram bot logic
├── web/                  # Web server/API
│   ├── __init__.py
│   ├── app.py            # Flask/FastAPI server
│   └── routes.py         # API endpoints
├── memory/               # Agent memory/context storage
│   └── __init__.py
└── .env.example          # Environment variables template
```

## Setup

1. Install dependencies: `pip install -r requirements.txt`
2. Copy `.env.example` to `.env` and fill in your API keys
3. Run: `python main.py`

## API Endpoints

- `POST /api/chat` - Send a message to Aspasia
- `GET /api/status` - Check bot status
- `POST /api/telegram` - Telegram webhook receiver

## Deployment

See `DEPLOY.md` for production deployment instructions.

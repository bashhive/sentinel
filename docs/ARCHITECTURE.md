# Aspasia System Architecture

Overview of Aspasia's design and component architecture.

## High-Level Architecture

```
┌─────────────────────────────────────────────────────────────┐
│                     User Interfaces                          │
├──────────────┬──────────────────┬──────────────┬────────────┤
│  Telegram    │   Web Browser    │   REST API   │   Future   │
│     Bot      │   UI (JS/HTML)   │ (FastAPI)    │ Integrations
└──────────┬───┴────────┬─────────┴──────┬───────┴────────────┘
           │            │                │
┌──────────▼────────────▼────────────────▼──────────────────┐
│                   Web Server (FastAPI)                     │
│  - Routes & Endpoints                                      │
│  - Request validation (Pydantic)                           │
│  - CORS & Security middleware                             │
└────────────────────────┬─────────────────────────────────┘
                         │
        ┌────────────────┼────────────────┐
        │                │                │
┌───────▼────────┐  ┌────▼────────────┐  │
│ Agent (Core)   │  │   Integrations  │  │
│ - Logic        │  │ - Claude API    │  │
│ - Reasoning    │  │ - Telegram      │  │
│ - Decision     │  │ - Future APIs   │  │
│   Making       │  └────────────────┘  │
└───────┬────────┘                       │
        │                                │
┌───────▼────────┐  ┌────────────────┐  │
│   Memory       │  │   Tools        │  │
│ - Conversations│  │ - Search       │  │
│ - Preferences  │  │ - Notifications│  │
│ - Facts        │  │ - Scheduling   │  │
└───────┬────────┘  └────────────────┘  │
        │                                │
┌───────▼──────────────────────────────▼┐
│          Storage Layer                │
│  - SQLite / PostgreSQL                │
│  - Redis (optional caching)           │
└──────────────────────────────────────┘
```

## Component Overview

### 1. User Interfaces

#### Telegram Bot (`aspasia/integrations/telegram_handler.py`)

- Handles incoming Telegram messages
- Processes commands (`/start`, `/help`, `/clear`, `/status`)
- Sends responses back to users
- Supports both polling and webhook modes
- Manages bot state and user sessions

**Technology:** `python-telegram-bot`

#### Web UI (`aspasia/web/static/index.html`)

- Simple, modern chat interface
- Real-time message display
- Responsive design (mobile-friendly)
- Connects to REST API
- Local message storage for session

**Technology:** HTML5, CSS3, Vanilla JavaScript

#### REST API (`aspasia/web/`)

- FastAPI-based HTTP server
- JSON request/response format
- Comprehensive endpoint coverage
- Built-in documentation (Swagger UI)
- Error handling and validation

**Technology:** FastAPI, Pydantic, Uvicorn

### 2. Agent Core (`aspasia/agent/core.py`)

**Responsibilities:**
- Receives user messages
- Manages conversation flow
- Calls Claude for responses
- Stores message history
- Tracks user context

**Key Methods:**
- `process_message()` - Main async message handler
- `health_check()` - Dependency health verification
- `get_stats()` - System statistics

**Design Pattern:** Async-first, event-driven

### 3. Memory System (`aspasia/agent/memory.py`)

**Stores:**
- Conversation history (messages per user)
- User preferences (settings, language, etc.)
- Learned facts (extracted from conversations)
- User metadata (creation time, last interaction)

**In-Memory Storage:**
- Fast access for active conversations
- Configurable max history size
- Per-user memory isolation

**Persistence:** Via storage layer

### 4. Claude Integration (`aspasia/integrations/claude_api.py`)

**Responsibilities:**
- API key management
- Async HTTP communication with Claude
- Message formatting for Claude API
- Tool definitions and calls
- Error handling and retries

**Capabilities:**
- Text generation
- Tool use (function calling)
- System prompts
- Token management

### 5. Storage Layer (`aspasia/storage/`)

**Supported Databases:**
- SQLite (default, development)
- PostgreSQL (production)
- MySQL (alternative)

**Data Models:**
- `ConversationRecord` - Persistent message storage
- `UserRecord` - User preferences and facts

**Optional:**
- Redis for caching and sessions
- Message queue for async processing

### 6. Tools System (`aspasia/agent/tools.py`)

**Available Tools:**
- `search_information` - Web search
- `recall_memory` - Retrieve stored facts
- `store_memory` - Learn and remember
- `send_notification` - Send messages
- `schedule_task` - Schedule future tasks

**Architecture:**
- Tool registry pattern
- Extensible design
- Claude-compatible format
- Approval workflow for sensitive operations

## Data Flow

### User Message → Response

```
1. User sends message (Telegram, Web, API)
   ↓
2. Integration receives and validates
   ↓
3. Routes to Agent via process_message()
   ↓
4. Agent retrieves user memory & context
   ↓
5. Agent calls Claude with:
   - System prompt
   - Conversation history
   - User preferences
   - Available tools
   ↓
6. Claude returns response (+ tool calls if any)
   ↓
7. Agent processes tool calls (if any)
   ↓
8. Agent stores conversation in memory
   ↓
9. Agent persists to database (async)
   ↓
10. Integration sends response back to user
```

## Request/Response Cycle (Web API)

```
HTTP POST /api/chat
├─ Validate request (Pydantic)
├─ Extract: user_id, message, context
├─ Call agent.process_message()
│  └─ Async processing
├─ Format response
└─ Return JSON 200 OK
```

## Message Flow (Telegram)

```
Telegram Server
    ↓
Telegram Bot (polling/webhook)
    ↓
telegram_handler.py
    ├─ Command handlers (/start, /help, etc.)
    └─ message_handler (regular messages)
       ├─ Extract: user_id, text
       ├─ Add typing indicator
       ├─ Call agent.process_message()
       └─ Send response
```

## Concurrency Model

- **Main Framework:** `asyncio`
- **Web Server:** `uvicorn` (async ASGI)
- **Telegram:** `python-telegram-bot` (async-first)
- **Database:** Sync SQLAlchemy with thread pool

**Concurrency Limits:**
- Multiple users served in parallel
- Telegram polling runs independently
- Web API scales with worker count
- Claude API calls are properly awaited

## Error Handling

**Layers of Error Handling:**

1. **Request Validation** (Pydantic)
   - Invalid input → 400 Bad Request

2. **Agent Level**
   - Claude API errors → Graceful fallback message
   - Memory errors → Logged, operation skipped

3. **Integration Level**
   - Telegram connection errors → Retry with backoff
   - Web request errors → 500 Internal Server Error

4. **Global Exception Handling**
   - Uncaught errors logged
   - Graceful degradation
   - User-friendly error messages

## Configuration Management

**Hierarchy:**
1. `.env` file (highest priority)
2. Environment variables
3. Code defaults (lowest priority)

**Configuration Validation:**
- Type checking (Pydantic)
- Required field verification
- Enum validation for specific fields
- Integration compatibility checks

## Security Architecture

**API Security:**
- Optional API key authentication
- CORS configuration
- Input validation and sanitization
- Rate limiting (recommended)
- HTTPS enforcement (production)

**Data Security:**
- Sensitive data in environment variables only
- No hardcoded secrets
- Database access control
- User data isolation
- Message encryption in transit (HTTPS/TLS)

**Telegram Security:**
- Webhook secret validation
- Bot token management
- User permission boundaries

## Scalability Considerations

### Horizontal Scaling

**Stateless Components:**
- Web API server (stateless, can scale)
- Agent (mostly stateless, uses memory)
- Integrations (mostly stateless)

**Stateful Components:**
- Memory system (user data)
- Database (persistent storage)

**Scaling Strategy:**
1. Load balance web servers (Nginx, HAProxy)
2. Use PostgreSQL for shared database
3. Use Redis for shared memory/cache
4. Telegram bot runs once per deployment

### Vertical Scaling

- Increase machine resources
- Adjust `AGENT_MEMORY_SIZE`
- Increase database pool size
- Cache frequently accessed data

### Database Scaling

- Use PostgreSQL in production
- Implement connection pooling
- Archive old conversations
- Add indexes for common queries

## Performance Optimization

### Caching

- Redis for conversation cache
- Memory for active user data
- Claude API response caching (if applicable)

### Async Operations

- Non-blocking I/O for all network calls
- Async database queries
- Background task processing

### Resource Management

- Configurable memory history limit
- Message batching
- Connection pooling

## Monitoring & Observability

**Logging Levels:**
- DEBUG: Detailed operation info
- INFO: Important events
- WARNING: Issues to notice
- ERROR: Failures requiring action

**Metrics to Track:**
- Message count per user
- Response latency
- API error rates
- Memory usage
- Database connection pool

**Health Checks:**
- Agent health endpoint
- Claude API connectivity
- Database connectivity
- Memory system status

## Extension Points

1. **New Integrations**
   - Create new handler in `integrations/`
   - Implement `process_message()` interface

2. **New Tools**
   - Add to `tool_registry` in `tools.py`
   - Implement handler function

3. **Storage Backends**
   - Extend `Database` class in `storage/database.py`
   - Implement CRUD operations

4. **Custom Prompts**
   - Edit `agent/prompts.py`
   - Implement prompt templates

## Future Architecture Plans

- WebSocket support for real-time updates
- Multi-modal input (images, voice)
- Plugin system for dynamic tools
- Distributed tracing (OpenTelemetry)
- Vector database for semantic search
- Long-term memory (episodic storage)
- Multi-model support (Claude, GPT, etc.)

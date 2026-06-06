# Aspasia API Documentation

> ⚠️ **Outdated (v1).** Describes the legacy `aspasia/...` layout. The current
> product is **HiveSec Sentinel** — see the root `README.md` for the live API.

Complete REST API reference for Aspasia.

## Base URL

```
http://localhost:8000/api
https://your-domain.com/api
```

## Authentication

Currently uses optional API key authentication. Set `REQUIRE_API_KEY=true` in `.env` to enforce.

```bash
curl -H "Authorization: Bearer YOUR_API_KEY" ...
```

## Endpoints

### Chat

#### Send Message

```
POST /api/chat
```

Send a message to the agent and receive a response.

**Request:**

```json
{
  "user_id": "user123",
  "message": "What is the meaning of life?",
  "context": {
    "platform": "web",
    "user_name": "John"
  }
}
```

**Response:**

```json
{
  "text": "The meaning of life is a philosophical question...",
  "user_id": "user123",
  "timestamp": "2024-01-15T10:30:00",
  "metadata": {
    "context": {
      "user_id": "user123",
      "created_at": "2024-01-15T10:00:00",
      "last_interaction": "2024-01-15T10:30:00",
      "message_count": 5,
      "preferences": {},
      "facts": {}
    }
  }
}
```

**Status Codes:**
- `200` - Success
- `400` - Invalid request
- `500` - Server error

#### Get Conversation History

```
GET /api/chat/{user_id}/history?limit=10
```

Retrieve conversation history for a user.

**Parameters:**
- `user_id` (path): User identifier
- `limit` (query): Maximum messages to return (default: 10)

**Response:**

```json
{
  "user_id": "user123",
  "messages": [
    {
      "role": "user",
      "content": "Hello",
      "timestamp": "2024-01-15T10:00:00"
    },
    {
      "role": "assistant",
      "content": "Hi! How can I help you?",
      "timestamp": "2024-01-15T10:00:05"
    }
  ],
  "count": 2
}
```

#### Get User Context

```
GET /api/chat/{user_id}/context
```

Get context, preferences, and facts about a user.

**Response:**

```json
{
  "user_id": "user123",
  "created_at": "2024-01-15T10:00:00",
  "last_interaction": "2024-01-15T10:30:00",
  "message_count": 5,
  "preferences": {
    "language": "en",
    "timezone": "UTC"
  },
  "facts": {
    "occupation": "Engineer",
    "interests": "AI, programming"
  }
}
```

#### Set User Preference

```
POST /api/chat/{user_id}/preference
```

Store a user preference.

**Request:**

```json
{
  "key": "language",
  "value": "en"
}
```

**Response:**

```json
{
  "status": "ok",
  "user_id": "user123",
  "key": "language",
  "value": "en"
}
```

#### Clear Conversation History

```
DELETE /api/chat/{user_id}/history
```

Delete all conversation history for a user.

**Response:**

```json
{
  "status": "ok",
  "user_id": "user123",
  "message": "History cleared"
}
```

### Agent

#### Health Check

```
GET /api/agent/health
```

Check the health status of the agent and its dependencies.

**Response:**

```json
{
  "agent": "healthy",
  "memory": "healthy",
  "claude": "healthy",
  "timestamp": "2024-01-15T10:30:00"
}
```

#### Get Statistics

```
GET /api/agent/stats
```

Get agent and system statistics.

**Response:**

```json
{
  "agent_name": "Aspasia",
  "model": "claude-3-5-sonnet-20241022",
  "timestamp": "2024-01-15T10:30:00",
  "memory": {
    "total_users": 42,
    "total_messages": 523,
    "avg_messages_per_user": 12
  },
  "tools_available": 6
}
```

### Server

#### Root

```
GET /
```

Get basic server information.

**Response:**

```json
{
  "name": "Aspasia",
  "version": "0.1.0",
  "status": "running",
  "endpoints": [
    "POST /api/chat",
    "GET /api/chat/{user_id}/history",
    "GET /api/chat/{user_id}/context",
    "POST /api/chat/{user_id}/preference",
    "DELETE /api/chat/{user_id}/history",
    "GET /api/agent/health",
    "GET /api/agent/stats",
    "GET /health"
  ]
}
```

#### Health Check

```
GET /health
```

Simple server health check.

**Response:**

```json
{
  "status": "ok",
  "timestamp": "2024-01-15T10:30:00"
}
```

## Examples

### Python

```python
import httpx
import asyncio

async def chat_with_aspasia():
    async with httpx.AsyncClient() as client:
        response = await client.post(
            "http://localhost:8000/api/chat",
            json={
                "user_id": "user123",
                "message": "Hello Aspasia!",
                "context": {"platform": "python"}
            }
        )
        data = response.json()
        print(data["text"])

asyncio.run(chat_with_aspasia())
```

### JavaScript/Node.js

```javascript
const response = await fetch("http://localhost:8000/api/chat", {
  method: "POST",
  headers: {
    "Content-Type": "application/json",
  },
  body: JSON.stringify({
    user_id: "user123",
    message: "Hello Aspasia!",
    context: { platform: "javascript" }
  })
});

const data = await response.json();
console.log(data.text);
```

### cURL

```bash
curl -X POST http://localhost:8000/api/chat \
  -H "Content-Type: application/json" \
  -d '{
    "user_id": "user123",
    "message": "Hello Aspasia!",
    "context": {"platform": "curl"}
  }'
```

## Error Handling

All errors return JSON with consistent format:

```json
{
  "detail": "Error description"
}
```

**Common status codes:**

- `400` - Bad Request (validation error)
- `401` - Unauthorized (invalid API key)
- `404` - Not Found (user not found)
- `429` - Too Many Requests (rate limited)
- `500` - Internal Server Error
- `503` - Service Unavailable (Claude API down)

## Rate Limiting

Currently unlimited, but recommended limits:

- **Chat**: 10 requests per minute per user
- **History**: 30 requests per minute per user
- **General**: 100 requests per minute per IP

## CORS

Default CORS origins from `.env`:

```env
WEB_CORS_ORIGINS=http://localhost:3000,https://your-domain.com
```

## WebSocket Support (Future)

Planned for real-time messaging:

```
WS /api/ws/{user_id}
```

## Pagination

Some endpoints support pagination via query parameters:

```
GET /api/chat/{user_id}/history?limit=20&offset=0
```

## Versioning

Current API version: `v1` (implicit)

Future versions will use:

```
GET /api/v2/chat
```

## Changelog

### v0.1.0 (Current)

- Initial release
- Basic chat functionality
- User context management
- Agent health checks
- Statistics endpoints

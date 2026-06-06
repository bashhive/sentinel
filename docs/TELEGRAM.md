# Telegram Integration Guide

Complete guide to setting up and using Aspasia as a Telegram bot.

## Prerequisites

- Telegram account
- Access to BotFather (@BotFather on Telegram)
- Deployed Aspasia instance (or local development)

## Creating a Telegram Bot

### Step 1: Create Bot with BotFather

1. Open Telegram and search for **@BotFather**
2. Start a conversation: `/start`
3. Create a new bot: `/newbot`
4. Follow the prompts:
   - Choose a name (display name): **HiveSec Sentinel**
   - Choose a username (must end with 'bot'): **hivesecsentinelbot**
5. BotFather will give you the **API Token**

Example token:
```
<REDACTED_TELEGRAM_TOKEN>
```

### Step 2: Configure Bot Settings

Still in BotFather:

```
/setcommands

Select your bot: hivesecsentinelbot

Commands:
start - Start the conversation
help - Show help message
clear - Clear conversation history
status - Show bot status
```

### Step 3: Set Bot Description

```
/setdescription

Select: hivesecsentinelbot

Description: HiveSec Sentinel — AI security assistant for alerts, guidance and security topics.
```

### Step 4: Set Bot About Text

```
/setabouttext

Select: hivesecsentinelbot

About: I'm HiveSec Sentinel — an AI security assistant for alerts, guidance and security topics.
```

## Configuration

### For Polling (Development/Testing)

Polling is simpler to setup but less efficient.

1. Get your bot token from BotFather
2. Add to `.env`:

```env
TELEGRAM_BOT_TOKEN=<REDACTED_TELEGRAM_TOKEN>
```

3. Run Aspasia:

```bash
python -m aspasia.main
```

The bot will connect and start receiving messages immediately.

### For Webhook (Production)

Webhooks are more efficient and reliable for production.

#### Step 1: Setup HTTPS

Webhook requires HTTPS with valid certificate:

```bash
# Get certificate (e.g., with Let's Encrypt)
sudo certbot certonly -d your-domain.com
```

#### Step 2: Set Telegram Webhook

```env
TELEGRAM_BOT_TOKEN=<REDACTED_TELEGRAM_TOKEN>
TELEGRAM_WEBHOOK_URL=https://your-domain.com/telegram/webhook
TELEGRAM_WEBHOOK_SECRET=your-secret-key
```

#### Step 3: Register Webhook with Telegram

```bash
# Call Telegram API to set webhook
curl -X POST https://api.telegram.org/bot<REDACTED_TELEGRAM_TOKEN>/setWebhook \
  -d "url=https://your-domain.com/telegram/webhook" \
  -d "secret_token=your-secret-key"

# Response should be:
# {"ok":true,"result":true,"description":"Webhook was set"}
```

#### Step 4: Verify Webhook

```bash
curl https://api.telegram.org/bot<REDACTED_TELEGRAM_TOKEN>/getWebhookInfo
```

Response:
```json
{
  "ok": true,
  "result": {
    "url": "https://your-domain.com/telegram/webhook",
    "has_custom_certificate": false,
    "pending_update_count": 0
  }
}
```

## Using the Bot

### Starting a Conversation

1. Find your bot on Telegram (search by username)
2. Send `/start` to initialize
3. Start chatting!

### Available Commands

- `/start` - Initialize bot
- `/help` - Show help message
- `/clear` - Clear conversation history
- `/status` - Show bot status

### Example Conversation

```
You: /start
Aspasia: Hello! I'm Aspasia, an autonomous AI assistant...

You: What's the weather like?
Aspasia: I can help with information about weather...

You: Tell me a joke
Aspasia: Why did the AI go to school? To improve its learning...

You: /clear
Aspasia: Conversation history cleared.
```

## Debugging

### Check Bot Status

In Telegram, send `/status` to Aspasia for health information.

### View Logs

```bash
# Development (polling)
python -m aspasia.main 2>&1 | grep -i telegram

# Production (systemd)
sudo journalctl -u aspasia -f | grep -i telegram

# Docker
docker logs -f aspasia_container
```

### Common Issues

#### "Bot not responding"

1. Check token in `.env` is correct
2. Verify Claude API key is set
3. Check logs for errors: `python -m aspasia.main`
4. Ensure internet connectivity

#### "Webhook error"

1. Verify HTTPS certificate is valid
2. Check domain is correct in webhook URL
3. Test endpoint manually: `curl -X POST https://your-domain.com/telegram/webhook -d "test"`
4. Verify secret token matches

#### "Message sending fails"

1. Check Telegram bot token is still valid (can reset in BotFather)
2. Check Claude API connectivity
3. Review logs for rate limiting

#### Reset Webhook (if needed)

```bash
# Delete webhook
curl https://api.telegram.org/bot<REDACTED_TELEGRAM_TOKEN>/deleteWebhook

# Or restart with polling mode
# Remove TELEGRAM_WEBHOOK_URL from .env, keep TELEGRAM_BOT_TOKEN
```

## Advanced Configuration

### Rate Limiting

Edit `aspasia/integrations/telegram_handler.py` to add rate limiting:

```python
# Example: 10 messages per minute per user
from collections import defaultdict
from datetime import datetime, timedelta

message_counts = defaultdict(list)

async def handle_message(self, update, context):
    user_id = str(update.effective_user.id)
    now = datetime.now()
    
    # Remove old timestamps
    message_counts[user_id] = [
        t for t in message_counts[user_id] 
        if now - t < timedelta(minutes=1)
    ]
    
    if len(message_counts[user_id]) >= 10:
        await update.message.reply_text(
            "Rate limited. Please try again in a moment."
        )
        return
    
    message_counts[user_id].append(now)
    # ... continue with normal handling
```

### Custom Commands

Add new commands in `aspasia/integrations/telegram_handler.py`:

```python
self.app.add_handler(CommandHandler("custom_command", self.custom_command))

async def custom_command(self, update, context):
    await update.message.reply_text("Custom response")
```

### Group Chat Support

The bot works in group chats. Users can:

1. Add bot to group
2. Mention bot in message: `@aspasia_ai_bot What's 2+2?`
3. Receive response

To restrict to direct messages only:

```python
async def handle_message(self, update, context):
    if update.message.chat.type != "private":
        await update.message.reply_text(
            "Please message me directly for privacy"
        )
        return
```

### Custom Responses

Edit system prompt in `aspasia/agent/prompts.py` to customize behavior:

```python
SYSTEM_PROMPT = """You are Aspasia, a specialized AI assistant for [your domain].
You focus on [your specialty]..."""
```

## Monitoring

### Monitor Bot Activity

```bash
# Count messages per user
grep "Telegram message from" logs/aspasia.log | cut -d: -f2 | sort | uniq -c

# List all active users
grep "user_id" logs/aspasia.log | grep -o 'user_id=[^ ]*' | sort -u
```

### Set Alerts

Example systemd alert (add to service file):

```ini
[Unit]
OnFailure=systemd-email@%n.service
```

## Troubleshooting Checklist

- [ ] Bot token is correct
- [ ] Claude API key is set
- [ ] Internet connectivity works
- [ ] Telegram API is accessible
- [ ] Logs show no errors
- [ ] Webhook URL is HTTPS (if using webhook)
- [ ] Certificate is valid (if using webhook)
- [ ] Bot is running (check with `/status`)
- [ ] Database is writable

## Further Reading

- [Telegram Bot API Docs](https://core.telegram.org/bots/api)
- [Telegram Bot Features](https://core.telegram.org/bots/features)
- [python-telegram-bot Documentation](https://docs.python-telegram-bot.org/)
- [Deployment Guide](./DEPLOYMENT.md)

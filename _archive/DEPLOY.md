# Aspasia Deployment Guide

## Prerequisites

- Python 3.10+
- Telegram Bot Token (from BotFather)
- Anthropic API Key
- Domain name (for Telegram webhook)

## Local Development

### 1. Setup Environment

```bash
cd /Users/raf/Code/Aspasia
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 2. Install Dependencies

```bash
pip install -r requirements.txt
```

### 3. Configure

```bash
cp .env.example .env
# Edit .env with your actual keys
```

### 4. Run Locally

```bash
python main.py
```

The API will be available at `http://localhost:8000`

API Endpoints:
- `POST /api/chat` - Send message
- `GET /api/status` - Bot status
- `GET /api/history` - Conversation history
- `POST /api/reset` - Reset conversation
- `GET /api/health` - Health check

## Production Deployment

### Option 1: Docker

Create `Dockerfile`:

```dockerfile
FROM python:3.11-slim

WORKDIR /app
COPY requirements.txt .
RUN pip install -r requirements.txt

COPY . .

CMD ["python", "main.py"]
```

Build and run:

```bash
docker build -t aspasia .
docker run -p 8000:8000 --env-file .env aspasia
```

### Option 2: Linux Server (VPS/Ubuntu)

1. SSH into server
2. Clone repository
3. Setup Python venv and install dependencies
4. Use systemd service:

Create `/etc/systemd/system/aspasia.service`:

```ini
[Unit]
Description=Aspasia AI Bot
After=network.target

[Service]
Type=simple
User=aspasia
WorkingDirectory=/home/aspasia/Aspasia
ExecStart=/home/aspasia/Aspasia/venv/bin/python main.py
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl enable aspasia
sudo systemctl start aspasia
```

### Option 3: Heroku

1. Add Procfile:

```
web: python main.py
```

2. Deploy:

```bash
git push heroku main
```

## Telegram Webhook Setup

For production, set up webhook instead of polling:

```bash
curl -X POST https://api.telegram.org/bot{TOKEN}/setWebhook \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://your-domain.com/api/telegram"}'
```

Update in `.env`:

```
TELEGRAM_WEBHOOK_URL=https://your-domain.com/api/telegram
```

## Reverse Proxy (nginx)

```nginx
server {
    listen 80;
    server_name your-domain.com;
    
    location / {
        proxy_pass http://localhost:8000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }
}
```

## SSL/TLS (Let's Encrypt)

```bash
sudo certbot certonly --nginx -d your-domain.com
```

Update nginx config to use SSL.

## Monitoring

Check logs:

```bash
# Docker
docker logs aspasia -f

# Systemd
sudo journalctl -u aspasia -f

# Directly
tail -f /var/log/aspasia.log
```

## Security Checklist

- [ ] Use strong API keys
- [ ] Set DEBUG=false in production
- [ ] Use HTTPS only
- [ ] Limit CORS origins
- [ ] Rate limit API endpoints
- [ ] Monitor API logs
- [ ] Keep dependencies updated
- [ ] Use environment variables (not .env in production)

## Troubleshooting

**Bot not responding:**
- Check TELEGRAM_BOT_TOKEN is correct
- Verify ANTHROPIC_API_KEY is valid
- Check logs for errors

**API errors:**
- Ensure all required env vars are set
- Check network connectivity
- Verify API keys have correct permissions

**Memory/Performance:**
- Monitor conversation history size
- Implement message pruning
- Consider using Redis for caching

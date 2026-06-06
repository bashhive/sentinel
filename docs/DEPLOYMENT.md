# Deployment Guide for Aspasia

> ⚠️ **Outdated (v1).** Describes the legacy `aspasia/...` layout and Anthropic-only
> setup. The current product is **HiveSec Sentinel** (free-tier Groq by default) —
> see the root `README.md` for current deploy steps.

Complete guide for deploying Aspasia in production environments.

## Table of Contents

1. [Local Development](#local-development)
2. [Docker Deployment](#docker-deployment)
3. [Cloud Platforms](#cloud-platforms)
4. [VPS / Self-Hosted](#vps--self-hosted)
5. [Production Checklist](#production-checklist)

## Local Development

### Quick Start

```bash
# Clone and setup
git clone <repo>
cd Aspasia
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Configure
cp .env.example .env
# Edit .env with your API keys

# Run
python -m aspasia.main
```

Access the web UI at `http://localhost:8000`

## Docker Deployment

### Build Docker Image

```bash
docker build -t aspasia:latest .
```

### Run with Docker Compose

```bash
# Copy and configure
cp .env.example .env
# Edit .env

# Start
docker-compose up -d

# View logs
docker-compose logs -f aspasia
```

### Docker Compose File

See `config/docker-compose.yml` for production setup with PostgreSQL and Redis.

## Cloud Platforms

### Railway.app

1. Connect your GitHub repo to Railway
2. Add environment variables in Railway dashboard:
   - `CLAUDE_API_KEY`
   - `TELEGRAM_BOT_TOKEN` (if using Telegram)
   - `ENVIRONMENT=production`

3. Set the start command:
   ```
   python -m aspasia.main
   ```

4. Deploy: `git push`

### Heroku

```bash
# Create app
heroku create aspasia-bot

# Set environment variables
heroku config:set CLAUDE_API_KEY=sk-ant-...
heroku config:set ENVIRONMENT=production

# Deploy
git push heroku main

# View logs
heroku logs -t
```

### Replit

1. Import GitHub repo to Replit
2. Configure `.env` with secrets
3. Set run command: `python -m aspasia.main`
4. Click "Run"

### AWS (via Elastic Beanstalk)

```bash
# Install EB CLI
pip install awsebcli

# Initialize
eb init -p python-3.11 aspasia

# Create environment
eb create aspasia-env

# Set environment variables
eb setenv CLAUDE_API_KEY=sk-ant-...

# Deploy
eb deploy
```

## VPS / Self-Hosted

### Prerequisites

- Ubuntu 20.04+ or similar Linux
- Python 3.10+
- Nginx or Apache (reverse proxy)
- PostgreSQL (optional but recommended)
- Redis (optional, for caching)

### Installation Steps

```bash
# 1. System setup
sudo apt update && sudo apt upgrade -y
sudo apt install -y python3.11 python3.11-venv git curl

# 2. Create app user
sudo useradd -m -s /bin/bash aspasia

# 3. Clone repository
cd /home/aspasia
sudo -u aspasia git clone <repo> app
cd app

# 4. Create virtual environment
sudo -u aspasia python3.11 -m venv venv
sudo -u aspasia venv/bin/pip install --upgrade pip

# 5. Install dependencies
sudo -u aspasia venv/bin/pip install -r requirements.txt

# 6. Configure
sudo -u aspasia cp .env.example .env
sudo nano /home/aspasia/app/.env  # Edit with your keys
```

### Systemd Service Setup

Create `/etc/systemd/system/aspasia.service`:

```ini
[Unit]
Description=Aspasia AI Bot
After=network.target

[Service]
Type=simple
User=aspasia
WorkingDirectory=/home/aspasia/app
Environment="PATH=/home/aspasia/app/venv/bin"
ExecStart=/home/aspasia/app/venv/bin/python -m aspasia.main
Restart=always
RestartSec=10

[Install]
WantedBy=multi-user.target
```

Enable and start:

```bash
sudo systemctl daemon-reload
sudo systemctl enable aspasia
sudo systemctl start aspasia
sudo systemctl status aspasia
```

### Nginx Reverse Proxy

Create `/etc/nginx/sites-available/aspasia`:

```nginx
upstream aspasia {
    server 127.0.0.1:8000;
}

server {
    listen 80;
    server_name your-domain.com;

    # Redirect to HTTPS
    return 301 https://$server_name$request_uri;
}

server {
    listen 443 ssl http2;
    server_name your-domain.com;

    ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
    ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;

    client_max_body_size 10M;

    location / {
        proxy_pass http://aspasia;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
    }

    # WebSocket support (if needed)
    location /ws {
        proxy_pass http://aspasia;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection "upgrade";
    }
}
```

Enable site:

```bash
sudo ln -s /etc/nginx/sites-available/aspasia /etc/nginx/sites-enabled/
sudo systemctl restart nginx
```

### SSL Certificate (Let's Encrypt)

```bash
sudo apt install -y certbot python3-certbot-nginx
sudo certbot certonly -d your-domain.com
# Certificate auto-renews via systemd timer
```

### PostgreSQL Setup

```bash
# Install
sudo apt install -y postgresql postgresql-contrib

# Create database and user
sudo -u postgres createdb aspasia
sudo -u postgres createuser aspasia -P
# Set password when prompted

# Update .env
DATABASE_URL=postgresql://aspasia:password@localhost/aspasia
```

### Monitoring

```bash
# View logs
sudo journalctl -u aspasia -f

# Monitor resource usage
top
# or
htop

# Check disk space
df -h

# Restart if needed
sudo systemctl restart aspasia
```

## Production Checklist

Before going live:

- [ ] Set `ENVIRONMENT=production` in `.env`
- [ ] Use strong, unique `WEB_API_KEY` if authentication needed
- [ ] Set `ALLOW_ADMIN_ENDPOINTS=false` for sensitive deployments
- [ ] Configure logging to files (check `LOG_FILE` setting)
- [ ] Setup HTTPS with valid certificate
- [ ] Use PostgreSQL instead of SQLite for production
- [ ] Configure Redis for caching and sessions
- [ ] Setup automated backups of database
- [ ] Configure monitoring and alerting
- [ ] Test failover and recovery procedures
- [ ] Review security headers and CORS settings
- [ ] Setup rate limiting on API endpoints
- [ ] Configure Telegram webhook (not polling) for production
- [ ] Use environment variables, never hardcode secrets
- [ ] Test all integrations before deploying
- [ ] Document deployment procedure
- [ ] Setup health check monitoring

## Troubleshooting

### Bot not responding
```bash
# Check service status
sudo systemctl status aspasia

# View recent logs
sudo journalctl -u aspasia -n 50

# Check API connectivity
curl http://localhost:8000/health
```

### High memory usage
- Increase `AGENT_MEMORY_SIZE` carefully
- Enable Redis for caching
- Monitor conversation history size
- Archive old conversations

### Slow responses
- Check Claude API status
- Review network latency
- Optimize database queries
- Enable caching with Redis

### Telegram bot not receiving messages
- Verify `TELEGRAM_BOT_TOKEN` is correct
- Check webhook URL is accessible
- Review Telegram logs: `sudo journalctl -u aspasia -f`
- Test webhook: `curl https://api.telegram.org/botYOUR_TOKEN/getMe`

## Performance Tuning

### Environment Variables for Scaling

```env
# Increase max tokens for longer responses
CLAUDE_MAX_TOKENS=4096

# Reduce memory overhead
AGENT_MEMORY_SIZE=25

# Adjust timeout for slower networks
AGENT_TIMEOUT_SECONDS=60

# Enable debug logging for diagnostics
LOG_LEVEL=DEBUG
```

### Database Optimization

```bash
# Backup regularly
pg_dump aspasia > backup-$(date +%Y%m%d).sql

# Archive old conversations
# Add script in /home/aspasia/scripts/archive.py

# Schedule with cron
0 2 * * * /home/aspasia/scripts/archive.sh
```

## Further Reading

- [System Architecture](./ARCHITECTURE.md)
- [API Documentation](./API.md)
- [Telegram Setup](./TELEGRAM.md)

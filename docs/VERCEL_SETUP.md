# Setup Vercel

## 1. Acesso

Vai a: https://vercel.com
- Clica "Sign Up"
- Escolhe "Continue with GitHub"
- Autentica e conecta GitHub

## 2. Deploy

- Clica "New Project"
- Procura `aspasia-bot` (do GitHub)
- Clica "Import"

## 3. Environment Variables

Na dashboard do Vercel:
- Vai a Settings → Environment Variables
- Adiciona:
  - `ANTHROPIC_API_KEY` = (tua chave Claude)
  - `TELEGRAM_BOT_TOKEN` = (teu token Telegram)

## 4. Deploy

Clica "Deploy"

Espera por "Ready" ✓

URL será tipo: https://aspasia-bot.vercel.app

## 5. Update Telegram Webhook

```bash
curl -X POST https://api.telegram.org/bot<TELEGRAM_BOT_TOKEN>/setWebhook \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://aspasia-bot.vercel.app/api/telegram"}'
```

(Muda a URL conforme Vercel dá)

## 6. Website Widget

No teu site (bash.pt), muda:

```javascript
const API_URL = 'https://aspasia-bot.vercel.app';
```

Pronto! 🎉

# Aspasia - Setup Checklist ✓

## ✅ O que foi feito

- [x] Bot core (Node.js + Claude API)
- [x] Telegram integration (commands + messages)
- [x] Web API (Express server)
- [x] GitHub repository
- [x] Vercel config (`vercel.json`)
- [x] Environment variables (`ANTHROPIC_API_KEY`, `TELEGRAM_BOT_TOKEN`)

## 📋 Próximos passos

### 1. Deploy em Vercel
- [ ] Vai a https://vercel.com
- [ ] Sign in com GitHub
- [ ] Novo projeto → `aspasia-bot`
- [ ] Adiciona Environment Variables:
  - `ANTHROPIC_API_KEY`
  - `TELEGRAM_BOT_TOKEN`
- [ ] Deploy

### 2. Configurar Telegram Webhook
Uma vez que Vercel dá a URL (tipo `https://aspasia-bot.vercel.app`):

```bash
curl -X POST https://api.telegram.org/bot{TOKEN}/setWebhook \
  -H 'Content-Type: application/json' \
  -d '{"url": "https://aspasia-bot.vercel.app/api/telegram"}'
```

### 3. Integrar no Website
No `bash.pt`, adiciona o widget HTML:
- Copia código do `VERCEL_SETUP.md`
- Muda `API_URL = 'https://aspasia-bot.vercel.app'`
- Adiciona ao teu site

### 4. Testar
- Abre Telegram
- Procura `@AspasiaBAshBot`
- Envia `/start`
- Deve responder!

## 🔗 Links importantes

| Recurso | URL |
|---------|-----|
| GitHub | https://github.com/rafpt/aspasia-bot |
| Vercel | https://vercel.com |
| Telegram Bot | @AspasiaBAshBot |
| API (depois) | https://aspasia-bot.vercel.app |

## 🆘 Troubleshooting

**Bot não responde no Telegram?**
- Verifica webhook com: `curl https://api.telegram.org/botTOKEN/getWebhookInfo`
- Vercel logs: `vercel logs aspasia-bot`

**API retorna erro?**
- Verifica vars no Vercel Dashboard
- Logs: https://vercel.com/dashboard → aspasia-bot → Logs

**Widget não funciona no site?**
- Abre DevTools (F12)
- Console → vê erros CORS
- Vercel precisa de CORS headers (adicionar se needed)

---

**Tudo pronto. Prossegue com Vercel!** 🚀

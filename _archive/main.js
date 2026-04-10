import 'dotenv/config.js';
import Anthropic from '@anthropic-ai/sdk';
import { Telegraf } from 'telegraf';
import express from 'express';

const app = express();
app.use(express.json());

// Initialize clients
const anthropic = new Anthropic({
  apiKey: process.env.ANTHROPIC_API_KEY,
});

const bot = new Telegraf(process.env.TELEGRAM_BOT_TOKEN);

// Agent state
const conversationHistory = {};
const AGENT_NAME = process.env.AGENT_NAME || 'Aspasia';
const MODEL = process.env.AGENT_MODEL || 'claude-3-5-sonnet-20241022';

// System prompt
const systemPrompt = `You are ${AGENT_NAME}, an autonomous AI assistant.
You are helpful, direct, and intelligent. You engage in thoughtful conversation and can help with a wide variety of tasks.
Always be respectful and honest. If you don't know something, say so.
You have memory of the current conversation and can reference previous messages.`;

// Chat function
async function chat(userId, userMessage) {
  if (!conversationHistory[userId]) {
    conversationHistory[userId] = [];
  }

  // Add user message
  conversationHistory[userId].push({
    role: 'user',
    content: userMessage,
  });

  try {
    const response = await anthropic.messages.create({
      model: MODEL,
      max_tokens: 2048,
      system: systemPrompt,
      messages: conversationHistory[userId],
    });

    const assistantMessage = response.content[0].text;

    // Add assistant response to history
    conversationHistory[userId].push({
      role: 'assistant',
      content: assistantMessage,
    });

    return assistantMessage;
  } catch (error) {
    console.error('Chat error:', error);
    return 'Sorry, I encountered an error. Please try again.';
  }
}

// Telegram Bot Handlers
bot.command('start', (ctx) => {
  ctx.reply(`Hello! I'm ${AGENT_NAME}. How can I help you today?`);
});

bot.command('help', (ctx) => {
  const helpText = `I'm ${AGENT_NAME}, your AI assistant.

Available commands:
/start - Start conversation
/help - Show this help message
/reset - Reset conversation history
/status - Show bot status

Just type any message to chat with me!`;
  ctx.reply(helpText);
});

bot.command('reset', (ctx) => {
  const userId = ctx.from.id;
  conversationHistory[userId] = [];
  ctx.reply("Conversation history cleared. Let's start fresh!");
});

bot.command('status', (ctx) => {
  const userId = ctx.from.id;
  const messageCount = conversationHistory[userId] ? conversationHistory[userId].length : 0;
  const statusText = `Status: Online ✓
Agent: ${AGENT_NAME}
Model: ${MODEL}
Conversation messages: ${messageCount}`;
  ctx.reply(statusText);
});

bot.on('message', async (ctx) => {
  const userId = ctx.from.id;
  const userMessage = ctx.message.text;

  // Show typing indicator
  await ctx.sendChatAction('typing');

  try {
    const response = await chat(userId, userMessage);

    // Send response (split if too long)
    if (response.length > 4096) {
      const parts = response.match(/[\s\S]{1,4096}/g);
      for (const part of parts) {
        await ctx.reply(part);
      }
    } else {
      await ctx.reply(response);
    }
  } catch (error) {
    console.error('Message handler error:', error);
    await ctx.reply('Sorry, I encountered an error. Please try again.');
  }
});

// Web API Endpoints
app.get('/', (req, res) => {
  res.json({
    name: 'Aspasia API',
    version: '1.0.0',
    status: 'running',
  });
});

app.get('/api/status', (req, res) => {
  res.json({
    status: 'online',
    agent_name: AGENT_NAME,
    model: MODEL,
    uptime: 'running',
  });
});

app.post('/api/chat', async (req, res) => {
  try {
    const { message, session_id } = req.body;
    const userId = session_id || 'default';

    if (!message) {
      return res.status(400).json({ error: 'Message required' });
    }

    const response = await chat(userId, message);
    res.json({
      message: response,
      session_id: userId,
    });
  } catch (error) {
    console.error('Chat endpoint error:', error);
    res.status(500).json({ error: 'Failed to process message' });
  }
});

app.get('/api/history', (req, res) => {
  const { session_id } = req.query;
  const userId = session_id || 'default';
  res.json({
    history: conversationHistory[userId] || [],
  });
});

app.post('/api/reset', (req, res) => {
  const { session_id } = req.body;
  const userId = session_id || 'default';
  conversationHistory[userId] = [];
  res.json({ status: 'conversation reset' });
});

app.post('/api/telegram', (req, res) => {
  // Telegram webhook endpoint
  res.json({ ok: true });
});

app.get('/api/health', (req, res) => {
  res.json({
    status: 'healthy',
    service: 'Aspasia',
    timestamp: new Date().toISOString(),
  });
});

// Start servers
const PORT = process.env.PORT || 3000;

(async () => {
  console.log(`Starting ${AGENT_NAME}...`);
  console.log(`API Server: localhost:${PORT}`);
  console.log(`Model: ${MODEL}`);
  console.log(`Telegram Bot: Enabled`);

  // Start Telegram bot
  try {
    await bot.launch();
    console.log('Telegram bot started');
  } catch (error) {
    console.error('Telegram bot error:', error);
  }

  // Start Express server
  app.listen(PORT, () => {
    console.log(`Web API listening on port ${PORT}`);
  });

  // Graceful shutdown
  process.once('SIGINT', () => bot.stop('SIGINT'));
  process.once('SIGTERM', () => bot.stop('SIGTERM'));
})();

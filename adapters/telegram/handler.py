"""
Telegram adapter.
Receives Telegram events → calls core.Agent → replies.
Knows nothing about profiles or business logic.
"""

import logging
from typing import Optional

from telegram import Update, BotCommand
from telegram.ext import (
    Application,
    CommandHandler,
    MessageHandler,
    filters,
    ContextTypes,
)

from core.agent import Agent

logger = logging.getLogger(__name__)


class TelegramAdapter:
    """Bridges python-telegram-bot with core.Agent."""

    def __init__(self, token: str, agent: Agent):
        self.token = token
        self.agent = agent
        self.app: Optional[Application] = None

    # ── Setup ────────────────────────────────────────────────────────────────

    async def initialize(self) -> None:
        self.app = Application.builder().token(self.token).build()

        self.app.add_handler(CommandHandler("start",  self._cmd_start))
        self.app.add_handler(CommandHandler("help",   self._cmd_help))
        self.app.add_handler(CommandHandler("reset",  self._cmd_reset))
        self.app.add_handler(CommandHandler("status", self._cmd_status))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self._on_message)
        )
        await self._set_commands()
        logger.info(f"TelegramAdapter ready (agent={self.agent.name})")


    # ── Commands ─────────────────────────────────────────────────────────────

    async def _cmd_start(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            f"Olá! Sou {self.agent.name}. Como posso ajudar?"
        )

    async def _cmd_help(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        await update.message.reply_text(
            f"{self.agent.name} — comandos disponíveis:\n"
            "/start  — iniciar\n"
            "/reset  — limpar histórico\n"
            "/status — estado do bot\n"
            "/help   — esta mensagem\n\n"
            "Escreve qualquer mensagem para conversar."
        )

    async def _cmd_reset(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        user_id = str(update.effective_user.id)
        self.agent.clear_history(user_id)
        await update.message.reply_text("Histórico limpo. Podemos recomeçar!")

    async def _cmd_status(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        try:
            health = await self.agent.health_check()
            stats  = self.agent.stats()
            text = (
                f"*{self.agent.name} — estado*\n\n"
                f"Agent: {health['agent']}\n"
                f"LLM: {health['llm']}\n"
                f"Utilizadores: {stats['memory']['total_users']}\n"
                f"Mensagens: {stats['memory']['total_messages']}"
            )
            await update.message.reply_text(text, parse_mode="Markdown")
        except Exception as e:
            await update.message.reply_text(f"Erro ao obter estado: {e}")


    # ── Message handler ──────────────────────────────────────────────────────

    async def _on_message(self, update: Update, ctx: ContextTypes.DEFAULT_TYPE) -> None:
        user_id   = str(update.effective_user.id)
        user_name = update.effective_user.first_name or "User"
        text      = update.message.text

        await update.message.chat.send_action("typing")

        try:
            response = await self.agent.process_message(
                user_id=user_id,
                message=text,
                context={"platform": "telegram", "user_name": user_name},
            )
            reply = response.text
            # Telegram max message length = 4096 chars
            chunks = [reply[i:i+4096] for i in range(0, len(reply), 4096)]
            for chunk in chunks:
                await update.message.reply_text(chunk)
        except Exception as e:
            logger.error(f"Telegram message error: {e}", exc_info=True)
            await update.message.reply_text("Ocorreu um erro. Tenta de novo.")

    # ── Internal ─────────────────────────────────────────────────────────────

    async def _set_commands(self) -> None:
        if not self.app:
            return
        commands = [
            BotCommand("start",  "Iniciar conversa"),
            BotCommand("help",   "Ajuda"),
            BotCommand("reset",  "Limpar histórico"),
            BotCommand("status", "Estado do bot"),
        ]
        try:
            await self.app.bot.set_my_commands(commands)
        except Exception as e:
            logger.warning(f"Could not set bot commands: {e}")

    # ── Run modes ────────────────────────────────────────────────────────────

    async def run_polling(self) -> None:
        if not self.app:
            raise RuntimeError("Call initialize() first")
        logger.info("Telegram polling started")
        await self.app.run_polling(allowed_updates=Update.ALL_TYPES)

    async def run_webhook(self, webhook_url: str) -> None:
        if not self.app:
            raise RuntimeError("Call initialize() first")
        logger.info(f"Telegram webhook: {webhook_url}")
        await self.app.run_webhook(webhook_url=webhook_url)

    async def stop(self) -> None:
        if self.app:
            await self.app.stop()
            logger.info("Telegram bot stopped")

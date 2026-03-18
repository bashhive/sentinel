"""
Telegram bot integration for Aspasia.

Handles incoming Telegram messages and sends responses back.
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

from aspasia.agent.core import Agent
from aspasia.config import Config

logger = logging.getLogger(__name__)


class TelegramHandler:
    """Handler for Telegram bot integration."""

    def __init__(self, config: Config, agent: Agent):
        """
        Initialize Telegram handler.

        Args:
            config: Configuration instance
            agent: Agent instance
        """
        self.config = config
        self.agent = agent
        self.bot_token = config.telegram_bot_token
        self.app: Optional[Application] = None

    async def initialize(self) -> None:
        """Initialize Telegram application."""
        if not self.bot_token:
            logger.warning("TELEGRAM_BOT_TOKEN not set, Telegram integration disabled")
            return

        logger.info("Initializing Telegram bot...")

        self.app = Application.builder().token(self.bot_token).build()

        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start_command))
        self.app.add_handler(CommandHandler("help", self.help_command))
        self.app.add_handler(CommandHandler("clear", self.clear_command))
        self.app.add_handler(CommandHandler("status", self.status_command))
        self.app.add_handler(
            MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message)
        )

        # Set commands in Telegram
        await self.set_bot_commands()

        logger.info("Telegram bot initialized")

    async def start_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /start command."""
        await update.message.reply_text(
            "Hello! I'm Aspasia, an autonomous AI assistant. "
            "Send me a message and I'll respond!\n\n"
            "Commands:\n"
            "/help - Show help\n"
            "/clear - Clear conversation history\n"
            "/status - Show bot status"
        )

    async def help_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /help command."""
        help_text = (
            "Aspasia - Autonomous AI Assistant\n\n"
            "I can help you with:\n"
            "• Answering questions\n"
            "• Having conversations\n"
            "• Providing information\n"
            "• Problem-solving\n\n"
            "Commands:\n"
            "/start - Start conversation\n"
            "/clear - Clear history\n"
            "/status - Show status\n"
            "/help - Show this message"
        )
        await update.message.reply_text(help_text)

    async def clear_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /clear command."""
        user_id = str(update.effective_user.id)
        self.agent.clear_user_history(user_id)
        await update.message.reply_text("Conversation history cleared.")

    async def status_command(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle /status command."""
        try:
            health = await self.agent.health_check()
            stats = self.agent.get_stats()

            status_text = f"*Aspasia Status*\n\n"
            status_text += f"Agent: {health['agent']}\n"
            status_text += f"Memory: {health['memory']}\n"
            status_text += f"Claude API: {health['claude']}\n"
            status_text += f"\nUsers tracked: {stats['memory']['total_users']}\n"
            status_text += f"Messages: {stats['memory']['total_messages']}"

            await update.message.reply_text(
                status_text, parse_mode="Markdown", disable_notification=True
            )
        except Exception as e:
            await update.message.reply_text(f"Status check failed: {str(e)}")

    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE):
        """Handle regular messages."""
        user_id = str(update.effective_user.id)
        user_name = update.effective_user.first_name or "User"
        message_text = update.message.text

        logger.info(f"Telegram message from {user_id}: {message_text[:50]}...")

        # Show typing indicator
        await update.message.chat.send_action("typing")

        try:
            # Process message through agent
            response = await self.agent.process_message(
                user_id=user_id,
                message=message_text,
                context={
                    "platform": "telegram",
                    "user_name": user_name,
                    "chat_id": update.message.chat_id,
                },
            )

            # Send response
            await update.message.reply_text(
                response.text, disable_notification=False, parse_mode="Markdown"
            )

        except Exception as e:
            logger.error(f"Error handling Telegram message: {str(e)}", exc_info=True)
            await update.message.reply_text(
                f"Sorry, I encountered an error: {str(e)}"
            )

    async def set_bot_commands(self) -> None:
        """Set bot commands in Telegram."""
        if not self.app:
            return

        commands = [
            BotCommand("start", "Start the conversation"),
            BotCommand("help", "Show help message"),
            BotCommand("clear", "Clear conversation history"),
            BotCommand("status", "Show bot status"),
        ]

        try:
            await self.app.bot.set_my_commands(commands)
            logger.info("Bot commands set")
        except Exception as e:
            logger.error(f"Failed to set bot commands: {str(e)}")

    async def run_polling(self) -> None:
        """Run bot with polling."""
        if not self.app:
            logger.error("Telegram app not initialized")
            return

        logger.info("Starting Telegram bot polling...")
        await self.app.run_polling(allowed_updates=Update.ALL_TYPES)

    async def run_webhook(self, webhook_url: str) -> None:
        """Run bot with webhook."""
        if not self.app:
            logger.error("Telegram app not initialized")
            return

        logger.info(f"Starting Telegram bot with webhook: {webhook_url}")
        await self.app.run_webhook(webhook_url=webhook_url)

    async def stop(self) -> None:
        """Stop the bot."""
        if self.app:
            await self.app.stop()
            logger.info("Telegram bot stopped")

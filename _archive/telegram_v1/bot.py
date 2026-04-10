"""
Telegram Bot Handler for Aspasia
"""

from telegram import Update
from telegram.ext import Application, CommandHandler, MessageHandler, filters, ContextTypes
from config import settings
from agent.core import get_agent
import logging


# Set up logging
logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)


class AspasiaTelegramBot:
    """Telegram bot integration for Aspasia"""
    
    def __init__(self):
        self.token = settings.telegram_bot_token
        self.app = None
        self.agent = get_agent()
    
    async def start(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /start command"""
        await update.message.reply_text(
            f"Hello! I'm {self.agent.name}. How can I help you today?"
        )
    
    async def help(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /help command"""
        help_text = f"""I'm {self.agent.name}, your AI assistant.

Available commands:
/start - Start conversation
/help - Show this help message
/reset - Reset conversation history
/status - Show bot status

Just type any message to chat with me!"""
        await update.message.reply_text(help_text)
    
    async def reset(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /reset command"""
        self.agent.reset_conversation()
        await update.message.reply_text("Conversation history cleared. Let's start fresh!")
    
    async def status(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle /status command"""
        messages_count = len(self.agent.get_history())
        status_text = f"""Status: Online ✓
Agent: {self.agent.name}
Model: {self.agent.model}
Conversation messages: {messages_count}"""
        await update.message.reply_text(status_text)
    
    async def handle_message(self, update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        """Handle regular messages"""
        user_message = update.message.text
        
        # Show typing indicator
        await context.bot.send_chat_action(
            chat_id=update.effective_chat.id,
            action="typing"
        )
        
        try:
            # Get response from agent
            response = self.agent.chat(user_message)
            
            # Split long messages (Telegram limit is 4096 chars)
            if len(response) > 4096:
                parts = [response[i:i+4096] for i in range(0, len(response), 4096)]
                for part in parts:
                    await update.message.reply_text(part)
            else:
                await update.message.reply_text(response)
        
        except Exception as e:
            logger.error(f"Error processing message: {e}")
            await update.message.reply_text(
                "Sorry, I encountered an error. Please try again."
            )
    
    async def setup_application(self):
        """Set up the Telegram application"""
        self.app = Application.builder().token(self.token).build()
        
        # Add handlers
        self.app.add_handler(CommandHandler("start", self.start))
        self.app.add_handler(CommandHandler("help", self.help))
        self.app.add_handler(CommandHandler("reset", self.reset))
        self.app.add_handler(CommandHandler("status", self.status))
        self.app.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, self.handle_message))
        
        return self.app


async def create_bot() -> AspasiaTelegramBot:
    """Create and set up the Telegram bot"""
    bot = AspasiaTelegramBot()
    await bot.setup_application()
    return bot

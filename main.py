# =============================================
# Developer : ✘ 𝙍𝘼𝙑𝙀𝙉
# Telegram  : @P_X_24
# =============================================

import sys
import subprocess
import logging
import os

# NOTE: Dependency imports must succeed before loading configuration or handlers
try:
    from telegram import Update
    from telegram.ext import Application, CallbackQueryHandler, CommandHandler, MessageHandler, filters
except ImportError as e:
    print(f"Required library missing: {e}. Attempting install...")
    try:
        subprocess.check_call([sys.executable, "-m", "pip", "install", 
                               "python-telegram-bot", "telethon", "requests", "httpx"])
        print("Dependencies installed. Please restart the script.")
    except Exception as install_err:
        print(f"Failed to automatically install dependencies: {install_err}")
    sys.exit(1)


import config
import data
from bot import start, admin_panel, echoMaker, button

logger = logging.getLogger(__name__)

def main() -> None:
    """Start the bot."""
    
    
    if config.BOT_TOKEN == "YOUR_BOT_TOKEN":
        logger.error("BOT_TOKEN is missing. Exiting.")
        sys.exit(1)

    
    application = Application.builder().token(config.BOT_TOKEN).build()

    # Handlers
    application.add_handler(CommandHandler("start", start))
    application.add_handler(CommandHandler("admin", admin_panel))
    
    # Message handlers (filters.ALL catches text and media/files for spam command)
    application.add_handler(MessageHandler(filters.TEXT & ~filters.COMMAND, echoMaker))
    application.add_handler(MessageHandler(filters.ALL & ~filters.COMMAND & ~filters.TEXT, echoMaker))
    
    
    application.add_handler(CallbackQueryHandler(button))

    # Run the bot
    print("Starting bot polling...")
    application.run_polling(allowed_updates=Update.ALL_TYPES)


if __name__ == "__main__":
    
    main()
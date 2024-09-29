# commands/cmd_start.py

from telegram import Update
from telegram.ext import ContextTypes
import logging

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Welcome to your event manager bot!')
    logging.info("Bot started by user.")

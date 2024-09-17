from telegram import Update
from telegram.ext import ContextTypes
import logging

async def start(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text('Bot started!')
    logging.info("Bot started by user.")

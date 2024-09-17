# commands/cmd_settimezone.py

from telegram import Update
from telegram.ext import (
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
import pytz
import logging

ASK_TIMEZONE = 1

# Rename function to set_timezone_command
async def set_timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please send me your timezone in the format 'Region/City', e.g., 'Europe/Berlin'."
    )
    return ASK_TIMEZONE

async def receive_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tz = update.message.text.strip()
    if user_tz in pytz.all_timezones:
        context.user_data['timezone'] = user_tz
        await update.message.reply_text(f"Timezone set to {user_tz}.")
        return ConversationHandler.END
    else:
        await update.message.reply_text(
            "Invalid timezone. Please send a valid timezone in the format 'Region/City', e.g., 'Europe/Berlin'."
        )
        return ASK_TIMEZONE

async def cancel(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text("Timezone setting canceled.")
    return ConversationHandler.END

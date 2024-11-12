# commands/cmd_settimezone.py

from telegram import Update
from telegram.ext import ContextTypes, ConversationHandler
import pytz
from telegram import KeyboardButton, ReplyKeyboardMarkup
from timezonefinder import TimezoneFinder

ASK_TIMEZONE = 1

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
    ASK_LOCATION = 2

    async def set_timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
        location_keyboard = [[KeyboardButton("Send Location", request_location=True)]]
        reply_markup = ReplyKeyboardMarkup(location_keyboard, one_time_keyboard=True)
        await update.message.reply_text(
            "Please send me your location or type your timezone in the format 'Region/City', e.g., 'Europe/Berlin'.",
            reply_markup=reply_markup
        )
        return ASK_TIMEZONE

    async def receive_location(update: Update, context: ContextTypes.DEFAULT_TYPE):
        user_location = update.message.location
        if user_location:
            tf = TimezoneFinder()
            user_tz = tf.timezone_at(lng=user_location.longitude, lat=user_location.latitude)
            if user_tz:
                context.user_data['timezone'] = user_tz
                await update.message.reply_text(f"Timezone set to {user_tz}.")
                return ConversationHandler.END
            else:
                await update.message.reply_text("Could not determine timezone from location. Please try again.")
                return ASK_LOCATION
        else:
            await update.message.reply_text("Please send a valid location.")
            return ASK_LOCATION

    # Add the new states to the conversation handler
    conversation_handler = ConversationHandler(
        entry_points=[CommandHandler('settimezone', set_timezone_command)],
        states={
            ASK_TIMEZONE: [MessageHandler(Filters.text & ~Filters.command, receive_timezone)],
            ASK_LOCATION: [MessageHandler(Filters.location, receive_location)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
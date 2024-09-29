# telegram_bot.py

import logging
import os
import base64  # Import base64 for encoding/decoding UIDs

from telegram import (
    InlineKeyboardButton,
    InlineKeyboardMarkup,
    Update,
    BotCommand,
)
from telegram.ext import (
    ApplicationBuilder,
    CommandHandler,
    CallbackQueryHandler,
    ContextTypes,
    ConversationHandler,
    MessageHandler,
    filters,
)
from dotenv import load_dotenv
from datetime import datetime, timedelta, time
import pytz
import aiohttp  # Use aiohttp for asynchronous HTTP requests

# Load environment variables from .env file
load_dotenv()

# Configuration variables
TELEGRAM_TOKEN = os.getenv('TELEGRAM_TOKEN')
CHAT_ID = int(os.getenv('CHAT_ID'))
ICS_URL = os.getenv('ICS_URL')
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'UTC')

# Configure logging
logging.basicConfig(
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s',
    level=logging.INFO
)

# Import command handlers and utilities
from commands.cmd_start import start
from commands.cmd_showtoday import show_today
from commands.cmd_settimezone import (
    set_timezone_command,
    receive_timezone,
    cancel,
    ASK_TIMEZONE,
)
from commands.utils import (
    fetch_events,
    should_notify,
    extract_completion_url,
    format_event_message,
    get_next_event,
)

# Dictionary to store user data
user_data = {}

# Function to handle callback queries
async def handle_callback_query(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    data = query.data.split(':')
    action = data[0]
    encoded_event_uid = data[1]
    event_uid = base64.urlsafe_b64decode(encoded_event_uid.encode()).decode()

    # Acknowledge the callback query
    await query.answer()

    if action == 'toggle':
        # Toggle expand/collapse
        is_expanded = data[2] == 'True'
        await update_event_message(
            query, context, event_uid, not is_expanded, is_completed=False
        )
    elif action == 'complete':
        # Mark event as completed
        await mark_event_completed(query, context, event_uid)

async def update_event_message(query, context, event_uid, is_expanded, is_completed):
    # Fetch the specific event
    events = await fetch_events()
    event = next((e for e in events if e['uid'] == event_uid), None)
    if not event:
        await query.edit_message_text("Event not found.")
        return

    # Update the message with the completed status and inline buttons
    message, reply_markup = format_event_message(
        event, is_expanded=is_expanded, is_completed=is_completed
    )

    # Use `query.edit_message_text` to update the original message in place
    try:
        await query.edit_message_text(
            text=message, reply_markup=reply_markup, parse_mode='Markdown'
        )
    except Exception as e:
        logging.error(f"Failed to edit message: {e}")


async def mark_event_completed(query, context, event_uid):
    # Fetch the specific event
    events = await fetch_events()
    event = next((e for e in events if e['uid'] == event_uid), None)
    if not event:
        await query.edit_message_text("Event not found.")
        return

    # Find the completion URL
    completion_url = extract_completion_url(event['description'])
    if completion_url:
        # Make the API call to mark the task as completed
        try:
            async with aiohttp.ClientSession() as session:
                async with session.get(completion_url) as response:
                    if response.status == 200:
                        # Update the message to show completion using `edit_message_text`
                        await update_event_message(
                            query, context, event_uid, is_expanded=True, is_completed=True
                        )
                        # No need to send a new message here
                    else:
                        await query.edit_message_text(
                            f"Failed to mark the task as completed. Status code: {response.status}"
                        )
        except Exception as e:
            logging.error(f"Error making API call: {e}")
            await query.edit_message_text(
                "An error occurred while marking the task as completed."
            )
    else:
        await query.edit_message_text("No completion URL found for this task.")

async def send_event_reminders(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    chat_id = CHAT_ID
    events = await fetch_events()

    # Use the user's timezone or default
    user_tz_name = user_data.get(chat_id, {}).get('timezone', DEFAULT_TIMEZONE)
    user_tz = pytz.timezone(user_tz_name)
    now = datetime.now(user_tz)

    for event in events:
        event_start = event['dtstart']
        if event_start.tzinfo is None:
            event_start = user_tz.localize(event_start)
        else:
            event_start = event_start.astimezone(user_tz)

        notify_time_start = event_start - timedelta(minutes=15)
        notify_time_end = event_start + timedelta(minutes=15)

        if notify_time_start <= now <= notify_time_end:
            if should_notify('reminder_' + event['uid']):
                message, reply_markup = format_event_message(
                    event, is_expanded=False, is_completed=False
                )
                await bot.send_message(
                    chat_id=chat_id,
                    text="Your next item:\n\n" + message,
                    reply_markup=reply_markup,
                    parse_mode='Markdown'
                )
                logging.info(f"Sent reminder for event UID: {event['uid']}")

# Set bot commands
async def set_bot_commands(application):
    commands = [
        BotCommand('start', 'Start the bot'),
        BotCommand('showtoday', "Show today's events"),
        BotCommand('settimezone', 'Set your timezone'),
    ]
    await application.bot.set_my_commands(commands)

# Startup function
async def startup(application):
    await set_bot_commands(application)

if __name__ == '__main__':
    application = (
        ApplicationBuilder()
        .token(TELEGRAM_TOKEN)
        .post_init(startup)
        .build()
    )

    # Add command handlers
    application.add_handler(CommandHandler('start', start))
    application.add_handler(CommandHandler('showtoday', show_today))

    # Add a CallbackQueryHandler
    application.add_handler(CallbackQueryHandler(handle_callback_query))

    # Conversation handler for /settimezone
    conv_handler = ConversationHandler(
        entry_points=[CommandHandler('settimezone', set_timezone_command)],
        states={
            ASK_TIMEZONE: [MessageHandler(filters.TEXT & ~filters.COMMAND, receive_timezone)],
        },
        fallbacks=[CommandHandler('cancel', cancel)],
    )
    application.add_handler(conv_handler)

    # Schedule tasks
    job_queue = application.job_queue

    # Schedule reminders every minute
    job_queue.run_repeating(
        send_event_reminders,
        interval=60,
        first=0,
        name='event_reminders'
    )

    # Start the bot
    logging.info("Bot is starting...")
    application.run_polling()

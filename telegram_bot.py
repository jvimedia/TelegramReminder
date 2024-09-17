import logging
import os

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update, BotCommand
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
import requests

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
from commands.utils import fetch_events, should_notify, extract_completion_url

# Dictionary to store user timezones (for a single user in this case)
user_timezone = {}

# Function to handle event completion from callback query
async def mark_event_completed(update: Update, context: ContextTypes.DEFAULT_TYPE):
    query = update.callback_query
    task_uid = query.data

    # Acknowledge the callback query
    await query.answer()

    # Find the completion URL based on the task UID
    events = fetch_events()
    completion_url = None
    for event in events:
        if event['uid'] == task_uid:
            completion_url = extract_completion_url(event['description'])
            break

    if completion_url:
        # Make the API call to mark the task as completed
        try:
            response = requests.get(completion_url)
            if response.status_code == 200:
                await query.edit_message_text(f"The task has been marked as completed.")
            else:
                await query.edit_message_text(f"Failed to mark the task as completed. Status code: {response.status_code}")
        except Exception as e:
            logging.error(f"Error making API call: {e}")
            await query.edit_message_text(f"An error occurred while marking the task as completed.")
    else:
        await query.edit_message_text("No completion URL found for this task.")


async def send_morning_notifications(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    chat_id = CHAT_ID
    events = fetch_events()

    # Use the user's timezone or default
    user_tz_name = user_timezone.get(chat_id, DEFAULT_TIMEZONE)
    user_tz = pytz.timezone(user_tz_name)
    now = datetime.now(user_tz)

    for event in events:
        event_start = event['dtstart']
        if isinstance(event_start, datetime):
            if event_start.tzinfo is None:
                event_start = user_tz.localize(event_start)
            else:
                event_start = event_start.astimezone(user_tz)

            if event_start.date() == now.date():
                if should_notify('morning_' + event['uid']):
                    message = (
                        f"Good morning! You have an upcoming event:\n\n"
                        f"*{event['summary']}* at {event_start.strftime('%H:%M')} {user_tz_name}"
                    )
                    await bot.send_message(chat_id=chat_id, text=message, parse_mode='Markdown')
                    logging.info(f"Sent morning notification for event UID: {event['uid']}")

async def send_event_completion_prompt(context: ContextTypes.DEFAULT_TYPE):
    bot = context.bot
    chat_id = CHAT_ID
    events = fetch_events()

    # Use the user's timezone or default
    user_tz_name = user_timezone.get(chat_id, DEFAULT_TIMEZONE)
    user_tz = pytz.timezone(user_tz_name)
    now = datetime.now(user_tz)

    for event in events:
        event_end = event['dtend']
        if isinstance(event_end, datetime):
            if event_end.tzinfo is None:
                event_end = user_tz.localize(event_end)
            else:
                event_end = event_end.astimezone(user_tz)

            notify_time_start = event_end - timedelta(minutes=30)
            notify_time_end = event_end + timedelta(minutes=30)

            if notify_time_start <= now <= notify_time_end:
                if should_notify('event_' + event['uid']):
                    message = f"Have you completed the event:\n\n*{event['summary']}*?"
                    url = extract_completion_url(event['description'])
                    if url:
                        button = InlineKeyboardButton("Mark as Completed", url=url)
                        reply_markup = InlineKeyboardMarkup([[button]])
                        await bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            reply_markup=reply_markup,
                            parse_mode='Markdown'
                        )
                        logging.info(f"Sent completion prompt for event UID: {event['uid']}")
                    else:
                        await bot.send_message(
                            chat_id=chat_id,
                            text=message,
                            parse_mode='Markdown'
                        )
                        logging.warning(f"No URL found in event UID: {event['uid']}")

# Handlers for the /settimezone command
ASK_TIMEZONE = 1  # Define the state for ConversationHandler

async def set_timezone_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    await update.message.reply_text(
        "Please send me your timezone in the format 'Region/City', e.g., 'Europe/Berlin'."
    )
    return ASK_TIMEZONE

async def receive_timezone(update: Update, context: ContextTypes.DEFAULT_TYPE):
    user_tz = update.message.text.strip()
    if user_tz in pytz.all_timezones:
        user_timezone[update.effective_chat.id] = user_tz
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

# Set bot commands
async def set_bot_commands(application):
    commands = [
        BotCommand('start', 'Start the bot'),
        BotCommand('showtoday', 'Show today\'s events'),
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

    # Add a CallbackQueryHandler to handle "Done?" button clicks
    application.add_handler(CallbackQueryHandler(mark_event_completed))

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

    # Schedule morning notifications at 8 AM UTC
    job_queue.run_daily(
        send_morning_notifications,
        time=time(8, 0, tzinfo=pytz.utc),
        name='morning_notifications'
    )

    # Check for event completion prompts every 5 minutes
    job_queue.run_repeating(
        send_event_completion_prompt,
        interval=300,
        first=0,
        name='event_completion_prompts'
    )

    # Start the bot
    logging.info("Bot is starting...")
    application.run_polling()

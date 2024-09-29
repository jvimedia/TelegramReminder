# commands/cmd_showtoday.py

from telegram import Update
from telegram.ext import ContextTypes
from datetime import datetime
from .utils import fetch_events, format_event_message
import pytz
import os
import logging

# Load the default timezone from .env or use 'UTC' if not set
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'UTC')

async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Fetch events from the ICS calendar
        events = await fetch_events()

        # Get the user's timezone from context or use default
        user_tz_name = context.user_data.get('timezone', DEFAULT_TIMEZONE)
        user_tz = pytz.timezone(user_tz_name)
        now = datetime.now(user_tz)
        today_events = []

        for event in events:
            event_start = event['dtstart']

            # Ensure event_start is timezone-aware
            if event_start.tzinfo is None:
                event_start = user_tz.localize(event_start)
            else:
                event_start = event_start.astimezone(user_tz)

            # Compare event date with current date in user's timezone
            if event_start.date() == now.date():
                today_events.append(event)

        if today_events:
            for event in today_events:
                message, reply_markup = format_event_message(
                    event, is_expanded=False, is_completed=False
                )
                await update.message.reply_text(
                    message, reply_markup=reply_markup, parse_mode='Markdown'
                )
        else:
            await update.message.reply_text("You have no events scheduled for today.")
    except Exception as e:
        logging.error(f"Error in show_today: {e}")
        await update.message.reply_text("An error occurred while fetching today's events.")

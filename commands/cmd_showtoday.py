from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ContextTypes
from datetime import datetime
from .utils import fetch_events, extract_completion_url
import pytz
import os
import logging

# Load the default timezone from .env or use 'UTC' if not set
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'UTC')

async def show_today(update: Update, context: ContextTypes.DEFAULT_TYPE):
    try:
        # Fetch events from the ICS calendar
        events = fetch_events()

        # Get the user's timezone from context or use default
        user_tz_name = context.user_data.get('timezone', DEFAULT_TIMEZONE)
        user_tz = pytz.timezone(user_tz_name)
        now = datetime.now(user_tz)
        today_events = []

        for event in events:
            event_start = event['dtstart']
            event_end = event['dtend']

            # Ensure event_start and event_end are timezone-aware
            if event_start.tzinfo is None:
                event_start = user_tz.localize(event_start)
            else:
                event_start = event_start.astimezone(user_tz)

            if event_end.tzinfo is None:
                event_end = user_tz.localize(event_end)
            else:
                event_end = event_end.astimezone(user_tz)

            # Extract the date portion for comparison
            event_start_date = event_start.date()

            # Compare event date with current date in user's timezone
            if event_start_date == now.date():
                event_time = event_start.strftime('%H:%M') + ' - ' + event_end.strftime('%H:%M') + f' {user_tz_name}'
                event_summary = f"*{event['summary']}*"
                
                # Use the event's unique UID as the callback data
                task_uid = event['uid']
                button = InlineKeyboardButton("Done?", callback_data=task_uid)
                reply_markup = InlineKeyboardMarkup([[button]])

                today_events.append(
                    {"message": f"{event_time}: {event_summary}", "reply_markup": reply_markup}
                )

        if today_events:
            for event in today_events:
                await update.message.reply_text(event['message'], reply_markup=event['reply_markup'], parse_mode='Markdown')
        else:
            await update.message.reply_text("You have no events scheduled for today.")
    except Exception as e:
        logging.error(f"Error in show_today: {e}")
        await update.message.reply_text("An error occurred while fetching today's events.")

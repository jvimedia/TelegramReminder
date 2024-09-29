# commands/utils.py

import os
import aiohttp  # Use aiohttp for asynchronous HTTP requests
import re
import logging
from datetime import datetime, date, time, timedelta
from icalendar import Calendar
import pytz
from telegram import InlineKeyboardButton, InlineKeyboardMarkup
import base64  # Import base64 for encoding/decoding UIDs

# Load environment variables
ICS_URL = os.getenv('ICS_URL')
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'UTC')

# Dictionary to track notified events
notified_events = {}

# Simple in-memory cache for events
event_cache = {
    'events': [],
    'last_updated': None
}

async def fetch_events():
    now = datetime.utcnow()
    # Cache expiry time in seconds
    cache_expiry = 60  # Cache events for 60 seconds

    if event_cache['last_updated'] and (now - event_cache['last_updated']).total_seconds() < cache_expiry:
        # Return cached events
        logging.info("Returning cached events")
        return event_cache['events']
    try:
        async with aiohttp.ClientSession() as session:
            async with session.get(ICS_URL) as response:
                response_text = await response.text()
        cal = Calendar.from_ical(response_text)
        events = []
        local_tz = pytz.timezone(DEFAULT_TIMEZONE)
        for component in cal.walk('VEVENT'):
            dtstart = component.get('DTSTART').dt
            dtend = component.get('DTEND').dt

            # Convert dates to datetimes if necessary
            if isinstance(dtstart, date) and not isinstance(dtstart, datetime):
                dtstart = datetime.combine(dtstart, time.min)
            if isinstance(dtend, date) and not isinstance(dtend, datetime):
                dtend = datetime.combine(dtend, time.min)

            # Localize datetime objects
            if dtstart.tzinfo is None:
                dtstart = local_tz.localize(dtstart)
            else:
                dtstart = dtstart.astimezone(local_tz)
            if dtend.tzinfo is None:
                dtend = local_tz.localize(dtend)
            else:
                dtend = dtend.astimezone(local_tz)

            event = {
                'uid': str(component.get('UID')),
                'summary': str(component.get('SUMMARY')),
                'dtstart': dtstart,
                'dtend': dtend,
                'description': str(component.get('DESCRIPTION')),
            }
            events.append(event)
        # Update the cache
        event_cache['events'] = events
        event_cache['last_updated'] = now
        logging.info("Events fetched and cache updated")
        return events
    except Exception as e:
        logging.error(f"Error fetching events: {e}")
        # Return cached events even if empty
        return event_cache['events']

def should_notify(event_uid):
    now = datetime.utcnow()
    last_notified = notified_events.get(event_uid)
    if not last_notified or (now - last_notified) > timedelta(minutes=15):
        notified_events[event_uid] = now
        return True
    return False

def extract_completion_url(description):
    match = re.search(r'\[✅ set task status\s*completed\]\((http[^\s\)]+)\)', description, re.DOTALL)
    if match:
        return match.group(1)
    return None

def format_event_message(event, is_expanded=False, is_completed=False):
    # Format the event message using a template
    dt_format = '%d.%m.%Y %H:%M'
    event_start = event['dtstart'].strftime(dt_format)
    event_end = event['dtend'].strftime('%H:%M')
    title = event['summary']
    description = event['description'] if is_expanded else ''
    checkbox = '✅ ' if is_completed else ''
    message = f"*{checkbox}{event_start} - {event_end}* {title}\n{description}"

    # Encode the event UID
    event_uid = event['uid']
    encoded_uid = base64.urlsafe_b64encode(event_uid.encode()).decode()

    # Create buttons
    buttons = []
    if not is_completed:
        buttons.append(
            InlineKeyboardButton(
                "Mark as Completed",
                callback_data=f"complete:{encoded_uid}"
            )
        )
    else:
        buttons.append(InlineKeyboardButton("✅ Completed", callback_data="noop"))

    expand_text = "Collapse" if is_expanded else "Expand"
    buttons.append(
        InlineKeyboardButton(
            expand_text,
            callback_data=f"toggle:{encoded_uid}:{is_expanded}"
        )
    )

    reply_markup = InlineKeyboardMarkup([buttons])
    return message, reply_markup

def get_next_event(events, current_event):
    # Find the next event after the current_event
    sorted_events = sorted(events, key=lambda e: e['dtstart'])
    for event in sorted_events:
        if event['dtstart'] > current_event['dtstart']:
            return event
    return None

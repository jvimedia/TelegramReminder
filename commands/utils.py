import os
import requests
import re
import logging
from datetime import datetime, date, time, timedelta
from icalendar import Calendar
import pytz

# Load environment variables
ICS_URL = os.getenv('ICS_URL')
DEFAULT_TIMEZONE = os.getenv('DEFAULT_TIMEZONE', 'UTC')

# Dictionary to track notified events
notified_events = {}

def fetch_events():
    try:
        response = requests.get(ICS_URL)
        response.raise_for_status()
        cal = Calendar.from_ical(response.text)
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
        return events
    except Exception as e:
        logging.error(f"Error fetching events: {e}")
        return []

def should_notify(event_uid):
    now = datetime.utcnow()
    last_notified = notified_events.get(event_uid)
    if not last_notified or (now - last_notified) > timedelta(hours=12):
        notified_events[event_uid] = now
        return True
    return False

def extract_completion_url(description):
    match = re.search(r'\[✅ set task status completed\]\((.*?)\)', description)
    if match:
        return match.group(1)
    return None

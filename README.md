# Telegram Reminder Bot

This bot helps you manage your events and reminders using a Telegram bot. It fetches events from an ICS calendar URL and sends reminders to your Telegram chat.

## Features

- Fetch events from an ICS calendar URL.
- Send reminders for upcoming events.
- Set and manage your timezone.
- Mark events as completed.
- Expand and collapse event details.

## Setup

1. Clone the repository:
    ```sh
    git clone https://github.com/jvimedia/TelegramReminder.git
    cd TelegramReminder
    ```

2. Create a virtual environment and install dependencies:
    ```sh
    python3 -m venv venv
    source venv/bin/activate
    pip install -r requirements.txt
    ```

3. Create a `.env` file in the root directory and add your configuration:
    ```plaintext
    # Example .env file for TelegramReminder

    # Replace with your actual Telegram bot token the @botfather gave you
    TELEGRAM_TOKEN = 'your-telegram-bot-token'

    # Replace with your chat ID as an integer
    CHAT_ID = 12345678

    # Replace with your actual ICS URL
    ICS_URL = 'https://example.com/your-ics-url'

    # Set your default timezone
    DEFAULT_TIMEZONE=UTC
    ```

4. Run the bot:
    ```sh
    python telegram_bot.py
    ```

## Usage

### Commands

- `/start`: Start the bot and receive a welcome message.
- `/showtoday`: Show today's events.
- `/settimezone`: Set your timezone. You can either send your location or type your timezone in the format `Region/City`, e.g., `Europe/Berlin`.
- `/cancel`: Cancel the current operation.

### ICS File Format

The bot expects the ICS file to contain events in the following format:

```ics
BEGIN:VCALENDAR
VERSION:2.0
PRODID:-//Your Organization//Your Product//EN
BEGIN:VEVENT
UID:unique-event-id@example.com
DTSTAMP:20231010T123456Z
DTSTART:20231010T140000Z
DTEND:20231010T150000Z
SUMMARY:Event Title
DESCRIPTION:Event Description\n\n[✅ set task status completed](http://example.com/complete-task)
END:VEVENT
END:VCALENDAR
```

### Event Description

To mark an event as completed, the description should contain a completion URL in the following format:

```markdown
[✅ set task status completed](http://example.com/complete-task)
```

The description field in the ICS file should look like this:

```ics
DESCRIPTION:Event Description\n\n[✅ set task status completed](http://example.com/complete-task)
```

## Contributing

Feel free to submit issues and pull requests. For major changes, please open an issue first to discuss what you would like to change.

## License

This project is licensed under the MIT License.
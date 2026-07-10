"""
Shared constants and helpers for the Garba 2026 promo bot.
"""
from datetime import date, datetime

# Event date — used to compute "days left" for countdown captions
EVENT_DATE = date(2026, 10, 25)

# PLACEHOLDER DATES — edit these once you lock in real ticket dates.
# Everything in schedule.csv that references an early-bird push is built
# around these two constants, so changing them here is the only edit needed.
EARLY_BIRD_LAUNCH_DATE = date(2026, 7, 17)   # <-- set your real ticket-open date
EARLY_BIRD_DEADLINE_DATE = date(2026, 8, 7)  # <-- set your real early-bird cutoff

# Target audience cities. Add/remove freely — generate_captions.py will
# create one caption variant per city automatically.
TARGET_CITIES = [
    "Munich",
    "Nuremberg",
    "Augsburg",
    "Regensburg",
    "Wurzburg",
    "Ingolstadt",
    "Furth",
    "Erlangen",
    "Bamberg",
    "Zurich",
]


def days_left(as_of: date = None) -> int:
    """Days remaining until the event, from the given date (default: today)."""
    as_of = as_of or date.today()
    return (EVENT_DATE - as_of).days


def parse_extra(extra_str: str) -> dict:
    """Parse a schedule.csv 'extra' cell like 'sponsor_name=Starvent;sponsor_tag=@starvent' into a dict."""
    result = {}
    if not extra_str:
        return result
    for pair in extra_str.split(";"):
        if "=" in pair:
            k, v = pair.split("=", 1)
            result[k.strip()] = v.strip()
    return result


def render_template(text: str, city: str, as_of: date = None, extra: dict = None) -> str:
    """Fill {city}, {days_left}, {event_date}, and any {extra} placeholders in a template string."""
    rendered = (
        text.replace("{city}", city or "")
        .replace("{days_left}", str(days_left(as_of)))
        .replace("{event_date}", EVENT_DATE.strftime("%d %B %Y"))
    )
    for key, value in (extra or {}).items():
        rendered = rendered.replace("{" + key + "}", value)
    return rendered


def parse_schedule_datetime(date_str: str, time_str: str) -> datetime:
    return datetime.strptime(f"{date_str} {time_str}", "%Y-%m-%d %H:%M")


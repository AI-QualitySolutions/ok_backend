from dateutil import parser
import re
import pytz
from django.utils import timezone
from datetime import datetime, time

saudi_tz = pytz.timezone('Asia/Riyadh')


def Current_saudi_time():
    now_saudi = timezone.now().astimezone(saudi_tz)
    start_time = saudi_tz.localize(
        datetime.combine(now_saudi.date(), time.min))
    end_time = now_saudi

    return start_time, end_time


def parse_datetime_with_timezone(date_str, default_tz='Asia/Riyadh'):
    """
    Parses an ISO 8601 datetime string into a timezone-aware datetime object.
    If the input is already timezone-aware, it converts it to the default timezone.
    If parsing fails, returns None.
    """
    try:
        dt = datetime.fromisoformat(date_str)
        if dt.tzinfo is None:
            # Assume it's in the default timezone if no tz is provided
            tz = pytz.timezone(default_tz)
            dt = tz.localize(dt)
        else:
            # Convert to default timezone
            tz = pytz.timezone(default_tz)
            dt = dt.astimezone(tz)
        return dt
    except Exception as e:
        print(f"Error parsing datetime: {e}")
        return None


def convert_given_iso_to_utc(dt_str):
    if not dt_str:
        return None
    try:
        # Fix datetime strings like "2025-05-27T00:00:00 06:00"
        match = re.match(r"(.+?)\s([+-]\d{2}:\d{2})", dt_str)
        if match:
            dt_str = match.group(1) + match.group(2)

        # Parse the datetime string
        dt = parser.isoparse(dt_str)

        # Convert to UTC
        return dt.astimezone(pytz.UTC)

    except (ValueError, TypeError) as e:
        print(f"Error parsing datetime '{dt_str}': {e}")
        return None


def convert_utc_to_riyadh(utc_dt):
    """
    Convert a UTC datetime to Riyadh (Asia/Riyadh) timezone.

    Parameters:
        utc_dt (datetime): A timezone-aware or naive UTC datetime object.

    Returns:
        datetime: A timezone-aware datetime object in Riyadh timezone.
    """
    if utc_dt.tzinfo is None:
        # Assume input is in UTC if naive
        utc_dt = pytz.utc.localize(utc_dt)
    return utc_dt.astimezone(saudi_tz)


def start_end_time_to_riyad(dt):
    if dt.tzinfo is None:
        return saudi_tz.localize(dt)
    return dt.astimezone(saudi_tz)


def calculate_duration_minutes(start, end):
    return int((end - start).total_seconds())

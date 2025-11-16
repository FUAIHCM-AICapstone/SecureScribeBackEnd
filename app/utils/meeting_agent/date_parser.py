"""
AI-based date parser for converting relative date strings to datetime objects.
Uses pattern matching and semantic understanding to parse human-readable dates.
"""

from datetime import datetime, timedelta, timezone
from typing import Optional


def get_next_day_of_week(target_day: str, base_date: Optional[datetime] = None) -> datetime:
    """Get the next occurrence of a specific day of week."""
    if base_date is None:
        base_date = datetime.now(timezone.utc)

    day_map = {
        "monday": 0,
        "tuesday": 1,
        "wednesday": 2,
        "thursday": 3,
        "friday": 4,
        "saturday": 5,
        "sunday": 6,
    }

    target_day_lower = target_day.lower().strip()
    if target_day_lower not in day_map:
        return base_date

    current_weekday = base_date.weekday()
    target_weekday = day_map[target_day_lower]

    # Calculate days to add (next occurrence)
    days_ahead = (target_weekday - current_weekday) % 7
    if days_ahead <= 0:  # Target day already happened this week
        days_ahead += 7

    return base_date + timedelta(days=days_ahead)


def get_end_of_month(base_date: Optional[datetime] = None) -> datetime:
    """Get the last day of the current month."""
    if base_date is None:
        base_date = datetime.now(timezone.utc)

    # Get first day of next month, then subtract 1 day
    if base_date.month == 12:
        next_month_first = base_date.replace(year=base_date.year + 1, month=1, day=1)
    else:
        next_month_first = base_date.replace(month=base_date.month + 1, day=1)

    return next_month_first - timedelta(days=1)


def get_end_of_week(base_date: Optional[datetime] = None) -> datetime:
    """Get the end of the current week (Sunday)."""
    if base_date is None:
        base_date = datetime.now(timezone.utc)

    # Find Sunday (weekday 6)
    days_to_sunday = (6 - base_date.weekday()) % 7
    if days_to_sunday == 0 and base_date.weekday() != 6:
        days_to_sunday = 7

    return base_date + timedelta(days=days_to_sunday)


def _parse_numeric_duration(due_date_lower: str, base_date: datetime) -> Optional[datetime]:
    """Parse numeric durations like '3 days' or '2 weeks'."""
    parts = due_date_lower.split()
    if not parts or not parts[0].isdigit():
        return None
    amount = int(parts[0])
    if "day" in due_date_lower:
        return base_date + timedelta(days=amount)
    if "week" in due_date_lower:
        return base_date + timedelta(weeks=amount)
    return None


def _parse_named_date(due_date_lower: str, base_date: datetime) -> Optional[datetime]:
    """Parse named dates like 'end of week', 'next Monday', etc."""
    if "end of week" in due_date_lower:
        return get_end_of_week(base_date)
    if "end of month" in due_date_lower or "end of this month" in due_date_lower:
        return get_end_of_month(base_date)
    day_names = ["monday", "tuesday", "wednesday", "thursday", "friday", "saturday", "sunday"]
    if "next " in due_date_lower:
        day_part = due_date_lower.replace("next", "").strip()
        return get_next_day_of_week(day_part, base_date) if day_part in day_names else None
    return get_next_day_of_week(due_date_lower, base_date) if due_date_lower in day_names else None


def parse_due_date_to_datetime(
    due_date_str: Optional[str],
    base_date: Optional[datetime] = None,
) -> Optional[datetime]:
    """
    Parse relative date string to datetime using AI-inspired semantic understanding.

    Supports formats like:
    - "3 days" -> 3 days from now
    - "1 week" -> 7 days from now
    - "2 weeks" -> 14 days from now
    - "end of week" -> next Sunday
    - "end of month" -> last day of current month
    - "next Monday" -> next occurrence of Monday
    - "next Friday" -> next occurrence of Friday
    - null/None -> None (no deadline)

    Args:
        due_date_str: Relative date string from AI extraction
        base_date: Base date for calculations (defaults to current UTC time)

    Returns:
        datetime object or None if no valid date parsed
    """
    if not due_date_str or due_date_str.strip().lower() == "null":
        return None

    if base_date is None:
        base_date = datetime.now(timezone.utc)

    due_date_lower = due_date_str.strip().lower()

    # Try numeric duration first (3 days, 2 weeks)
    result = _parse_numeric_duration(due_date_lower, base_date)
    if result:
        return result

    # Try named dates
    result = _parse_named_date(due_date_lower, base_date)
    if result:
        return result

    # If unable to parse, return None
    print(f"[DateParser] Warning: Unable to parse due_date: {due_date_str}")
    return None

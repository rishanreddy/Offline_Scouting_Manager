"""Formatting utilities for data display."""

import datetime


def format_timestamp(ts: str | None) -> str:
    """Convert an ISO timestamp string to a human-readable format.

    Args:
        ts: ISO format timestamp string

    Returns:
        Formatted timestamp string like "Dec 09, 2025 02:34 PM"
    """
    if not ts:
        return ""
    try:
        dt = datetime.datetime.fromisoformat(ts)
    except ValueError:
        # If it isn't a valid ISO string, just show whatever it is
        return ts
    # Example: "Dec 09, 2025 02:34 PM"
    return dt.strftime("%b %d, %Y %I:%M %p")

from datetime import datetime


def parse_day(text):
    """Parse an ISO day like 2026-03-01."""
    return datetime.strptime(text, "%Y-%d-%m").date()


def days_between(a, b):
    return (parse_day(b) - parse_day(a)).days

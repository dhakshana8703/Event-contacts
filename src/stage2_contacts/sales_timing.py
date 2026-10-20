"""Sales Timing Engine: Calculate days until event and sales priority classification."""
from datetime import datetime, date, timezone
from typing import Optional, Tuple, Dict
import re

DEFAULT_PRIORITY_THRESHOLDS: Dict[str, Tuple[Optional[int], Optional[int]]] = {
    "Urgent": (0, 7),
    "Near-term": (8, 30),
    "Upcoming": (31, 90),
    "Long-term": (91, None)
}


def parse_start_date(dates_str: Optional[str]) -> Optional[date]:
    """
    Parse the starting date from standard formatted date strings.

    Examples:
        '2026-10-20 to 2026-10-22' -> date(2026, 10, 20)
        '2026-10-30' -> date(2026, 10, 30)
        '19 Oct 2026 to 21 Oct 2026' -> date(2026, 10, 19)
    """
    if not dates_str or not isinstance(dates_str, str):
        return None

    cleaned = dates_str.strip()
    if not cleaned:
        return None

    # Pattern 1: ISO formatted YYYY-MM-DD (e.g. '2026-10-20 to 2026-10-22' or '2026-10-30')
    iso_match = re.search(r'(\d{4})-(\d{2})-(\d{2})', cleaned)
    if iso_match:
        year, month, day = map(int, iso_match.groups())
        try:
            return date(year, month, day)
        except ValueError:
            return None

    # Pattern 2: 'DD Mon YYYY' (e.g. '19 Oct 2026')
    mon_match = re.search(r'(\d{1,2})\s+([A-Za-z]{3,9})\s+(\d{4})', cleaned)
    if mon_match:
        day_s, mon_s, year_s = mon_match.groups()
        for fmt in ('%d %b %Y', '%d %B %Y'):
            try:
                dt = datetime.strptime(f"{day_s} {mon_s} {year_s}", fmt)
                return dt.date()
            except ValueError:
                continue

    return None


def calculate_sales_timing(
    dates_str: Optional[str],
    reference_date: Optional[date] = None,
    thresholds: Optional[Dict[str, Tuple[Optional[int], Optional[int]]]] = None
) -> Tuple[Optional[int], str]:
    """
    Calculate the days remaining until the event and classify sales urgency.

    Args:
        dates_str: Raw or normalized date string.
        reference_date: Today's date (defaults to current UTC date at runtime).
        thresholds: Custom threshold mapping.

    Returns:
        Tuple of (days_until_event, sales_priority_classification).
        Classification values: 'Past', 'Urgent', 'Near-term', 'Upcoming', 'Long-term', 'Unknown'.
    """
    if reference_date is None:
        reference_date = datetime.now(timezone.utc).date()

    start_date = parse_start_date(dates_str)
    if not start_date:
        return None, "Unknown"

    days_delta = (start_date - reference_date).days

    if days_delta < 0:
        return days_delta, "Past"

    active_thresholds = thresholds or DEFAULT_PRIORITY_THRESHOLDS

    for category, (min_days, max_days) in active_thresholds.items():
        if min_days is not None and days_delta < min_days:
            continue
        if max_days is not None and days_delta > max_days:
            continue
        return days_delta, category

    return days_delta, "Long-term"

"""Unit tests for Sales Timing Engine (deterministic, offline)."""
from datetime import date
import pytest

from src.stage2_contacts.sales_timing import parse_start_date, calculate_sales_timing


class TestSalesTiming:
    def test_parse_start_date_iso_range(self):
        d = parse_start_date("2026-10-20 to 2026-10-22")
        assert d == date(2026, 10, 20)

    def test_parse_start_date_iso_single(self):
        d = parse_start_date("2026-10-30")
        assert d == date(2026, 10, 30)

    def test_parse_start_date_textual(self):
        d = parse_start_date("19 Oct 2026 to 21 Oct 2026")
        assert d == date(2026, 10, 19)

    def test_parse_start_date_invalid(self):
        assert parse_start_date("") is None
        assert parse_start_date(None) is None
        assert parse_start_date("Dates to be announced") is None

    def test_calculate_sales_timing_buckets(self):
        ref = date(2026, 10, 19)

        # Past event
        days, prio = calculate_sales_timing("2026-10-10", reference_date=ref)
        assert days == -9
        assert prio == "Past"

        # Urgent (0–7 days)
        days, prio = calculate_sales_timing("2026-10-20 to 2026-10-22", reference_date=ref)
        assert days == 1
        assert prio == "Urgent"

        days, prio = calculate_sales_timing("2026-10-26", reference_date=ref)
        assert days == 7
        assert prio == "Urgent"

        # Near-term (8–30 days)
        days, prio = calculate_sales_timing("2026-11-05", reference_date=ref)
        assert days == 17
        assert prio == "Near-term"

        # Upcoming (31–90 days)
        days, prio = calculate_sales_timing("2026-12-08", reference_date=ref)
        assert days == 50
        assert prio == "Upcoming"

        # Long-term (>90 days)
        days, prio = calculate_sales_timing("2027-04-21", reference_date=ref)
        assert days == 184
        assert prio == "Long-term"

    def test_calculate_sales_timing_unknown_date(self):
        days, prio = calculate_sales_timing(None)
        assert days is None
        assert prio == "Unknown"

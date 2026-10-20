"""Stage 1 CLI Runner: Discover events and their external websites in-memory."""
import os
import sys
import json
import csv
import argparse
from typing import List, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from src.models import DiscoveredEvent, FieldEvidence, current_iso_timestamp
from src.stage1_discovery.api_client import AlgoliaApiClient
from src.stage1_discovery.parser import parse_algolia_hits, parse_listing_page, extract_external_website
from src.stage1_discovery.normalizer import normalize_text

DEFAULT_LISTING_URL = "https://www.investindubai.gov.ae/en/events-calendar?tags=Business+events"
OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "data", "output")
JSON_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "events.json")
CSV_OUTPUT_PATH = os.path.join(OUTPUT_DIR, "events.csv")


def save_results(events: List[DiscoveredEvent], json_path: str = JSON_OUTPUT_PATH, csv_path: str = CSV_OUTPUT_PATH) -> None:
    """Save discovered events to readable JSON and CSV files."""
    os.makedirs(os.path.dirname(json_path), exist_ok=True)

    # 1. Save JSON
    events_dicts = [e.to_dict() for e in events]
    with open(json_path, "w", encoding="utf-8") as f:
        json.dump(events_dicts, f, indent=2, ensure_ascii=False)

    # 2. Save CSV
    fieldnames = [
        "event_name",
        "listing_page_url",
        "event_page_url",
        "event_website_url",
        "website_status",
        "category",
        "dates",
        "venue",
        "retrieval_status",
        "notes"
    ]

    with open(csv_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for e in events:
            writer.writerow({
                "event_name": e.event_name.normalized_value if e.event_name else "",
                "listing_page_url": e.listing_page_url,
                "event_page_url": e.event_page_url or "",
                "event_website_url": e.event_website_url.normalized_value if (e.event_website_url and e.event_website_url.normalized_value) else "",
                "website_status": e.event_website_url.extraction_status if e.event_website_url else "null",
                "category": e.category.normalized_value if e.category else "",
                "dates": e.dates_text.normalized_value if e.dates_text else "",
                "venue": e.venue.normalized_value if (e.venue and e.venue.normalized_value) else "",
                "retrieval_status": e.retrieval_status,
                "notes": e.notes or ""
            })


def run_stage1(
    listing_url: str = DEFAULT_LISTING_URL,
    target_event_filter: Optional[str] = None,
    limit: Optional[int] = None,
    tag_filter: str = "Business events",
    hits_per_page: int = 50,
    headless: bool = True
) -> List[DiscoveredEvent]:
    """
    Run Stage 1 discovery using the verified Algolia Search API.

    Args:
        listing_url: Starting URL for the business events calendar.
        target_event_filter: Substring to filter specific events (e.g. 'Russian Design Forum').
        limit: Maximum number of events to process.
        tag_filter: Tag filter for Algolia query ('Business events').
        hits_per_page: Number of hits to query per page (pagination handled dynamically).
        headless: Maintained for CLI compatibility.

    Returns:
        List of processed DiscoveredEvent objects.
    """
    print(f"\n[Stage 1] Querying Algolia Events API for tag: '{tag_filter}'...")
    client = AlgoliaApiClient()
    raw_hits, total_reported = client.fetch_all_events(hits_per_page=hits_per_page, tag_filter=tag_filter)
    print(f"[Stage 1] API reported total {total_reported} event(s). Retrieved {len(raw_hits)} raw hit(s).")

    events = parse_algolia_hits(raw_hits, listing_url=listing_url)
    print(f"[Stage 1] Successfully parsed and deduplicated {len(events)} unique event(s).")

    # Apply target filter if provided (e.g. Russian Design Forum)
    if target_event_filter:
        target_lower = target_event_filter.lower()
        filtered = [e for e in events if target_lower in (e.event_name.normalized_value or "").lower()]
        if filtered:
            events = filtered
            print(f"[Stage 1] Filtered to target event: '{target_event_filter}' ({len(events)} match).")
        else:
            print(f"[Warning] Filter '{target_event_filter}' matched 0 events. Proceeding with all discovered.")

    if limit and limit > 0:
        events = events[:limit]
        print(f"[Stage 1] Limited processing to {len(events)} event(s).")

    # Save outputs
    save_results(events)
    print(f"\n[Stage 1 Complete]")
    print(f"  - Primary Output (JSON): {os.path.abspath(JSON_OUTPUT_PATH)}")
    print(f"  - Table Output (CSV):   {os.path.abspath(CSV_OUTPUT_PATH)}")

    return events


def main():
    # Ensure UTF-8 output encoding for console
    if sys.stdout.encoding.lower() != "utf-8":
        try:
            sys.stdout.reconfigure(encoding="utf-8")
        except Exception:
            pass

    parser = argparse.ArgumentParser(description="Stage 1 - Discover events and their external websites via Algolia API.")
    parser.add_argument("--url", default=DEFAULT_LISTING_URL, help="Event calendar listing URL")
    parser.add_argument("--event", default=None, help="Filter for a specific event name (e.g. 'Russian Design Forum')")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of events to process")
    parser.add_argument("--headful", action="store_true", help="Maintained for CLI compatibility")

    args = parser.parse_args()

    events = run_stage1(
        listing_url=args.url,
        target_event_filter=args.event,
        limit=args.limit,
        headless=not args.headful
    )

    # Print summary
    succeeded = sum(1 for e in events if e.retrieval_status == "succeeded")
    failed = sum(1 for e in events if e.retrieval_status in ("failed", "incomplete"))

    print("\n" + "=" * 50)
    print(f"STAGE 1 SUMMARY:")
    print(f"  Total Unique Events Saved: {len(events)}")
    print(f"  Websites Discovered (Succeeded): {succeeded}")
    print(f"  Missing Websites (Incomplete): {failed}")
    print("=" * 50)


if __name__ == "__main__":
    main()


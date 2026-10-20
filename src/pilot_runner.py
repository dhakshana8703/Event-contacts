"""End-to-End Live Pilot Runner for Dubai Business Events.

Coordinates:
- Stage 1: Discovered Event Record
- Specialist 1: In-Memory Event Web Scout (scout.py)
- Specialist 2: In-Memory Contact & Evidence Extractor with Gemini (extractor.py)
- Specialist 3: Live LinkedIn Discovery & Verification with Serper (specialist.py)
"""
import os
import sys
import json
import csv
import argparse
from typing import Dict, Any, List

# Fix Windows console UTF-8 encoding
if sys.stdout.encoding and sys.stdout.encoding.lower() != 'utf-8':
    try:
        sys.stdout.reconfigure(encoding='utf-8')
    except Exception:
        pass

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath("."))
import src

from src.stage2_contacts.scout import EventWebScout
from src.stage2_contacts.extractor import ContactExtractor
from src.stage3_verification.specialist import LinkedInSpecialist
from src.providers.search_serper import SerperSearchProvider
from src.providers.llm_gemini import GeminiLLMProvider


def run_live_pilot(event_name_filter: str = "top5", top_n: Optional[int] = None) -> List[Dict[str, Any]]:
    print("=" * 75)
    print(f"STARTING LIVE AGENTIC PILOT FOR: {event_name_filter} (top_n={top_n})")
    print("=" * 75)

    # 1. Load Stage 1 Discovered Events
    events_path = os.path.join("data", "output", "events.json")
    if not os.path.exists(events_path):
        raise FileNotFoundError(f"Stage 1 events file not found: {events_path}")

    with open(events_path, "r", encoding="utf-8") as f:
        events = json.load(f)

    target_events = []
    if top_n is not None:
        target_events = events[:top_n]
    elif event_name_filter.lower() in ("all", "all29"):
        target_events = events
    elif event_name_filter.lower() == "top5":
        target_events = events[:5]
    else:
        filters = [f.strip() for f in event_name_filter.split(",") if f.strip()]
        for flt in filters:
            matched = False
            for e in events:
                ename = e.get("event_name", {}).get("normalized_value", "")
                if flt.lower() in ename.lower():
                    if e not in target_events:
                        target_events.append(e)
                    matched = True
                    break
            if not matched:
                print(f"[Warning] No event matching '{flt}' found in events.json", flush=True)

    if not target_events:
        raise ValueError(f"No events matching '{event_name_filter}' found in events.json")

    # 2. Initialize Live Providers
    print(f"\n[Initializing Live Providers]")
    serper_provider = SerperSearchProvider()
    gemini_provider = GeminiLLMProvider(model="gemini-flash-lite-latest")
    print("  - Search Provider:   SerperSearchProvider (Google Search API)")
    print("  - LLM Provider:      GeminiLLMProvider (Google Gemini Flash Lite)")

    from src.stage1_discovery.client import InMemoryBrowserClient
    linkedin_specialist = LinkedInSpecialist(search_provider=serper_provider)

    all_verified_contacts: List[Dict[str, Any]] = []

    with InMemoryBrowserClient(headless=True) as browser_client:
        scout = EventWebScout(timeout=15, browser_client=browser_client)
        extractor = ContactExtractor(scout=scout, llm_provider=gemini_provider)

        for e_idx, target_event in enumerate(target_events, start=1):
            event_name = target_event["event_name"]["normalized_value"]
            event_dates = target_event.get("dates_text", {}).get("normalized_value", "") if target_event.get("dates_text") else ""
            event_venue = target_event.get("venue", {}).get("normalized_value", "") if target_event.get("venue") else ""
            website_url = target_event.get("event_website_url", {}).get("normalized_value")
            event_category = target_event.get("category", {}).get("normalized_value", "") if target_event.get("category") else ""
            detail_url = target_event.get("event_page_url")

            print("\n" + "-" * 75)
            print(f"EVENT [{e_idx}/{len(target_events)}]: {event_name}")
            print(f"  - Dates:             {event_dates}")
            print(f"  - Venue:             {event_venue}")
            print(f"  - External Website:  {website_url}")
            print(f"  - Detail Page URL:   {detail_url}")
            print("-" * 75)

            # 3. Specialist 1 & 2: Scout and Extract Contacts
            print(f"  -> Scouting website in-memory: {website_url}...")
            stage2_result = extractor.process_event(
                event_name=event_name,
                event_website_url=website_url,
                event_detail_url=detail_url
            )

            print(f"  -> Inspected {len(stage2_result['inspected_pages'])} page(s):")
            for p in stage2_result['inspected_pages']:
                print(f"     * URL: {p['url']} | Status: {p['status']} | Contacts Found: {p['contacts_found']}")

            extracted_contacts = stage2_result.get("contacts", [])
            print(f"  -> Extracted {len(extracted_contacts)} contact/desk record(s).")

            # 4. Specialist 3: Live LinkedIn Discovery & Verification
            event_contacts: List[Dict[str, Any]] = []
            for idx, c in enumerate(extracted_contacts, start=1):
                ctype = c.get("contact_type", "person")
                pname = c.get("person_name", {}).get("normalized_value")
                prole = c.get("role_as_written", {}).get("normalized_value") if c.get("role_as_written") else "N/A"

                if ctype == "person":
                    print(f"     [{idx}/{len(extracted_contacts)}] [Person] Searching LinkedIn: {pname} ({prole})...")
                else:
                    print(f"     [{idx}/{len(extracted_contacts)}] [General Desk] Recording Desk: {pname} ({prole})...")

                updated_contact = linkedin_specialist.process_single_contact(c)
                # Attach master event metadata
                updated_contact["event_dates"] = event_dates
                updated_contact["event_venue"] = event_venue
                updated_contact["event_website"] = website_url
                updated_contact["event_category"] = event_category

                v_status = updated_contact.get("verification_status")
                li_url = updated_contact.get("linkedin_url", {}).get("normalized_value") if updated_contact.get("linkedin_url") else "null"
                print(f"         Status:     {v_status}")
                print(f"         LinkedIn:   {li_url}")
                event_contacts.append(updated_contact)

            # If no contacts found, emit single summary row so event is still represented in master sheet
            if not event_contacts:
                no_contact_row = {
                    "event_name": event_name,
                    "event_dates": event_dates,
                    "event_venue": event_venue,
                    "event_website": website_url or "",
                    "event_category": event_category,
                    "contact_type": "No Contacts Published",
                    "person_name": {"normalized_value": "No Personal Contact Published"},
                    "role_as_written": {"normalized_value": "N/A"},
                    "organisation": None,
                    "email": None,
                    "phone": None,
                    "linkedin_url": None,
                    "verification_status": "not_found",
                    "notes": stage2_result.get("notes") or "Pages inspected; no qualifying event-team contacts or desks were publicly published.",
                    "contact_source_url": website_url or detail_url or ""
                }
                event_contacts.append(no_contact_row)

            all_verified_contacts.extend(event_contacts)
            # Incremental checkpoint after every event
            save_master_deliverables(all_verified_contacts)
            print(f"  [Checkpoint] Incremental save: {len(all_verified_contacts)} total records committed to data/output/contacts.csv", flush=True)

    # 5. Clean up temporary / legacy pilot files to keep data/output clean
    for fname in os.listdir("data/output"):
        if fname.startswith("pilot_") or fname in ("contacts_pilot.csv", "contacts_pilot.json", "contacts_accessabilities_expo.csv", "contacts_accessabilities_expo.json"):
            try:
                os.remove(os.path.join("data", "output", fname))
            except Exception:
                pass

    contacts_csv, contacts_json = save_master_deliverables(all_verified_contacts)

    print("\n" + "=" * 75, flush=True)
    print("LIVE AGENTIC RUN COMPLETED SUCCESSFULLY", flush=True)
    print(f"  - Total Events Processed:    {len(target_events)}", flush=True)
    print(f"  - Total Records Generated:   {len(all_verified_contacts)}", flush=True)
    print(f"  - Single Master Sheet (CSV): {contacts_csv}", flush=True)
    print(f"  - Single Master JSON:        {contacts_json}", flush=True)
    print("=" * 75, flush=True)
    return all_verified_contacts


def save_master_deliverables(contacts_list: List[Dict[str, Any]]):
    """Persist the single unified master deliverables incrementally (contacts.json & contacts.csv)."""
    os.makedirs(os.path.join("data", "output"), exist_ok=True)
    contacts_json = os.path.join("data", "output", "contacts.json")
    contacts_csv = os.path.join("data", "output", "contacts.csv")

    with open(contacts_json, "w", encoding="utf-8") as f:
        json.dump(contacts_list, f, indent=2, ensure_ascii=False)

    fieldnames = [
        "Event Name",
        "Event Dates",
        "Event Venue",
        "Official Event Website",
        "Event Category",
        "Contact Type",
        "Contact / Desk Name",
        "Job Title / Role",
        "Organization",
        "Work Email",
        "Phone Number",
        "LinkedIn Profile URL",
        "Verification Status",
        "Evidence Snippet",
        "Notes",
        "Source URL"
    ]

    with open(contacts_csv, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        for c in contacts_list:
            ctype = c.get("contact_type", "person")
            if ctype == "person":
                label_type = "Person"
            elif ctype == "department_desk":
                label_type = "General Desk"
            else:
                label_type = "No Contacts Published"

            writer.writerow({
                "Event Name": c.get("event_name", ""),
                "Event Dates": c.get("event_dates", ""),
                "Event Venue": c.get("event_venue", ""),
                "Official Event Website": c.get("event_website", ""),
                "Event Category": c.get("event_category", ""),
                "Contact Type": label_type,
                "Contact / Desk Name": c.get("person_name", {}).get("normalized_value", ""),
                "Job Title / Role": c.get("role_as_written", {}).get("normalized_value", ""),
                "Organization": c.get("organisation", {}).get("normalized_value", "") if c.get("organisation") else "",
                "Work Email": c.get("email", {}).get("normalized_value", "") if c.get("email") else "",
                "Phone Number": c.get("phone", {}).get("normalized_value", "") if c.get("phone") else "",
                "LinkedIn Profile URL": c.get("linkedin_url", {}).get("normalized_value", "") if c.get("linkedin_url") else "",
                "Verification Status": c.get("verification_status", ""),
                "Evidence Snippet": c.get("person_name", {}).get("supporting_snippet", ""),
                "Notes": c.get("notes", ""),
                "Source URL": c.get("contact_source_url", "")
            })

    return contacts_csv, contacts_json


if __name__ == "__main__":
    parser = argparse.ArgumentParser()
    parser.add_argument("--event", default="top5", help="Comma-separated event names or 'top5'")
    parser.add_argument("--top", type=int, default=None, help="Process top N events")
    args = parser.parse_args()
    run_live_pilot(args.event, top_n=args.top)

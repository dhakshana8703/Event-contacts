"""Unit tests for Stage 2 Organizer Engine and Relational Schema (offline)."""
import os
import pytest

from src.stage2_contacts.organizer_engine import (
    build_organizers_catalog,
    build_contacts_catalog,
    enrich_discovered_events
)


class TestOrganizerEngine:
    def test_build_organizers_catalog_deduplication(self):
        """Verify that organizers catalog produces unique, deduplicated organization records."""
        orgs = build_organizers_catalog()
        org_ids = [o.organizer_id for o in orgs]
        assert len(org_ids) == len(set(org_ids)), "Organizer IDs must be strictly unique"

        # Check DEWA is present
        dewa = next((o for o in orgs if o.organizer_id == "org_dewa"), None)
        assert dewa is not None
        assert dewa.organization_name == "Dubai Electricity and Water Authority (DEWA)"
        assert dewa.organization_type == "Organizing Authority"
        assert dewa.official_website == "https://www.dewa.gov.ae/en"
        assert dewa.public_email == "wetex@dewa.gov.ae"
        assert dewa.public_phone == "+971 4 601 9999"

    def test_enrich_discovered_events_sales_priority_and_linkage(self):
        """Verify that discovered events receive sales priorities and organizer foreign keys."""
        sample_raw = [
            {
                "event_name": {"normalized_value": "WETEX"},
                "event_page_url": "https://www.investindubai.gov.ae/en/events-calendar/wetex",
                "event_website_url": {"normalized_value": "https://www.wetex.ae/en"},
                "dates_text": {"normalized_value": "2026-10-20 to 2026-10-22"},
                "category": {"normalized_value": "Exhibitions"},
                "retrieval_status": "succeeded"
            },
            {
                "event_name": {"normalized_value": "Gulf Superyacht Summit 2026"},
                "event_page_url": "https://www.investindubai.gov.ae/en/events-calendar/gulf-superyacht-summit",
                "event_website_url": None,
                "dates_text": {"normalized_value": "2026-11-24 to 2026-11-25"},
                "category": {"normalized_value": "Exhibitions"},
                "retrieval_status": "incomplete"
            }
        ]

        enriched = enrich_discovered_events(sample_raw)
        assert len(enriched) == 2

        wetex = enriched[0]
        assert wetex.event_name == "WETEX"
        assert wetex.primary_organizer_id == "org_dewa"
        assert wetex.organizer_name == "Dubai Electricity and Water Authority (DEWA)"
        assert wetex.sales_priority in ("Urgent", "Near-term", "Upcoming", "Long-term")
        assert wetex.verification_status == "verified"

        summit = enriched[1]
        assert summit.event_name == "Gulf Superyacht Summit 2026"
        assert summit.primary_organizer_id is None
        assert summit.verification_status == "incomplete"

    def test_contacts_responsibility_areas_and_foreign_keys(self):
        """Verify contacts contain explicit responsibility classifications and valid foreign keys."""
        orgs = build_organizers_catalog()
        known_org_ids = {o.organizer_id for o in orgs}

        contacts = build_contacts_catalog()
        assert len(contacts) >= 4

        for c in contacts:
            # Foreign key check
            assert c.organizer_id in known_org_ids, f"Contact {c.contact_id} has invalid organizer_id: {c.organizer_id}"
            assert c.responsibility_area is not None, f"Contact {c.contact_id} missing responsibility area"
            assert len(c.responsibility_area) > 3

        # WETEX Chairman test
        tayer = next((c for c in contacts if "Tayer" in (c.person_name.normalized_value or "")), None)
        assert tayer is not None
        assert tayer.event_name == "WETEX"
        assert tayer.organizer_id == "org_dewa"
        assert tayer.responsibility_area == "Overall Event Leadership"
        assert tayer.email.normalized_value == "wetex@dewa.gov.ae"

        # Russian Design Forum Founder test
        olga = next((c for c in contacts if "Olga" in (c.person_name.normalized_value or "")), None)
        assert olga is not None
        assert olga.responsibility_area == "Overall Event Leadership"
        assert olga.phone.normalized_value == "+971 586 194 041"

        # Russian Design Forum Assistant test (has missing email)
        anna = next((c for c in contacts if "Anna" in (c.person_name.normalized_value or "")), None)
        assert anna is not None
        assert anna.responsibility_area == "Operations & Registration Inquiries"
        assert anna.phone.normalized_value == "+7 905 198 26 06"
        assert anna.email is None, "Missing email must remain None without fabrication"

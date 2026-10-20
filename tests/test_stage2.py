"""Unit tests for Stage 2 event contact extraction (offline only)."""
import os
import json
import pytest

from src.models import EventContact, FieldEvidence
from src.stage2_contacts.parser import (
    extract_contacts_from_html,
    is_qualifying_organizer_role,
    is_plausible_person_name
)

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(filename: str) -> str:
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestStage2ContactParser:
    def test_extract_organizing_team_contacts(self):
        """Verify extraction of organizing committee members while excluding keynote speakers."""
        html = read_fixture("sample_contacts_page.html")
        source_url = "https://www.accessabilitiesexpo.com/team"
        event_name = "AccessAbilities Expo"

        contacts = extract_contacts_from_html(html, source_url, event_name)

        # Must find exactly 2 event organizers; 1 keynote speaker must be excluded
        assert len(contacts) == 2

        # 1. Sarah Jenkins
        sarah = contacts[0]
        assert sarah.person_name.normalized_value == "Sarah Jenkins"
        assert sarah.role_as_written.normalized_value == "Exhibition Director"
        assert sarah.email.normalized_value == "sarah.j@naddalshiba.com"
        assert sarah.phone.normalized_value == "+971 4 252 7959"
        assert sarah.organisation.normalized_value == "Nadd Al Shiba PR & Event Management"
        assert sarah.contact_source_url == source_url
        assert sarah.event_name == event_name

        # 2. Tariq Al Mansoori (missing email and phone)
        tariq = contacts[1]
        assert tariq.person_name.normalized_value == "Tariq Al Mansoori"
        assert tariq.role_as_written.normalized_value == "Event Operations Manager"
        assert tariq.organisation.normalized_value == "AccessAbilities Organizing Office"
        assert tariq.email is None
        assert tariq.phone is None

    def test_role_preserved_without_rewriting(self):
        """Role must be kept exactly as published without rewriting or upgrading titles."""
        html = read_fixture("sample_contacts_page.html")
        contacts = extract_contacts_from_html(html, "https://example.com", "Sample Event")
        sarah = contacts[0]
        assert sarah.role_as_written.raw_value == "Exhibition Director"
        assert sarah.role_as_written.normalized_value == "Exhibition Director"

    def test_missing_fields_never_fabricated(self):
        """Ensure missing contact details remain None and are not transferred between people."""
        html = read_fixture("sample_contacts_page.html")
        contacts = extract_contacts_from_html(html, "https://example.com", "Sample Event")
        tariq = contacts[1]
        assert tariq.email is None
        assert tariq.phone is None

    def test_qualifying_role_filter(self):
        """Test distinction between organizer roles and non-organizer roles."""
        assert is_qualifying_organizer_role("Exhibition Director") is True
        assert is_qualifying_organizer_role("Event Operations Manager") is True
        assert is_qualifying_organizer_role("Organizing Committee Secretary") is True
        assert is_qualifying_organizer_role("Keynote Speaker") is False
        assert is_qualifying_organizer_role("Conference Attendee") is False
        assert is_qualifying_organizer_role("Platinum Sponsor Representative") is False

    def test_non_person_heading_rejection(self):
        """Ensure page headings like 'Contact Us' or 'About Us' are rejected as names."""
        assert is_plausible_person_name("Contact Us") is False
        assert is_plausible_person_name("About Us") is False
        assert is_plausible_person_name("General Enquiries") is False
        assert is_plausible_person_name("Sarah Jenkins") is True
        assert is_plausible_person_name("Tariq Al Mansoori") is True

    def test_contact_serialization(self):
        """Ensure contact data structure serializes cleanly to JSON."""
        html = read_fixture("sample_contacts_page.html")
        contacts = extract_contacts_from_html(html, "https://example.com", "AccessAbilities Expo")
        data = [c.to_dict() for c in contacts]
        serialized = json.dumps(data, indent=2)
        assert "Sarah Jenkins" in serialized
        assert "Exhibition Director" in serialized

    def test_extract_rdf_organizers(self):
        """Verify extraction of real organizers from Russian Design Forum fixture."""
        html = read_fixture("sample_rdf_contact_section.html")
        contacts = extract_contacts_from_html(html, "https://rdf.ae/en/home/#cont", "Russian Design Forum")
        assert len(contacts) >= 2

        olga = next(c for c in contacts if "Olga" in c.person_name.normalized_value)
        assert olga.person_name.normalized_value == "Olga Melnikova"
        assert "Organizer" in olga.role_as_written.normalized_value
        assert olga.phone.normalized_value == "+ 971 586 194 041"
        assert olga.organisation.normalized_value == "OL Interior"
        assert olga.email is None  # Email was not published on the page

        anna = next(c for c in contacts if "Anna" in c.person_name.normalized_value)
        assert "Anna" in anna.person_name.normalized_value
        assert anna.role_as_written.normalized_value == "Assistant"
        assert anna.phone.normalized_value == "+ 7 905 198 26 06"
        assert anna.email is None

    def test_extract_department_desks_and_ordering(self):
        from src.stage2_contacts.parser import extract_department_desks_from_html
        from src.stage2_contacts.extractor import ContactExtractor

        sample_page = """
        <div class="team-section">
            <div class="organizer">
                <h3 class="name">Dr. Rashid Al Marri</h3>
                <p class="role">Executive Director</p>
                <a href="mailto:rashid@dubaievents.ae">rashid@dubaievents.ae</a>
            </div>
        </div>
        <div class="contact-channels">
            <div class="inquiry-box">
                <p><strong>For General Sales Inquiries</strong></p>
                <span class="phone">+971 4 515 0696</span>
                <a href="mailto:sales@dubaievents.ae">sales@dubaievents.ae</a>
            </div>
            <div class="inquiry-box">
                <p><strong>Media and Marketing Inquiries</strong></p>
                <span class="phone">+971 4 322 3833</span>
                <a href="mailto:media@dubaievents.ae">media@dubaievents.ae</a>
            </div>
        </div>
        """
        # Test desk extractor standalone
        desks = extract_department_desks_from_html(sample_page, "https://dubaievents.ae/contact", "Dubai Summit")
        assert len(desks) == 2
        assert desks[0].contact_type == "department_desk"
        assert desks[0].person_name.normalized_value == "General Sales Inquiries"
        assert desks[0].email.normalized_value == "sales@dubaievents.ae"
        assert desks[0].phone.normalized_value == "+971 4 515 0696"
        assert desks[0].verification_status == "institutional_desk"

        # Test combined extractor ordering: Persons FIRST, Department Desks SECOND
        extractor = ContactExtractor()
        combined = extractor.extract_from_in_memory_html(sample_page, "https://dubaievents.ae/contact", "Dubai Summit")
        assert len(combined) == 3
        # First record MUST be the person
        assert combined[0].contact_type == "person"
        assert combined[0].person_name.normalized_value == "Dr. Rashid Al Marri"
        # Subsequent records MUST be the department desks
        assert combined[1].contact_type == "department_desk"
        assert combined[1].person_name.normalized_value == "General Sales Inquiries"
        assert combined[2].contact_type == "department_desk"
        assert combined[2].person_name.normalized_value == "Media and Marketing Inquiries"

    def test_multi_value_email_and_phone_capture(self):
        from src.stage2_contacts.parser import extract_department_desks_from_html

        multi_val_html = """
        <div class="inquiry-desk">
            <p><strong>For General Sales Inquiries</strong></p>
            <p>Tel: +971 4 515 0696, +971 4 515 1939</p>
            <p>Email: <a href="mailto:sales_general@wetex.ae">sales_general@wetex.ae</a> <a href="mailto:info@wetex.ae">info@wetex.ae</a></p>
        </div>
        """
        desks = extract_department_desks_from_html(multi_val_html, "https://example.com", "Test Event")
        assert len(desks) == 1
        desk = desks[0]
        assert "sales_general@wetex.ae" in desk.email.normalized_value
        assert "info@wetex.ae" in desk.email.normalized_value
        assert "+971 4 515 0696" in desk.phone.normalized_value
        assert "+971 4 515 1939" in desk.phone.normalized_value

    def test_detail_page_hotline_extraction_and_attachment(self):
        from src.stage2_contacts.parser import extract_hotline_from_detail_html

        sample_detail_jss = """
        <div id="sitecore-app">
          {"title":{"jss":{"value":"Dubai Design District (d3)"}},"address":{"jss":{"value":"Dubai Design District - Dubai"}},"phone":{"jss":{"value":"+971 4 433 3000"}}}
        </div>
        """
        hotline = extract_hotline_from_detail_html(sample_detail_jss, "https://investindubai.gov.ae/events/dfw")
        assert hotline is not None
        assert hotline["venue_name"] == "Dubai Design District (d3)"
        assert hotline["phone"] == "+971 4 433 3000"
        assert "Dubai Design District" in hotline["snippet"]
        assert hotline["source_url"] == "https://investindubai.gov.ae/events/dfw"




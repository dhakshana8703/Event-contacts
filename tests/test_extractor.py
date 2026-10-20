"""Tests for Specialist 2: Contact & Evidence Extractor."""
import pytest
from src.providers.llm_mock import MockLLMProvider
from src.stage2_contacts.extractor import ContactExtractor
from src.stage2_contacts.scout import EventWebScout


class TestContactExtractor:
    def test_dom_extraction_from_html(self):
        extractor = ContactExtractor()
        sample_html = """
        <div class="organizer">
            <h3 class="name">Sarah Jenkins</h3>
            <p class="role">Exhibition Director</p>
            <a href="mailto:sarah.j@naddalshiba.com">sarah.j@naddalshiba.com</a>
            <span class="phone">+971 4 252 7959</span>
        </div>
        """
        contacts = extractor.extract_from_in_memory_html(
            html_content=sample_html,
            source_url="https://example.com/team",
            event_name="Test Event"
        )
        assert len(contacts) == 1
        assert contacts[0].person_name.normalized_value == "Sarah Jenkins"
        assert contacts[0].role_as_written.normalized_value == "Exhibition Director"
        assert contacts[0].email.normalized_value == "sarah.j@naddalshiba.com"

    def test_llm_extraction_with_verifiable_snippet(self):
        mock_llm = MockLLMProvider(canned_response={
            "contacts": [
                {
                    "person_name": "HE Saeed Al Tayer",
                    "role_as_written": "Chairman of WETEX Supreme Committee",
                    "organisation": "DEWA",
                    "email": None,
                    "phone": None,
                    "supporting_snippet": "HE Saeed Al Tayer serves as the Chairman of WETEX Supreme Committee and MD of DEWA."
                }
            ]
        })
        extractor = ContactExtractor(llm_provider=mock_llm)

        sample_html = """
        <html>
        <body>
            <p>HE Saeed Al Tayer serves as the Chairman of WETEX Supreme Committee and MD of DEWA.</p>
        </body>
        </html>
        """
        contacts = extractor.extract_from_in_memory_html(
            html_content=sample_html,
            source_url="https://wetex.ae/committee",
            event_name="WETEX"
        )
        assert len(contacts) == 1
        assert contacts[0].person_name.normalized_value == "HE Saeed Al Tayer"
        assert contacts[0].role_as_written.normalized_value == "Chairman of WETEX Supreme Committee"
        assert contacts[0].organisation.normalized_value == "DEWA"
        assert contacts[0].email is None

    def test_anti_hallucination_gate_rejects_invented_snippet(self):
        mock_llm = MockLLMProvider(canned_response={
            "contacts": [
                {
                    "person_name": "Fictional Person",
                    "role_as_written": "Event Director",
                    "supporting_snippet": "Fictional Person is the director of the secret project."
                }
            ]
        })
        extractor = ContactExtractor(llm_provider=mock_llm)

        # Page does NOT contain the snippet
        sample_html = """
        <html>
        <body>
            <p>Welcome to Dubai Business Events. General inquiries: info@dubai.ae</p>
        </body>
        </html>
        """
        contacts = extractor.extract_from_in_memory_html(
            html_content=sample_html,
            source_url="https://example.com",
            event_name="Test Event"
        )
        # Fictional contact must be dropped because snippet was not in the text
        assert len(contacts) == 0

    def test_anti_hallucination_gate_nulls_invented_email(self):
        mock_llm = MockLLMProvider(canned_response={
            "contacts": [
                {
                    "person_name": "HE Saeed Al Tayer",
                    "role_as_written": "Chairman of WETEX",
                    "email": "saeed.altayer@invented-email.gov.ae",  # INVENTED EMAIL
                    "phone": None,
                    "supporting_snippet": "HE Saeed Al Tayer is the Chairman of WETEX."
                }
            ]
        })
        extractor = ContactExtractor(llm_provider=mock_llm)

        sample_html = """
        <html>
        <body>
            <p>HE Saeed Al Tayer is the Chairman of WETEX.</p>
        </body>
        </html>
        """
        contacts = extractor.extract_from_in_memory_html(
            html_content=sample_html,
            source_url="https://wetex.ae",
            event_name="WETEX"
        )
        assert len(contacts) == 1
        # The email was NOT in the snippet, so it must be nulled out
        assert contacts[0].email is None

    def test_process_event_missing_website(self):
        extractor = ContactExtractor()
        report = extractor.process_event("No Web Event", event_website_url=None)
        assert report["overall_status"] == "missing_website_url"
        assert report["contacts_count"] == 0

"""Tests for Specialist 3: LinkedIn Discovery & Identity Verification Specialist."""
import json
import pytest
from src.providers.base import SearchResult
from src.providers.search_mock import MockSearchProvider
from src.stage3_verification.specialist import (
    clean_person_name,
    generate_search_queries,
    evaluate_verification,
    LinkedInSpecialist,
)


class TestSpecialist3Helpers:
    def test_clean_person_name_honorifics(self):
        assert clean_person_name("HE Saeed Mohammed Al Tayer") == "Saeed Mohammed Al Tayer"
        assert clean_person_name("H.E. Saeed Al Tayer") == "Saeed Al Tayer"
        assert clean_person_name("His Excellency Dr. Rashid") == "Rashid"
        assert clean_person_name("Eng. Fatima Al Mansoori") == "Fatima Al Mansoori"
        assert clean_person_name("Olga Melnikova") == "Olga Melnikova"

    def test_generate_search_queries_hierarchy(self):
        queries = generate_search_queries(
            person_name="HE Saeed Al Tayer",
            organization="DEWA",
            event_name="WETEX 2026 - Clean Energy",
            role="Managing Director & CEO"
        )
        assert len(queries) == 4
        # Priority 1: Name + Org
        assert queries[0] == 'site:linkedin.com/in "Saeed Al Tayer" "DEWA"'
        # Priority 2: Name + Event
        assert queries[1] == 'site:linkedin.com/in "Saeed Al Tayer" "WETEX 2026"'
        # Priority 3: Name + Role
        assert queries[2] == 'site:linkedin.com/in "Saeed Al Tayer" "Managing Director & CEO"'
        # Priority 4: Name + Dubai
        assert queries[3] == 'site:linkedin.com/in "Saeed Al Tayer" "Dubai"'

    def test_evaluate_verification_verified_match(self):
        eval_res = evaluate_verification(
            person_name="HE Saeed Al Tayer",
            organization="DEWA",
            role="MD & CEO",
            event_name="WETEX",
            candidate_url="https://www.linkedin.com/in/saeed-al-tayer",
            snippet="Saeed Al Tayer - MD & CEO at Dubai Electricity & Water Authority (DEWA)...",
            query_used='site:linkedin.com/in "Saeed Al Tayer" "DEWA"'
        )
        assert eval_res["status"] == "verified"
        assert "DEWA" in eval_res["justification"]

    def test_evaluate_verification_name_alone_returns_needs_review(self):
        eval_res = evaluate_verification(
            person_name="John Smith",
            organization="DEWA",
            role="Event Coordinator",
            event_name="WETEX",
            candidate_url="https://www.linkedin.com/in/john-smith-123",
            snippet="John Smith - Retail Manager at General Goods Corp, London.",
            query_used='site:linkedin.com/in "John Smith" "DEWA"'
        )
        assert eval_res["status"] == "needs_review"
        assert "lacks explicit supporting affiliation" in eval_res["justification"]

    def test_evaluate_verification_rejects_company_page(self):
        eval_res = evaluate_verification(
            person_name="HE Saeed Al Tayer",
            organization="DEWA",
            role="MD & CEO",
            event_name="WETEX",
            candidate_url="https://www.linkedin.com/company/dewaofficial",
            snippet="DEWA Official Corporate Page",
            query_used='site:linkedin.com "DEWA"'
        )
        assert eval_res["status"] == "not_found"
        assert "not a personal profile" in eval_res["justification"]


class TestSpecialist3Execution:
    def test_specialist_processes_contact_with_mock_search(self):
        mock_search = MockSearchProvider()
        mock_search.add_canned_result("saeed al tayer", [
            SearchResult(
                title="Saeed Al Tayer - MD & CEO - DEWA | LinkedIn",
                url="https://www.linkedin.com/in/saeed-al-tayer",
                snippet="Saeed Al Tayer is MD & CEO at DEWA, leading Dubai water and energy initiatives and WETEX Chairman.",
                source="mock"
            )
        ])

        specialist = LinkedInSpecialist(search_provider=mock_search)

        contact = {
            "contact_id": "cnt_01",
            "event_name": "WETEX",
            "person_name": {"normalized_value": "HE Saeed Al Tayer"},
            "organisation": {"normalized_value": "DEWA"},
            "role_as_written": {"normalized_value": "MD & CEO"}
        }

        result = specialist.process_single_contact(contact)
        assert result["verification_status"] == "verified"
        assert result["linkedin_url"]["normalized_value"] == "https://www.linkedin.com/in/saeed-al-tayer"
        assert result["linkedin_url"]["extraction_status"] == "verified"
        assert "DEWA" in result["notes"]

    def test_specialist_handles_search_provider_failure(self):
        class FailingSearchProvider(MockSearchProvider):
            def search(self, query: str, num_results: int = 5):
                raise RuntimeError("API Rate limit exceeded (429)")

        specialist = LinkedInSpecialist(search_provider=FailingSearchProvider())

        contact = {
            "contact_id": "cnt_02",
            "event_name": "WETEX",
            "person_name": {"normalized_value": "Some Person"},
            "organisation": {"normalized_value": "DEWA"}
        }

        result = specialist.process_single_contact(contact)
        assert result["verification_status"] == "search_unavailable"
        assert "Rate limit" in result["notes"]

    def test_specialist_file_processing(self, tmp_path):
        input_file = tmp_path / "test_contacts.json"
        output_file = tmp_path / "test_contacts_out.json"
        output_csv = tmp_path / "test_contacts_out.csv"

        mock_search = MockSearchProvider()
        mock_search.add_canned_result("anna", [
            SearchResult(
                title="Anna - Assistant | LinkedIn",
                url="https://www.linkedin.com/in/anna-assistant-dubai",
                snippet="Anna - Executive Assistant based in Dubai.",
                source="mock"
            )
        ])

        contacts = [
            {
                "contact_id": "cnt_03",
                "event_name": "Russian Design Forum",
                "person_name": {"normalized_value": "Assistant Anna"},
                "organisation": {"normalized_value": "OL Interior"}
            }
        ]
        input_file.write_text(json.dumps(contacts), encoding="utf-8")

        specialist = LinkedInSpecialist(search_provider=mock_search)
        results = specialist.process_contacts_file(
            input_path=str(input_file),
            output_json_path=str(output_file),
            output_csv_path=str(output_csv)
        )

        assert len(results) == 1
        assert results[0]["verification_status"] == "needs_review"  # Name matched, but org wasn't in snippet
        assert output_file.exists()
        assert output_csv.exists()

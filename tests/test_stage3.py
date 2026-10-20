"""Unit tests for Stage 3 LinkedIn Discovery and Verification (offline)."""
import pytest
from src.stage3_verification.verifier import evaluate_candidate_match


class TestLinkedInVerification:
    def test_verified_candidate_with_affiliation(self):
        """Candidate with matching name and verified organization/role must be marked verified."""
        res = evaluate_candidate_match(
            person_name="Saeed Mohammed Al Tayer",
            organization="DEWA",
            role="Chairman of WETEX",
            candidate_url="https://www.linkedin.com/in/saeed-al-tayer",
            snippet="HE Saeed Mohammed Al Tayer, MD & CEO of DEWA, Chairman of WETEX"
        )
        assert res["status"] == "verified"
        assert "confirmed" in res["justification"]

    def test_name_match_alone_insufficient(self):
        """Per AGENTS.md, a name match alone is never sufficient; must be flagged as needs_review."""
        res = evaluate_candidate_match(
            person_name="Anna Kovaleva",
            organization="Russian Design Council",
            role="Exhibition Director",
            candidate_url="https://www.linkedin.com/in/anna-kovaleva-random",
            snippet="Anna Kovaleva - Senior Software Engineer at Tech Corp, California"
        )
        assert res["status"] == "needs_review"
        assert "lacks explicit supporting affiliation" in res["justification"]

    def test_unrelated_name_returns_not_found(self):
        """Search result with a different person must return not_found."""
        res = evaluate_candidate_match(
            person_name="Dmitry Smirnov",
            organization="Russian Design Council",
            role="Head of Operations",
            candidate_url="https://www.linkedin.com/in/other-person",
            snippet="Alexey Petrov - Director of Operations"
        )
        assert res["status"] == "not_found"

    def test_missing_candidate_returns_not_found(self):
        """When no candidate URL or snippet is found, status must be not_found without guessing."""
        res = evaluate_candidate_match(
            person_name="Elena Morozova",
            organization="Russian Design Council",
            role="Sponsorship Lead",
            candidate_url=None,
            snippet=None
        )
        assert res["status"] == "not_found"
        assert "No public personal LinkedIn profile indexed" in res["justification"]

"""Unit tests for Stage 1 discovery, normalizer, and parser (offline only)."""
import os
import json
import pytest

from src.models import DiscoveredEvent, FieldEvidence
from src.stage1_discovery.normalizer import normalize_text, normalize_and_validate_url
from src.stage1_discovery.parser import parse_listing_page, extract_external_website

FIXTURES_DIR = os.path.join(os.path.dirname(__file__), "fixtures")


def read_fixture(filename: str) -> str:
    path = os.path.join(FIXTURES_DIR, filename)
    with open(path, "r", encoding="utf-8") as f:
        return f.read()


class TestNormalizer:
    def test_zero_width_character_stripping(self):
        """Zero-width spaces (\\u200b, \\ufeff) must be cleanly stripped."""
        raw = "AccessAbilities Expo \u200b"
        cleaned = normalize_text(raw)
        assert cleaned == "AccessAbilities Expo"
        assert "\u200b" not in cleaned

    def test_empty_and_whitespace_text(self):
        assert normalize_text("") is None
        assert normalize_text("   \n\t  ") is None
        assert normalize_text(None) is None

    def test_url_normalization_clean(self):
        url, status, reason = normalize_and_validate_url("https://example.com/event")
        assert status == "verified"
        assert url == "https://example.com/event"
        assert reason is None

    def test_url_normalization_spaces_in_scheme(self):
        """Handle Invest in Dubai bug: 'http:// www.accessabilitiesexpo.com'."""
        raw = "http:// www.accessabilitiesexpo.com"
        url, status, reason = normalize_and_validate_url(raw)
        assert status == "normalized"
        assert url == "http://www.accessabilitiesexpo.com"

    def test_url_normalization_relative_with_base(self):
        raw = "/en/events-calendar/wetex"
        base = "https://www.investindubai.gov.ae/en/events-calendar?tags=Business+events"
        url, status, reason = normalize_and_validate_url(raw, base_url=base)
        assert status == "normalized"
        assert url == "https://www.investindubai.gov.ae/en/events-calendar/wetex"

    def test_url_suspicious_schemes_and_auth(self):
        # JavaScript scheme
        url, status, reason = normalize_and_validate_url("javascript:void(0)")
        assert status == "suspicious"
        assert url is None

        # Internal portal auth
        raw = "https://app.invest.dubai.ae/login?redirect_url=/en/events"
        url, status, reason = normalize_and_validate_url(raw)
        assert status == "suspicious"
        assert "Internal portal authentication" in reason


class TestListingParser:
    def test_parse_listing_fixture(self):
        """Parse offline listing fixture and verify cards, titles, links, and metadata."""
        html = read_fixture("sample_listing.html")
        listing_url = "https://www.investindubai.gov.ae/en/events-calendar?tags=Business+events"

        events = parse_listing_page(html, listing_url)

        # 2 valid event cards must be discovered (3rd unlinked card omitted)
        assert len(events) == 2

        # First event: AccessAbilities Expo
        ev1 = events[0]
        assert ev1.event_name.normalized_value == "AccessAbilities Expo"
        assert "\u200b" not in ev1.event_name.normalized_value
        assert ev1.event_page_url == "https://www.investindubai.gov.ae/en/events-calendar/accessabilities-expo"
        assert ev1.category is not None
        assert ev1.category.normalized_value == "Exhibition"
        assert ev1.dates_text is not None
        assert "19 Oct" in ev1.dates_text.normalized_value
        assert ev1.listing_page_url == listing_url

        # Second event: WETEX with relative link converted to absolute
        ev2 = events[1]
        assert "WETEX" in ev2.event_name.normalized_value
        assert ev2.event_page_url == "https://www.investindubai.gov.ae/en/events-calendar/wetex"
        assert ev2.category.normalized_value == "Exhibitions"


class TestDetailParser:
    def test_extract_external_website_success(self):
        """Extract external event website and verify normalization and evidence."""
        html = read_fixture("sample_detail_with_website.html")
        detail_url = "https://www.investindubai.gov.ae/en/events-calendar/accessabilities-expo"

        evidence = extract_external_website(html, detail_url)

        assert evidence.extraction_status == "normalized"
        assert evidence.normalized_value == "http://www.accessabilitiesexpo.com"
        assert evidence.raw_value == "http:// www.accessabilitiesexpo.com"
        assert evidence.source_url == detail_url
        assert "More info" in evidence.supporting_snippet

    def test_extract_external_website_missing(self):
        """Verify that pages without external links return not_found without picking internal links."""
        html = read_fixture("sample_detail_missing_website.html")
        detail_url = "https://www.investindubai.gov.ae/en/events-calendar/internal-workshop"

        evidence = extract_external_website(html, detail_url)

        assert evidence.extraction_status == "not_found"
        assert evidence.normalized_value is None
        assert evidence.raw_value is None
        assert evidence.source_url == detail_url
        assert "No external website link found" in evidence.supporting_snippet


class TestDataModelSerialization:
    def test_discovered_event_to_dict_and_json(self):
        name_ev = FieldEvidence(
            raw_value="AccessAbilities Expo \u200b",
            normalized_value="AccessAbilities Expo",
            source_url="https://www.investindubai.gov.ae/en/events-calendar",
            supporting_snippet="<a ...>AccessAbilities Expo</a>"
        )
        web_ev = FieldEvidence(
            raw_value="http:// www.accessabilitiesexpo.com",
            normalized_value="http://www.accessabilitiesexpo.com",
            source_url="https://www.investindubai.gov.ae/en/events-calendar/accessabilities-expo",
            extraction_status="normalized"
        )
        event = DiscoveredEvent(
            event_name=name_ev,
            listing_page_url="https://www.investindubai.gov.ae/en/events-calendar",
            event_page_url="https://www.investindubai.gov.ae/en/events-calendar/accessabilities-expo",
            event_website_url=web_ev,
            retrieval_status="discovered"
        )

        d = event.to_dict()
        assert d["event_name"]["normalized_value"] == "AccessAbilities Expo"
        assert d["event_website_url"]["normalized_value"] == "http://www.accessabilitiesexpo.com"

        # Verify JSON serializability
        serialized = json.dumps(d, indent=2)
        assert "AccessAbilities Expo" in serialized


class MockResponse:
    """Helper mock for urllib.request.urlopen responses."""
    def __init__(self, data_bytes: bytes, status: int = 200, headers=None):
        self.data_bytes = data_bytes
        self.status = status
        self.headers = headers or {}

    def read(self):
        return self.data_bytes

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass


class TestAlgoliaApiClient:
    def test_fetch_page_valid_response(self):
        from unittest.mock import patch
        from src.stage1_discovery.api_client import AlgoliaApiClient

        sample_data = {
            "nbHits": 1,
            "nbPages": 1,
            "hits": [{"title": "AccessAbilities Expo", "urlSlug": "accessabilities-expo"}]
        }
        mock_resp = MockResponse(json.dumps(sample_data).encode("utf-8"))

        with patch("urllib.request.urlopen", return_value=mock_resp):
            client = AlgoliaApiClient()
            result = client.fetch_page(page=0)
            assert result["nbHits"] == 1
            assert len(result["hits"]) == 1
            assert result["hits"][0]["title"] == "AccessAbilities Expo"

    def test_fetch_all_events_pagination(self):
        from unittest.mock import patch
        from src.stage1_discovery.api_client import AlgoliaApiClient

        page0 = {
            "nbHits": 3,
            "nbPages": 2,
            "hits": [
                {"title": "Event 1", "urlSlug": "event-1"},
                {"title": "Event 2", "urlSlug": "event-2"}
            ]
        }
        page1 = {
            "nbHits": 3,
            "nbPages": 2,
            "hits": [
                {"title": "Event 3", "urlSlug": "event-3"}
            ]
        }

        def mock_side_effect(req, timeout=15):
            body = json.loads(req.data.decode("utf-8"))
            page = body.get("page", 0)
            data = page0 if page == 0 else page1
            return MockResponse(json.dumps(data).encode("utf-8"))

        with patch("urllib.request.urlopen", side_effect=mock_side_effect):
            client = AlgoliaApiClient()
            all_hits, total = client.fetch_all_events()
            assert total == 3
            assert len(all_hits) == 3
            titles = [h["title"] for h in all_hits]
            assert titles == ["Event 1", "Event 2", "Event 3"]

    def test_fetch_page_http_failure(self):
        import urllib.error
        from unittest.mock import patch
        from src.stage1_discovery.api_client import AlgoliaApiClient

        http_err = urllib.error.HTTPError("https://api", 500, "Internal Server Error", {}, None)
        with patch("urllib.request.urlopen", side_effect=http_err):
            client = AlgoliaApiClient()
            with pytest.raises(urllib.error.HTTPError) as exc_info:
                client.fetch_page(page=0)
            assert exc_info.value.code == 500

    def test_fetch_page_network_connection_error(self):
        import urllib.error
        from unittest.mock import patch
        from src.stage1_discovery.api_client import AlgoliaApiClient

        url_err = urllib.error.URLError("Connection refused")
        with patch("urllib.request.urlopen", side_effect=url_err):
            client = AlgoliaApiClient()
            with pytest.raises(ConnectionError) as exc_info:
                client.fetch_page(page=0)
            assert "Network error querying Algolia API" in str(exc_info.value)

    def test_fetch_page_malformed_json(self):
        from unittest.mock import patch
        from src.stage1_discovery.api_client import AlgoliaApiClient

        mock_resp = MockResponse(b"<html><head><title>Error</title></head><body>502 Bad Gateway</body></html>")
        with patch("urllib.request.urlopen", return_value=mock_resp):
            client = AlgoliaApiClient()
            with pytest.raises(ValueError) as exc_info:
                client.fetch_page(page=0)
            assert "Malformed JSON response" in str(exc_info.value)


class TestAlgoliaParser:
    def test_parse_algolia_hit_valid_website(self):
        from src.stage1_discovery.parser import parse_algolia_hit

        hit = {
            "objectID": "evt-101",
            "title": "AccessAbilities Expo",
            "urlSlug": "accessabilities-expo",
            "listingvendorswebsite": "https://www.accessabilitiesexpo.com",
            "category": ["Exhibition"],
            "datesRange": {"from_formatted": "19 Oct 2026", "to_formatted": "21 Oct 2026"},
            "phone": "+971 4 252 7959"
        }
        event = parse_algolia_hit(hit)
        assert event is not None
        assert event.event_name.normalized_value == "AccessAbilities Expo"
        assert event.event_page_url == "https://www.investindubai.gov.ae/en/events-calendar/accessabilities-expo"
        assert event.event_website_url.normalized_value == "https://www.accessabilitiesexpo.com"
        assert event.event_website_url.extraction_status == "verified"
        assert event.category.normalized_value == "Exhibition"
        assert event.dates_text.normalized_value == "19 Oct 2026 to 21 Oct 2026"
        assert event.phone.normalized_value == "+971 4 252 7959"
        assert event.retrieval_status == "succeeded"

    def test_parse_algolia_hit_url_normalization(self):
        from src.stage1_discovery.parser import parse_algolia_hit

        hit = {
            "objectID": "evt-102",
            "title": "AccessAbilities Expo \u200b",
            "urlSlug": "accessabilities-expo",
            "listingvendorswebsite": "http:// www.accessabilitiesexpo.com"
        }
        event = parse_algolia_hit(hit)
        assert event.event_name.normalized_value == "AccessAbilities Expo"
        assert "\u200b" not in event.event_name.normalized_value
        assert event.event_website_url.normalized_value == "http://www.accessabilitiesexpo.com"
        assert event.event_website_url.extraction_status == "normalized"
        assert event.retrieval_status == "succeeded"

    def test_parse_algolia_hit_missing_website(self):
        from src.stage1_discovery.parser import parse_algolia_hit

        hit = {
            "objectID": "evt-103",
            "title": "Internal Workshop",
            "urlSlug": "internal-workshop",
            "listingvendorswebsite": ""
        }
        event = parse_algolia_hit(hit)
        assert event.event_name.normalized_value == "Internal Workshop"
        assert event.event_website_url.normalized_value is None
        assert event.event_website_url.extraction_status == "not_found"
        assert event.retrieval_status == "incomplete"

    def test_parse_algolia_hit_empty_title_skipped(self):
        from src.stage1_discovery.parser import parse_algolia_hit

        hit = {"objectID": "evt-999", "title": "   \n\t  ", "urlSlug": "empty"}
        assert parse_algolia_hit(hit) is None

    def test_parse_algolia_hits_duplicate_prevention(self):
        from src.stage1_discovery.parser import parse_algolia_hits

        hits = [
            {"objectID": "1", "title": "Forum A", "urlSlug": "forum-a", "listingvendorswebsite": "https://a.com"},
            {"objectID": "2", "title": "Forum A", "urlSlug": "forum-a", "listingvendorswebsite": "https://a.com"},
            {"objectID": "3", "title": "Forum B", "urlSlug": "forum-b", "listingvendorswebsite": "https://b.com"}
        ]
        events = parse_algolia_hits(hits)
        assert len(events) == 2
        assert [e.event_name.normalized_value for e in events] == ["Forum A", "Forum B"]

    def test_parse_algolia_hits_empty_results(self):
        from src.stage1_discovery.parser import parse_algolia_hits

        assert parse_algolia_hits([]) == []


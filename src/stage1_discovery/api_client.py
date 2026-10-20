"""Algolia Search API Client for Invest in Dubai Business Events."""
import json
import urllib.request
import urllib.error
from typing import Dict, Any, List, Tuple, Optional

DEFAULT_APP_ID = "V3CV7A7CMC"
DEFAULT_API_KEY = "35a59b61c1577464818fdb267015c3d2"
DEFAULT_INDEX_NAME = "prod104_vd_en"
DEFAULT_TIMEOUT_SECONDS = 15


class AlgoliaApiClient:
    """Client for querying the Invest in Dubai official Algolia events feed."""

    def __init__(
        self,
        app_id: str = DEFAULT_APP_ID,
        api_key: str = DEFAULT_API_KEY,
        index_name: str = DEFAULT_INDEX_NAME,
        timeout: int = DEFAULT_TIMEOUT_SECONDS
    ):
        self.app_id = app_id
        self.api_key = api_key
        self.index_name = index_name
        self.timeout = timeout
        self.endpoint_url = f"https://{self.app_id}-dsn.algolia.net/1/indexes/{self.index_name}/query"

    def fetch_page(
        self,
        page: int = 0,
        hits_per_page: int = 50,
        tag_filter: str = "Business events"
    ) -> Dict[str, Any]:
        """
        Fetch a single page of events matching the tag filter.

        Args:
            page: 0-indexed page number.
            hits_per_page: Number of hits per page.
            tag_filter: Tag filter (e.g. 'Business events').

        Returns:
            Decoded JSON dictionary from the Algolia response.

        Raises:
            urllib.error.HTTPError: On HTTP error response (4xx, 5xx).
            urllib.error.URLError: On network connection failure or timeout.
            ValueError: On invalid / malformed JSON response.
        """
        payload = {
            "query": "",
            "facetFilters": [
                ["type:Event"],
                [f"tags:{tag_filter}"]
            ],
            "hitsPerPage": hits_per_page,
            "page": page
        }

        headers = {
            "x-algolia-application-id": self.app_id,
            "x-algolia-api-key": self.api_key,
            "Content-Type": "application/json; charset=UTF-8",
            "User-Agent": "InvestInDubai-EventDiscovery/1.0"
        }

        req = urllib.request.Request(
            self.endpoint_url,
            data=json.dumps(payload).encode("utf-8"),
            headers=headers,
            method="POST"
        )

        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                status_code = resp.status
                if status_code >= 400:
                    raise urllib.error.HTTPError(
                        self.endpoint_url, status_code, f"HTTP Error {status_code}", resp.headers, None
                    )
                raw_bytes = resp.read()
                try:
                    return json.loads(raw_bytes.decode("utf-8"))
                except (json.JSONDecodeError, UnicodeDecodeError) as err:
                    raise ValueError(f"Malformed JSON response from Algolia API: {err}") from err

        except urllib.error.HTTPError:
            raise
        except urllib.error.URLError as err:
            raise ConnectionError(f"Network error querying Algolia API at {self.endpoint_url}: {err}") from err

    def fetch_all_events(
        self,
        hits_per_page: int = 50,
        tag_filter: str = "Business events"
    ) -> Tuple[List[Dict[str, Any]], int]:
        """
        Fetch all events across all pages dynamically based on pagination metadata.

        Returns:
            Tuple of (all_hits_list, total_reported_hits).
        """
        first_page = self.fetch_page(page=0, hits_per_page=hits_per_page, tag_filter=tag_filter)
        total_hits = first_page.get("nbHits", 0)
        total_pages = first_page.get("nbPages", 1)
        all_hits = list(first_page.get("hits", []))

        for current_page in range(1, total_pages):
            page_data = self.fetch_page(page=current_page, hits_per_page=hits_per_page, tag_filter=tag_filter)
            all_hits.extend(page_data.get("hits", []))

        return all_hits, total_hits

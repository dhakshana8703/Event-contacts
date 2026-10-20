"""Specialist 1: Event Web Scout & In-Memory Page Inspector.

Discovers high-value contact, committee, and leadership pages on an event website
in-memory without saving raw HTML dumps to disk.
"""
import re
import urllib.parse
import urllib.request
import urllib.error
from typing import List, Dict, Tuple, Optional, Set
from bs4 import BeautifulSoup


# High-value keywords appearing in URL slugs, link texts, or accessibility labels
SCOUT_KEYWORDS = [
    (10, 'organising-committee'),
    (10, 'organizing-committee'),
    (9, 'committee'),
    (9, 'secretariat'),
    (8, 'contact-us'),
    (8, 'contactus'),
    (8, 'contacts'),
    (7, 'leadership'),
    (7, 'governance'),
    (7, 'team'),
    (7, 'management'),
    (6, 'about-us'),
    (6, 'about'),
    (5, 'patronage'),
    (5, 'advisory-board'),
    (5, 'show-info'),
    (4, 'event-team'),
]

# External domains to ignore when scouting internal pages
IGNORED_DOMAINS = {
    'facebook.com', 'twitter.com', 'x.com', 'linkedin.com', 'instagram.com',
    'youtube.com', 'google.com', 'apple.com', 'play.google.com', 'wa.me',
    't.me', 'telegram.me', 'investindubai.gov.ae', 'visitdubai.com'
}


class EventWebScout:
    """In-memory event website scout and navigation inspector."""

    def __init__(self, timeout: int = 15, user_agent: Optional[str] = None, browser_client: Optional[Any] = None):
        self.timeout = timeout
        self.user_agent = user_agent or "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
        self.browser_client = browser_client

    def fetch_url_content(self, url: str) -> Tuple[Optional[str], str, int]:
        """
        Fetch web page content directly into memory.
        Uses browser_client (Playwright) if available, falling back to urllib.
        Returns (html_content, final_url, status_code).
        """
        if self.browser_client:
            try:
                html, status, err = self.browser_client.fetch_page_content(url)
                if html and status < 400:
                    return html, url, status
            except Exception:
                pass

        headers = {
            "User-Agent": "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 (KHTML, like Gecko) Chrome/124.0.0.0 Safari/537.36 Edg/124.0.0.0",
            "Accept": "text/html,application/xhtml+xml,application/xml;q=0.9,image/avif,image/webp,*/*;q=0.8",
            "Accept-Language": "en-US,en;q=0.5",
        }
        req = urllib.request.Request(url, headers=headers)
        try:
            with urllib.request.urlopen(req, timeout=self.timeout) as resp:
                final_url = resp.geturl()
                status = resp.getcode()
                raw = resp.read()
                try:
                    html = raw.decode("utf-8")
                except UnicodeDecodeError:
                    html = raw.decode("latin-1", errors="replace")
                return html, final_url, status
        except urllib.error.HTTPError as e:
            return None, url, e.code
        except Exception:
            return None, url, 0

    def discover_contact_links(self, html_content: str, base_url: str) -> List[Tuple[str, str, int]]:
        """
        Inspect navigation links and score candidate contact/team pages.
        Returns list of (absolute_url, link_text, priority_score) sorted descending.
        """
        soup = BeautifulSoup(html_content, "html.parser")
        base_domain = urllib.parse.urlparse(base_url).netloc.lower()

        candidates: List[Tuple[str, str, int]] = []
        seen_urls: Set[str] = set()

        for a_tag in soup.find_all("a", href=True):
            raw_href = a_tag["href"].strip()
            if not raw_href or raw_href.startswith(("#", "javascript:", "mailto:", "tel:")):
                continue

            # Resolve relative URL
            abs_url = urllib.parse.urljoin(base_url, raw_href)
            parsed = urllib.parse.urlparse(abs_url)

            # Keep only HTTP/HTTPS
            if parsed.scheme not in ("http", "https"):
                continue

            # Strip fragments and query parameters for deduplication
            clean_url = f"{parsed.scheme}://{parsed.netloc}{parsed.path}".rstrip("/")
            if not clean_url or clean_url in seen_urls:
                continue

            # Reject known external generic/social domains
            if any(d in parsed.netloc.lower() for d in IGNORED_DOMAINS):
                continue

            # Check internal domain (must match base domain or subdomain)
            if base_domain and not (parsed.netloc.lower() == base_domain or parsed.netloc.lower().endswith("." + base_domain)):
                continue

            link_text = a_tag.get_text(separator=" ", strip=True)
            aria_label = a_tag.get("aria-label", "")
            title_attr = a_tag.get("title", "")
            combined_label = f"{link_text} {aria_label} {title_attr}".lower()
            path_slug = parsed.path.lower()

            # Score by keywords in slug or link text
            score = 0
            for weight, kw in SCOUT_KEYWORDS:
                if kw in path_slug:
                    score += weight * 2  # URL slug is very strong signal
                if kw in combined_label:
                    score += weight

            # Bonus for header / footer location
            parent_tag = a_tag.find_parent(["footer", "nav", "header"])
            if parent_tag:
                if parent_tag.name == "footer" and any(k in path_slug for k in ["contact", "about"]):
                    score += 3
                elif parent_tag.name == "nav":
                    score += 2

            if score > 0:
                seen_urls.add(clean_url)
                display_label = link_text or aria_label or path_slug
                candidates.append((clean_url, display_label, score))

        # Sort descending by priority score
        candidates.sort(key=lambda x: x[2], reverse=True)
        return candidates

    def scout_event_pages(self, event_website_url: str, max_subpages: int = 2) -> List[Dict[str, Any]]:
        """
        Scout event website in-memory. Fetches homepage and top candidate subpages.
        Returns list of inspected pages with in-memory HTML.
        """
        pages: List[Dict[str, Any]] = []

        # 1. Fetch homepage in-memory
        homepage_html, final_url, status = self.fetch_url_content(event_website_url)
        if not homepage_html or status not in (200, 301, 302):
            pages.append({
                "url": event_website_url,
                "html": None,
                "status": f"HTTP {status}" if status else "network_error",
                "is_homepage": True
            })
            return pages

        pages.append({
            "url": final_url,
            "html": homepage_html,
            "status": "success",
            "is_homepage": True
        })

        # 2. Discover high-priority subpages from navigation
        candidate_links = self.discover_contact_links(homepage_html, final_url)

        # 3. Fetch up to max_subpages in-memory
        fetched_count = 0
        for sub_url, label, score in candidate_links:
            if fetched_count >= max_subpages:
                break
            if sub_url == final_url:
                continue

            sub_html, sub_final, sub_status = self.fetch_url_content(sub_url)
            if sub_html and sub_status == 200:
                pages.append({
                    "url": sub_final,
                    "html": sub_html,
                    "status": "success",
                    "label": label,
                    "priority_score": score,
                    "is_homepage": False
                })
                fetched_count += 1

        return pages

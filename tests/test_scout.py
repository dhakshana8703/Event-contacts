"""Tests for Specialist 1: EventWebScout."""
import pytest
from src.stage2_contacts.scout import EventWebScout, SCOUT_KEYWORDS


class TestEventWebScout:
    def test_discover_contact_links_scoring_and_filtering(self):
        scout = EventWebScout()
        sample_html = """
        <html>
        <header>
            <nav>
                <a href="/en/home">Home</a>
                <a href="/en/organising-committee">Organizing Committee</a>
                <a href="/en/about-wetex">Know More</a>
                <a href="/en/contact-us">Contact</a>
                <a href="https://instagram.com/wetex">Follow Instagram</a>
                <a href="https://external-ticket-vendor.com/buy">Buy Tickets</a>
            </nav>
        </header>
        <body>
            <div class="hero">
                <a href="/leadership">Discover Our Leaders</a>
            </div>
        </body>
        <footer>
            <a href="/en/contact-us">Footer Contact</a>
        </footer>
        </html>
        """
        links = scout.discover_contact_links(sample_html, "https://wetex.ae/en/home")
        urls = [url for url, label, score in links]

        # Top candidate must be organizing committee
        assert "https://wetex.ae/en/organising-committee" in urls
        assert "https://wetex.ae/en/contact-us" in urls
        assert "https://wetex.ae/leadership" in urls

        # Social media and external tickets must be excluded
        assert not any("instagram.com" in u for u in urls)
        assert not any("external-ticket-vendor.com" in u for u in urls)

        # Committee should rank higher than generic about
        scores = {url: score for url, label, score in links}
        assert scores["https://wetex.ae/en/organising-committee"] > scores.get("https://wetex.ae/en/about-wetex", 0)

    def test_know_more_link_with_descriptive_href(self):
        scout = EventWebScout()
        sample_html = """
        <div>
            <!-- Vague anchor text, but clear URL path -->
            <a href="/about-the-show/governance">Know More</a>
            <a href="/show-info/secretariat-team">Explore</a>
        </div>
        """
        links = scout.discover_contact_links(sample_html, "https://eventdubai.com")
        urls = [url for url, label, score in links]

        assert "https://eventdubai.com/about-the-show/governance" in urls
        assert "https://eventdubai.com/show-info/secretariat-team" in urls

    def test_fetch_url_content_handles_invalid_url_gracefully(self):
        scout = EventWebScout(timeout=1)
        html, final_url, status = scout.fetch_url_content("http://invalid-non-existent-domain-123456.ae")
        assert html is None
        assert status == 0

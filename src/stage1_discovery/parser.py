"""Deterministic HTML parsing for Stage 1 event and website discovery."""
from bs4 import BeautifulSoup
import re
from typing import List, Optional, Tuple
from urllib.parse import urlparse

from src.models import DiscoveredEvent, FieldEvidence, current_iso_timestamp
from src.stage1_discovery.normalizer import normalize_text, normalize_and_validate_url

# Domains considered internal to the event portal or generic platforms
INTERNAL_OR_GENERIC_DOMAINS = {
    'investindubai.gov.ae',
    'visitdubai.com',
    'dubai.ae',
    'twitter.com',
    'x.com',
    'facebook.com',
    'instagram.com',
    'linkedin.com',
    'youtube.com',
    'google.com',
    'schema.org',
    'w3.org',
}


def parse_listing_page(html_content: str, listing_url: str) -> List[DiscoveredEvent]:
    """
    Parse an events calendar listing page and extract discovered event cards.

    Args:
        html_content: Raw HTML string of the listing page.
        listing_url: The URL of the listing page.

    Returns:
        List of DiscoveredEvent records with evidence.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    discovered_events: List[DiscoveredEvent] = []

    # Target cards by specific class, falling back to items containing event detail links
    cards = soup.select('.events__item')
    if not cards:
        # Fallback for alternative grid structures
        cards = soup.find_all(attrs={'class': re.compile(r'event(s)?[-_](item|card)', re.I)})

    for card in cards:
        # Find title anchor
        title_link = card.select_one('a.events__item-title')
        if not title_link:
            title_link = card.find('a', href=re.compile(r'/events-calendar/[^?#]+'))

        if not title_link:
            # Card without event title/link is incomplete/unlinked
            continue

        raw_title = title_link.get_text(separator=' ', strip=True)
        if not raw_title and title_link.get('aria-label'):
            raw_title = title_link['aria-label']

        clean_title = normalize_text(raw_title)
        if not clean_title:
            continue

        raw_href = title_link.get('href', '').strip()
        norm_href, href_status, _ = normalize_and_validate_url(raw_href, base_url=listing_url)

        title_evidence = FieldEvidence(
            raw_value=raw_title,
            normalized_value=clean_title,
            source_url=listing_url,
            supporting_snippet=str(title_link)[:300],
            extraction_status="extracted"
        )

        # Optional metadata
        category_el = card.select_one('.events__text-info--category')
        category_evidence = None
        if category_el:
            raw_cat = category_el.get_text(separator=' ', strip=True)
            norm_cat = normalize_text(raw_cat)
            if norm_cat:
                category_evidence = FieldEvidence(
                    raw_value=raw_cat,
                    normalized_value=norm_cat,
                    source_url=listing_url,
                    supporting_snippet=str(category_el)[:200],
                    extraction_status="extracted"
                )

        date_el = card.select_one('.events__date-item')
        date_evidence = None
        if date_el:
            raw_date = date_el.get_text(separator=' ', strip=True)
            norm_date = normalize_text(raw_date)
            if norm_date:
                date_evidence = FieldEvidence(
                    raw_value=raw_date,
                    normalized_value=norm_date,
                    source_url=listing_url,
                    supporting_snippet=str(date_el)[:200],
                    extraction_status="extracted"
                )

        event = DiscoveredEvent(
            event_name=title_evidence,
            listing_page_url=listing_url,
            event_page_url=norm_href,
            category=category_evidence,
            dates_text=date_evidence,
            retrieval_status="discovered"
        )
        discovered_events.append(event)

    return discovered_events


def extract_external_website(html_content: str, event_page_url: str) -> FieldEvidence:
    """
    Extract the external official event website from an event detail page.

    Filters out internal portal links, social networks, and auth redirects.

    Args:
        html_content: HTML content of the event detail page.
        event_page_url: The URL of the event detail page.

    Returns:
        FieldEvidence representing the discovered external website, or 'not_found' evidence.
    """
    soup = BeautifulSoup(html_content, 'html.parser')

    # Candidate links collected with relevance score: (score, a_tag, reason)
    candidates = []

    # Priority 1: Check known button boxes and CTAs
    button_boxes = soup.select('.button-links-box a, .events__reminder-cta, .btn')
    for a in button_boxes:
        href = a.get('href', '').strip()
        if href:
            candidates.append((10, a, "button_cta"))

    # Priority 2: Check all anchors for external URLs
    for a in soup.find_all('a', href=True):
        href = a['href'].strip()
        text = a.get_text(separator=' ', strip=True).lower()
        aria = a.get('aria-label', '').lower()

        if any(w in text or w in aria for w in ['website', 'more info', 'official', 'visit']):
            candidates.append((8, a, "keyword_match"))
        elif a.get('target') == '_blank':
            candidates.append((5, a, "blank_target"))
        elif href.startswith('http'):
            candidates.append((2, a, "external_link"))

    # Sort descending by priority score
    candidates.sort(key=lambda x: x[0], reverse=True)

    for score, a_tag, reason in candidates:
        raw_href = a_tag.get('href', '').strip()
        if not raw_href:
            continue

        normalized_url, status, error_reason = normalize_and_validate_url(raw_href, base_url=event_page_url)
        if status in ('null', 'suspicious'):
            continue

        parsed = urlparse(normalized_url)
        domain = parsed.netloc.lower()
        if any(domain == d or domain.endswith('.' + d) for d in INTERNAL_OR_GENERIC_DOMAINS):
            continue

        # Valid external website identified
        supporting_text = a_tag.get_text(separator=' ', strip=True) or a_tag.get('aria-label', '')
        snippet = f"Link text: '{supporting_text}' | Tag: {str(a_tag)[:250]}"

        return FieldEvidence(
            raw_value=raw_href,
            normalized_value=normalized_url,
            source_url=event_page_url,
            supporting_snippet=snippet,
            extraction_status=status
        )

    # If no qualifying external website was found
    return FieldEvidence(
        raw_value=None,
        normalized_value=None,
        source_url=event_page_url,
        supporting_snippet="No external website link found on inspected detail page",
        extraction_status="not_found"
    )


def parse_algolia_hit(hit: dict, listing_url: str = "https://www.investindubai.gov.ae/en/events-calendar?tags=Business+events") -> Optional[DiscoveredEvent]:
    """
    Parse a single event object from the Algolia search feed into a DiscoveredEvent record.

    Args:
        hit: Dictionary representing the Algolia hit.
        listing_url: Source listing URL for provenance tracking.

    Returns:
        DiscoveredEvent record, or None if the hit lacks a valid title.
    """
    # 1. Event title
    title_val = hit.get("title")
    if isinstance(title_val, list):
        raw_title = title_val[0] if title_val else ""
    else:
        raw_title = str(title_val or "")

    clean_title = normalize_text(raw_title)
    if not clean_title:
        return None

    object_id = hit.get("objectID", "")
    title_evidence = FieldEvidence(
        raw_value=raw_title,
        normalized_value=clean_title,
        source_url=listing_url,
        supporting_snippet=f"Algolia objectID: {object_id} | Title: '{raw_title}'",
        extraction_status="extracted"
    )

    # 2. Event detail URL from urlSlug
    slug = hit.get("urlSlug", "").strip()
    if slug:
        event_page_url = f"https://www.investindubai.gov.ae/en/events-calendar/{slug}"
    else:
        event_page_url = None

    # 3. External event website from listingvendorswebsite
    raw_website = hit.get("listingvendorswebsite")
    if raw_website and isinstance(raw_website, str) and raw_website.strip():
        norm_url, status, _ = normalize_and_validate_url(raw_website, base_url=event_page_url or listing_url)
        website_evidence = FieldEvidence(
            raw_value=raw_website,
            normalized_value=norm_url,
            source_url=event_page_url or listing_url,
            supporting_snippet=f"Algolia hit 'listingvendorswebsite': '{raw_website}'",
            extraction_status=status
        )
    else:
        website_evidence = FieldEvidence(
            raw_value=None,
            normalized_value=None,
            source_url=event_page_url or listing_url,
            supporting_snippet="listingvendorswebsite field is absent or empty in Algolia hit",
            extraction_status="not_found"
        )

    # 4. Category
    cat_val = hit.get("category")
    category_evidence = None
    if cat_val:
        raw_cat = cat_val[0] if isinstance(cat_val, list) and cat_val else str(cat_val)
        norm_cat = normalize_text(raw_cat)
        if norm_cat:
            category_evidence = FieldEvidence(
                raw_value=raw_cat,
                normalized_value=norm_cat,
                source_url=listing_url,
                supporting_snippet=f"Algolia category: {cat_val}",
                extraction_status="extracted"
            )

    # 5. Dates
    dates_range = hit.get("datesRange", {})
    from_date = dates_range.get("from_formatted")
    to_date = dates_range.get("to_formatted")
    dates_evidence = None
    if from_date and to_date:
        dates_str = f"{from_date} to {to_date}" if from_date != to_date else from_date
        dates_evidence = FieldEvidence(
            raw_value=dates_str,
            normalized_value=dates_str,
            source_url=listing_url,
            supporting_snippet=f"Algolia datesRange: {dates_range}",
            extraction_status="extracted"
        )

    # 6. Venue / Address
    address_val = hit.get("address") or hit.get("location")
    venue_evidence = None
    if address_val:
        raw_venue = address_val[0] if isinstance(address_val, list) and address_val else str(address_val)
        norm_venue = normalize_text(raw_venue)
        if norm_venue:
            venue_evidence = FieldEvidence(
                raw_value=raw_venue,
                normalized_value=norm_venue,
                source_url=listing_url,
                supporting_snippet=f"Algolia address/location: '{raw_venue}'",
                extraction_status="extracted"
            )

    # 7. Phone
    phone_val = hit.get("phone")
    phone_evidence = None
    if phone_val and isinstance(phone_val, str) and phone_val.strip():
        norm_phone = normalize_text(phone_val)
        if norm_phone:
            phone_evidence = FieldEvidence(
                raw_value=phone_val,
                normalized_value=norm_phone,
                source_url=listing_url,
                supporting_snippet=f"Algolia phone: '{phone_val}'",
                extraction_status="extracted"
            )

    retrieval_status = "succeeded" if website_evidence.normalized_value else "incomplete"

    return DiscoveredEvent(
        event_name=title_evidence,
        listing_page_url=listing_url,
        event_page_url=event_page_url,
        event_website_url=website_evidence,
        category=category_evidence,
        dates_text=dates_evidence,
        venue=venue_evidence,
        phone=phone_evidence,
        retrieval_status=retrieval_status
    )


def parse_algolia_hits(hits: List[dict], listing_url: str = "https://www.investindubai.gov.ae/en/events-calendar?tags=Business+events") -> List[DiscoveredEvent]:
    """
    Parse a list of Algolia hit objects into deduplicated DiscoveredEvent records.

    Args:
        hits: List of hit dictionaries from Algolia response.
        listing_url: Source listing URL for provenance.

    Returns:
        List of unique DiscoveredEvent records.
    """
    events: List[DiscoveredEvent] = []
    seen_identifiers = set()

    for hit in hits:
        event = parse_algolia_hit(hit, listing_url=listing_url)
        if not event:
            continue

        # Deduplicate by unique slug or normalized event name
        key = (event.event_page_url or event.event_name.normalized_value or "").lower()
        if key in seen_identifiers:
            continue
        seen_identifiers.add(key)
        events.append(event)

    return events


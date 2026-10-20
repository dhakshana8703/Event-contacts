"""Deterministic HTML parsing for Stage 2 event-team contact extraction."""
from bs4 import BeautifulSoup
import re
import urllib.parse
from typing import List, Optional, Tuple, Dict, Any

from src.models import EventContact, FieldEvidence, current_iso_timestamp
from src.stage1_discovery.normalizer import normalize_text

# Keywords indicating event management/organization responsibility
ORGANIZER_ROLE_KEYWORDS = {
    'organi', 'director', 'manager', 'lead', 'head', 'coordinator',
    'committee', 'officer', 'executive', 'operations', 'inquiries',
    'handling', 'secretary', 'chair', 'planner', 'producer',
    'founder', 'creator', 'assistant', 'curator'
}

# Roles that should NOT be classified as event organizers without explicit organizing evidence
EXCLUDED_ROLES = {
    'speaker', 'keynote', 'panelist', 'moderator', 'attendee', 'delegate',
    'sponsor', 'exhibitor', 'visitor', 'guest'
}

# Common non-person section headings and navigational labels
NON_PERSON_HEADINGS = {
    'contact us', 'contact', 'contacts', 'about us', 'about', 'get in touch',
    'enquiry', 'enquiries', 'location', 'office', 'head office', 'address',
    'quick links', 'navigation', 'home', 'privacy policy', 'terms of service',
    'social media', 'follow us', 'general enquiries', 'media enquiries',
    'exhibit with us', 'visit us', 'subscribe', 'newsletter', 'write to us',
    'send a message', 'message us', 'dubai', 'uae', 'reach us', 'working hours',
    'our team', 'meet the team', 'organizing committee', 'management team'
}


def is_plausible_person_name(name: Optional[str]) -> bool:
    """Validate that text looks like an individual person's name rather than a UI heading."""
    if not name or len(name) < 3 or len(name) > 60:
        return False
    lower = name.lower().strip()
    if lower in NON_PERSON_HEADINGS:
        return False
    if any(lower.startswith(prefix) for prefix in ['contact', 'about ', 'get in', 'send ', 'our ', 'meet ', 'for ', 'to ', 'view ', 'read ']):
        return False
    # Reject strings with email, url, digits, or non-name symbols
    if re.search(r'[@://0-9\(\)\[\]\{\}]', name):
        return False
    # Reject strings containing event-type or departmental nouns
    non_person_words = {
        'forum', 'expo', 'summit', 'conference', 'exhibition', 'festival',
        'meeting', 'congress', 'symposium', 'event', 'events', 'inquiries',
        'enquiries', 'sales', 'support', 'service', 'services', 'sponsorship',
        'registration', 'information', 'desk', 'office', 'department',
        'press', 'media', 'marketing', 'delegates', 'visitors', 'exhibitors',
        'partnership', 'partnerships', 'booking', 'stands', 'booths'
    }
    tokens = [t for t in re.split(r'\s+', name) if t]
    if any(t.lower() in non_person_words for t in tokens):
        return False
    # Must consist of reasonable name tokens
    if not (1 <= len(tokens) <= 5):
        return False
    return True


def is_qualifying_organizer_role(role_text: Optional[str]) -> bool:
    """Check if the published role explicitly relates to event organization or management."""
    if not role_text:
        return False
    lower = role_text.lower()
    # Check if it has excluded keywords without organizing terms
    has_excluded = any(ex in lower for ex in EXCLUDED_ROLES)
    has_organizer = any(org in lower for org in ORGANIZER_ROLE_KEYWORDS)
    if has_excluded and not has_organizer:
        return False
    return has_organizer


def extract_all_emails_from_container(container) -> List[str]:
    """Extract all valid, unique email addresses from a container element or text."""
    found: List[str] = []

    # 1. Inspect mailto links
    for a in container.select('a[href^="mailto:"]'):
        href_val = a['href'].replace('mailto:', '').split('?')[0].strip()
        text_val = a.get_text(strip=True)
        for cand in [href_val, text_val]:
            for token in re.split(r'[\s,;]+', cand):
                token = token.strip()
                if '@' in token and re.match(r'^[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}$', token):
                    if token.lower() not in [f.lower() for f in found]:
                        found.append(token)

    # 2. Inspect container text via regex
    for m in re.finditer(r'[a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,}', container.get_text()):
        em = m.group(0).strip()
        if em.lower() not in [f.lower() for f in found]:
            found.append(em)

    return found


def extract_all_phones_from_container(container) -> List[str]:
    """Extract all valid, unique phone numbers from a container element or text."""
    candidates: List[str] = []

    # 1. Inspect tel links (check visible text first, then decoded href)
    for a in container.select('a[href^="tel:"]'):
        text_val = a.get_text(strip=True)
        raw_href = urllib.parse.unquote(a['href'].replace('tel:', '').strip())
        for cand in [text_val, raw_href]:
            norm_cand = re.sub(r'\s+', ' ', cand).strip()
            if norm_cand and sum(c.isdigit() for c in norm_cand) >= 7:
                candidates.append(norm_cand)

    # 2. Inspect container text via regex
    for m in re.finditer(r'(\+?\d[\d -]{7,}\d)', container.get_text()):
        ph = re.sub(r'\s+', ' ', m.group(0)).strip()
        digits_count = sum(c.isdigit() for c in ph)
        if (
            digits_count >= 7
            and not ph.startswith('202')
            and not ph.startswith('100000')
            and not ph.startswith('179')
            and '-' not in ph[:3]
        ):
            candidates.append(ph)

    # Deduplicate by digits; preserve formatting of first occurrence
    deduped: List[str] = []
    seen_digit_keys = set()
    for cand in candidates:
        digits = re.sub(r'\D', '', cand)
        if digits and digits not in seen_digit_keys:
            seen_digit_keys.add(digits)
            deduped.append(cand)

    return deduped


def extract_contacts_from_html(html_content: str, source_url: str, event_name: str) -> List[EventContact]:
    """
    Parse HTML content in memory and extract event-team contacts with field-level evidence.

    Args:
        html_content: Rendered HTML string of the contact/team page.
        source_url: The exact URL where the content was retrieved.
        event_name: The name of the event.

    Returns:
        List of EventContact records.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    page_text = soup.get_text()
    contacts: List[EventContact] = []

    # Identify potential contact containers / cards
    containers = soup.select('.organizer, .contact-card, .team-member, .committee-member, .team__item')
    if not containers:
        containers = soup.find_all(attrs={'class': re.compile(r'(organi[sz]|contact|team[-_]item|member[-_]card)', re.I)})

    # Also inspect dedicated contact sections (e.g. #cont, #contact, #team) for direct contact entries
    contact_sections = soup.find_all(attrs={'id': re.compile(r'^(cont|contact|team)', re.I)})
    for sec in contact_sections:
        for child in sec.find_all(['div', 'li', 'section']):
            if child.find('a', href=re.compile(r'^(tel:|mailto:)')):
                h = child.find(['h2', 'h3', 'h4', 'h5', 'strong', '.name'])
                if h and is_plausible_person_name(normalize_text(h.get_text(strip=True))):
                    if child not in containers:
                        containers.append(child)

    for container in containers:
        # Check if this container is explicitly part of an excluded section (e.g. speakers-list)
        parent_section = container.find_parent(attrs={'class': re.compile(r'speaker|attendee|sponsor', re.I)})
        if parent_section and not any(k in parent_section.get('class', '') for k in ['organi', 'team', 'committee']):
            continue

        # Extract name first
        name_el = container.select_one('.name, h2, h3, h4, strong')
        if not name_el:
            continue
        raw_name = name_el.get_text(separator=' ', strip=True)
        norm_name = normalize_text(raw_name)

        if not is_plausible_person_name(norm_name):
            continue

        # Extract role
        role_el = container.select_one('.role, .designation, .title, .position, p.role')
        raw_role = role_el.get_text(separator=' ', strip=True) if role_el else None

        if not raw_role:
            # Check for role prefixes in person heading (e.g. 'Assistant Anna')
            for prefix in ['Assistant ', 'Organizer ', 'Director ', 'Coordinator ', 'Chair ']:
                if norm_name.lower().startswith(prefix.lower()):
                    raw_role = prefix.strip()
                    break

        if not raw_role:
            # Check full page text for explicit organizer/founder attribution
            page_text = soup.get_text()
            m = re.search(rf'(?:organi[sz]ed by|founder of|creator of)[^.]+?{re.escape(norm_name)}[^.]*|\b{re.escape(norm_name)}\b[^.]+?(?:organi[sz]er|founder|creator)', page_text, re.I)
            if m:
                raw_role = 'Organizer / Founder'
            elif container.find('a', href=re.compile(r'^(tel:|mailto:)')):
                raw_role = 'Event Contact'

        norm_role = normalize_text(raw_role)

        if not norm_role or not is_qualifying_organizer_role(norm_role):
            # Without a qualifying organizer role, generic containers (like contact forms) are rejected
            continue

        name_evidence = FieldEvidence(
            raw_value=raw_name,
            normalized_value=norm_name,
            source_url=source_url,
            supporting_snippet=str(container)[:300],
            extraction_status="extracted"
        )

        role_evidence = FieldEvidence(
            raw_value=raw_role,
            normalized_value=norm_role,
            source_url=source_url,
            supporting_snippet=str(role_el)[:200] if role_el else str(container)[:200],
            extraction_status="extracted"
        )

        # Extract emails (multi-value supported)
        emails = extract_all_emails_from_container(container)
        raw_email = ", ".join(emails) if emails else None
        norm_email = ", ".join(e.lower() for e in emails) if emails else None

        email_evidence = None
        if raw_email:
            email_evidence = FieldEvidence(
                raw_value=raw_email,
                normalized_value=norm_email,
                source_url=source_url,
                supporting_snippet=str(container)[:200],
                extraction_status="extracted"
            )

        # Extract phones (multi-value supported)
        phones = extract_all_phones_from_container(container)
        raw_phone = ", ".join(phones) if phones else None
        norm_phone = ", ".join(phones) if phones else None

        phone_evidence = None
        if raw_phone:
            phone_evidence = FieldEvidence(
                raw_value=raw_phone,
                normalized_value=norm_phone,
                source_url=source_url,
                supporting_snippet=str(container)[:200],
                extraction_status="extracted"
            )

        # Extract organization
        org_el = container.select_one('.organization, .company, .org')
        raw_org = org_el.get_text(separator=' ', strip=True) if org_el else None
        supporting_org_snippet = str(org_el)[:200] if org_el else None

        if not raw_org and norm_name:
            # Check for founder / director / organizer of <Organization> in surrounding page text
            org_match = re.search(
                rf'{re.escape(norm_name)}[^.]+?(?:founder|director|organi[sz]er|head|president|ceo|chair)\s+(?:of|at)\s+(?:[a-zA-Z0-9\s-]{{0,30}}?(?:studio|agency|authority|company|office|council|firm|corporation|group|center|centre|authority|department)\s+)?[‘\'"“]?([^‘\'"”\n,—.]+[A-Za-z0-9])[‘\'"”]?',
                page_text,
                re.I
            )
            if not org_match:
                org_match = re.search(
                    rf'(?:organi[sz]ed by|hosted by)\s+{re.escape(norm_name)}[^.]+?(?:of|from|at)\s+[‘\'"“]?([^‘\'"”\n,—.]+[A-Za-z0-9])[‘\'"”]?',
                    page_text,
                    re.I
                )
            if org_match:
                raw_org = org_match.group(1).strip()
                supporting_org_snippet = org_match.group(0)[:200]

        org_evidence = None
        if raw_org:
            norm_org = normalize_text(raw_org)
            if norm_org:
                org_evidence = FieldEvidence(
                    raw_value=raw_org,
                    normalized_value=norm_org,
                    source_url=source_url,
                    supporting_snippet=supporting_org_snippet,
                    extraction_status="extracted"
                )

        contact = EventContact(
            event_name=event_name,
            person_name=name_evidence,
            role_as_written=role_evidence,
            email=email_evidence,
            phone=phone_evidence,
            organisation=org_evidence,
            contact_source_url=source_url,
            retrieval_status="extracted",
            contact_type="person"
        )
        contacts.append(contact)

    return contacts


DESK_ROLE_KEYWORDS = {
    'sales', 'marketing', 'media', 'inquiries', 'enquiries', 'sponsorship',
    'exhibition', 'exhibit', 'registration', 'support', 'helpdesk', 'info',
    'press', 'partnership', 'partnerships', 'customer service', 'secretariat'
}


def extract_department_desks_from_html(
    html_content: str,
    source_url: str,
    event_name: str
) -> List[EventContact]:
    """
    Parse HTML content in memory and extract official department desks and general inquiry channels.
    Preserves field-level evidence and marks contact_type='department_desk'.
    """
    soup = BeautifulSoup(html_content, 'html.parser')
    desks: List[EventContact] = []
    seen_desks = set()

    seen_containers = set()
    for h in soup.find_all(['h2', 'h3', 'h4', 'h5', 'strong', 'p']):
        # If this is a <p> with inner strong or heading elements, skip the <p> so the inner element handles it
        if h.name == 'p' and h.find(['strong', 'b', 'h1', 'h2', 'h3', 'h4', 'h5']):
            continue

        title_text = h.get_text(strip=True)
        if not title_text or len(title_text) > 80:
            continue

        lower_title = title_text.lower()
        if not any(k in lower_title for k in DESK_ROLE_KEYWORDS):
            continue

        # Exclude individual roles (e.g. Exhibition Director, Marketing Manager) which belong to people
        if any(ind in lower_title for ind in ['director', 'manager', 'head of', 'lead', 'chair', 'coordinator', 'officer', 'executive', 'assistant', 'founder', 'curator', 'specialist']):
            continue

        container = h.find_parent(['div', 'section', 'li', 'article', 'aside'])
        if not container or container in seen_containers:
            continue

        # If the container is explicitly marked as a person/team card, skip desk extraction
        container_classes = container.get('class') or []
        if any(c in container_classes for c in ['organizer', 'team-member', 'committee-member', 'team__item']):
            continue

        # If container contains a named individual, skip desk extraction
        pname_el = container.select_one('.name, h2, h3, h4')
        if pname_el and pname_el != h and is_plausible_person_name(pname_el.get_text(strip=True)):
            continue

        seen_containers.add(container)

        # Find emails and phones (multi-value supported)
        emails = extract_all_emails_from_container(container)
        phones = extract_all_phones_from_container(container)

        if not emails and not phones:
            continue

        raw_email = ", ".join(emails) if emails else None
        norm_email = ", ".join(e.lower() for e in emails) if emails else None
        raw_phone = ", ".join(phones) if phones else None
        norm_phone = ", ".join(phones) if phones else None

        norm_title = normalize_text(title_text)
        if norm_title.lower().startswith("for "):
            norm_desk_name = norm_title[4:].strip()
        else:
            norm_desk_name = norm_title

        dedup_key = (norm_desk_name.lower(), (raw_email or "").lower(), (raw_phone or ""))
        if dedup_key in seen_desks:
            continue
        # Skip redundant desk if its name is just the email and a titled desk already has this email
        if raw_email and "@" in norm_desk_name and any(d.email and raw_email.lower() in (d.email.normalized_value or "") for d in desks):
            continue
        seen_desks.add(dedup_key)

        snippet = str(container)[:300]

        desk_contact = EventContact(
            event_name=event_name,
            contact_type="department_desk",
            person_name=FieldEvidence(
                raw_value=title_text,
                normalized_value=norm_desk_name,
                source_url=source_url,
                supporting_snippet=snippet,
                extraction_status="extracted"
            ),
            role_as_written=FieldEvidence(
                raw_value=norm_desk_name,
                normalized_value=f"{norm_desk_name} Desk",
                source_url=source_url,
                supporting_snippet=snippet,
                extraction_status="extracted"
            ),
            email=FieldEvidence(
                raw_value=raw_email,
                normalized_value=raw_email.lower(),
                source_url=source_url,
                supporting_snippet=snippet,
                extraction_status="extracted"
            ) if raw_email else None,
            phone=FieldEvidence(
                raw_value=raw_phone,
                normalized_value=re.sub(r'\s+', ' ', raw_phone).strip(),
                source_url=source_url,
                supporting_snippet=snippet,
                extraction_status="extracted"
            ) if raw_phone else None,
            contact_source_url=source_url,
            retrieval_status="extracted",
            verification_status="institutional_desk",
            notes="Official departmental inquiry desk published on event contact page."
        )
        desks.append(desk_contact)

    return desks


def extract_hotline_from_detail_html(html_content: str, detail_url: str) -> Optional[Dict[str, Any]]:
    """
    Extract host venue or event hotline and address from the Invest in Dubai event detail page.
    Deterministic parser looking for Sitecore JSS structures or official telephone entries.
    """
    if not html_content:
        return None

    # 1. Look for venue block with phone:
    # "title":{"jss":{"value":"Dubai Design District (d3)"}},"address":{"jss":{"value":"Dubai Design District - Dubai"}},"phone":{"jss":{"value":"+971 4 433 3000"}}
    v_match = re.search(
        r'"title"\s*:\s*\{\s*"jss"\s*:\s*\{\s*"value"\s*:\s*"([^"]+)"\}\},\s*"address"\s*:\s*\{\s*"jss"\s*:\s*\{\s*"value"\s*:\s*"([^"]*)"\}\},\s*"phone"\s*:\s*\{\s*"jss"\s*:\s*\{\s*"value"\s*:\s*"([^"]*)"\}\}',
        html_content
    )
    if v_match:
        venue_title = v_match.group(1).strip()
        venue_addr = v_match.group(2).strip()
        phone_val = v_match.group(3).strip()
        if phone_val and len(re.sub(r'\D', '', phone_val)) >= 7:
            snippet = f'Venue: "{venue_title}" | Address: "{venue_addr}" | Phone: "{phone_val}"'
            return {
                "venue_name": venue_title,
                "phone": phone_val,
                "snippet": snippet,
                "source_url": detail_url
            }

    # 2. General Phone field in JSS
    p_match = re.search(
        r'"[Pp]hone"\s*:\s*\{\s*"(?:jss|value)"\s*:\s*(?:\{\s*"value"\s*:\s*)?"([^"]+)"',
        html_content
    )
    if p_match:
        phone_val = p_match.group(1).strip()
        if len(re.sub(r'\D', '', phone_val)) >= 7:
            snippet = f'Detail page phone: "{phone_val}"'
            return {
                "venue_name": None,
                "phone": phone_val,
                "snippet": snippet,
                "source_url": detail_url
            }

    return None

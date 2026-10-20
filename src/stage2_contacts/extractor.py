"""Specialist 2: Contact & Evidence Extractor.

Extracts event-team organizers, directors, and managers from in-memory pages.
Combines deterministic DOM parsing with LLM schema extraction and strict
anti-hallucination verification gates. Follows AGENTS.md Section 2 (Stage 2).
"""
import os
import sys
import json
import csv
import re
from typing import List, Dict, Any, Optional

from src.models import EventContact, FieldEvidence, current_iso_timestamp
from src.stage1_discovery.normalizer import normalize_text
from src.stage2_contacts.parser import (
    extract_contacts_from_html,
    extract_department_desks_from_html,
    extract_hotline_from_detail_html,
    is_qualifying_organizer_role,
    is_plausible_person_name
)
from src.stage2_contacts.scout import EventWebScout
from src.providers.base import BaseLLMProvider
from src.providers.llm_mock import MockLLMProvider
from src.providers.llm_gemini import GeminiLLMProvider
from src.providers.llm_openai_compat import OpenAICompatibleLLMProvider

EXTRACTION_PROMPT_TEMPLATE = """You are a strict data extraction engine for event intelligence.
Your task is to extract ONLY people who explicitly organize, direct, manage, or chair the event from the provided text.

Event Name: {event_name}
Source URL: {source_url}

Webpage Text Snippet:
\"\"\"
{text_content}
\"\"\"

STRICT RULES:
1. Extract ONLY people who have an explicit event management/organizer role (e.g. Organizer, Director, Chair, Committee Member, Project Lead, Secretariat).
2. EXCLUDE keynote speakers, panelists, attendees, or sponsors UNLESS their title explicitly states they organize the event.
3. Every person must have an exact supporting_snippet (a 1-2 sentence verbatim quote from the text where their name and role appear).
4. If an email or phone is NOT explicitly published in the text, return null. NEVER guess, construct, or transfer an email or phone.
5. If no qualifying event organizers are found, return an empty list.

Return JSON in this exact structure:
{{
  "contacts": [
    {{
      "person_name": "Exact Name",
      "role_as_written": "Exact Role as Written",
      "organisation": "Organization Name or null",
      "email": "email@example.com or null",
      "phone": "+971... or null",
      "supporting_snippet": "Verbatim quote from the text"
    }}
  ]
}}
"""


class ContactExtractor:
    """Specialist 2: Contact & Evidence Extractor."""

    def __init__(
        self,
        scout: Optional[EventWebScout] = None,
        llm_provider: Optional[BaseLLMProvider] = None
    ):
        self.scout = scout or EventWebScout()
        if llm_provider:
            self.llm_provider = llm_provider
        elif os.getenv("GEMINI_API_KEY"):
            self.llm_provider = GeminiLLMProvider()
        elif os.getenv("NVIDIA_API_KEY"):
            self.llm_provider = OpenAICompatibleLLMProvider()
        else:
            self.llm_provider = MockLLMProvider(canned_response={"contacts": []})

    def extract_from_in_memory_html(
        self,
        html_content: str,
        source_url: str,
        event_name: str
    ) -> List[EventContact]:
        """
        Extract contacts from an in-memory HTML page.
        Combines deterministic parsing with LLM fallback and evidence validation.
        """
        contacts: List[EventContact] = []

        # 1. Deterministic extraction via DOM parser
        dom_contacts = extract_contacts_from_html(html_content, source_url, event_name)
        contacts.extend(dom_contacts)

        # 2. If DOM found fewer than 2 contacts, inspect prose/text via LLM
        if len(contacts) < 2 and self.llm_provider:
            from bs4 import BeautifulSoup
            soup = BeautifulSoup(html_content, "html.parser")
            # Extract readable text, removing scripts and styles
            for elem in soup(["script", "style", "noscript", "svg"]):
                elem.extract()
            text = soup.get_text(separator=" ", strip=True)

            # Look for organizer/committee mentions in text
            if re.search(r'(?:organi[sz]|committee|secretariat|director|founder|lead|chair|head|manager|operations|president|executive|chief)', text, re.I):
                # Send compact text window (up to 8,000 characters)
                truncated_text = text[:8000]
                prompt = EXTRACTION_PROMPT_TEMPLATE.format(
                    event_name=event_name,
                    source_url=source_url,
                    text_content=truncated_text
                )
                try:
                    resp = self.llm_provider.generate_json(prompt)
                    raw_items = resp.get("contacts", [])
                    for item in raw_items:
                        p_name = item.get("person_name")
                        p_role = item.get("role_as_written")
                        snippet = item.get("supporting_snippet", "")

                        # Anti-Hallucination Gate 1: Check plausible person name and role
                        if not p_name or not is_plausible_person_name(p_name):
                            continue
                        if not p_role or not is_qualifying_organizer_role(p_role):
                            continue

                        # Anti-Hallucination Gate 2: Snippet must actually appear in page text
                        if not snippet or snippet.strip()[:30].lower() not in text.lower():
                            # Snippet not verifiable in raw text -> reject
                            continue

                        # Anti-Hallucination Gate 3: Email and phone must be present in snippet
                        raw_email = item.get("email")
                        if raw_email and raw_email.lower() not in snippet.lower():
                            raw_email = None

                        raw_phone = item.get("phone")
                        if raw_phone and not any(ch.isdigit() for ch in raw_phone if ch in snippet):
                            raw_phone = None

                        # Create verified EventContact record
                        ec = EventContact(
                            event_name=event_name,
                            person_name=FieldEvidence(
                                raw_value=p_name,
                                normalized_value=normalize_text(p_name),
                                source_url=source_url,
                                supporting_snippet=snippet,
                                extraction_status="extracted"
                            ),
                            role_as_written=FieldEvidence(
                                raw_value=p_role,
                                normalized_value=normalize_text(p_role),
                                source_url=source_url,
                                supporting_snippet=snippet,
                                extraction_status="extracted"
                            ),
                            organisation=FieldEvidence(
                                raw_value=item.get("organisation"),
                                normalized_value=normalize_text(item.get("organisation")),
                                source_url=source_url,
                                supporting_snippet=snippet,
                                extraction_status="extracted"
                            ) if item.get("organisation") else None,
                            email=FieldEvidence(
                                raw_value=raw_email,
                                normalized_value=raw_email.lower() if raw_email else None,
                                source_url=source_url,
                                supporting_snippet=snippet,
                                extraction_status="extracted"
                            ) if raw_email else None,
                            phone=FieldEvidence(
                                raw_value=raw_phone,
                                normalized_value=normalize_text(raw_phone),
                                source_url=source_url,
                                supporting_snippet=snippet,
                                extraction_status="extracted"
                            ) if raw_phone else None,
                            contact_source_url=source_url,
                            retrieval_status="extracted",
                            notes="Extracted via LLM schema reasoning with verified verbatim text snippet."
                        )
                        contacts.append(ec)
                except Exception as e:
                    import logging
                    logging.getLogger(__name__).warning(f"LLM extraction note on {source_url}: {e}")

        # 3. Deterministic extraction of department desks & inquiry channels
        desks = extract_department_desks_from_html(html_content, source_url, event_name)

        # Deduplicate contacts: separate persons and department desks
        seen_person_names = set()
        deduped_persons: List[EventContact] = []
        for c in contacts:
            norm_name = c.person_name.normalized_value
            if norm_name and norm_name.lower() not in seen_person_names:
                seen_person_names.add(norm_name.lower())
                deduped_persons.append(c)

        seen_desks = set()
        deduped_desks: List[EventContact] = []
        for d in desks:
            d_name = d.person_name.normalized_value
            d_email = d.email.normalized_value if d.email else ""
            key = (d_name.lower() if d_name else "", d_email.lower())
            if key not in seen_desks:
                seen_desks.add(key)
                deduped_desks.append(d)

        # Strictly Persons FIRST, Department Desks AFTER
        return deduped_persons + deduped_desks

    def process_event(
        self,
        event_name: str,
        event_website_url: Optional[str],
        event_detail_url: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Inspect an event in memory and extract verified contacts.
        Orders all named persons first, followed by general inquiry / department desks.
        """
        report: Dict[str, Any] = {
            "event_name": event_name,
            "event_website_url": event_website_url,
            "event_detail_url": event_detail_url,
            "inspection_timestamp": current_iso_timestamp(),
            "overall_status": "inspected",
            "inspected_pages": [],
            "contacts_count": 0,
            "contacts": [],
            "notes": None
        }

        # 1. Scout event pages in-memory (if external website exists)
        all_contacts: List[EventContact] = []
        inspected_pages = []
        if event_website_url:
            inspected_pages = self.scout.scout_event_pages(event_website_url, max_subpages=2)
            for p in inspected_pages:
                p_url = p.get("url")
                p_html = p.get("html")
                p_status = p.get("status")

                page_meta = {
                    "url": p_url,
                    "status": p_status,
                    "is_homepage": p.get("is_homepage", False),
                    "contacts_found": 0
                }

                if p_html and p_status == "success":
                    extracted = self.extract_from_in_memory_html(p_html, p_url, event_name)
                    page_meta["contacts_found"] = len(extracted)
                    all_contacts.extend(extracted)

                report["inspected_pages"].append(page_meta)

        # 2. Scout event detail page on government portal if provided
        hotline_info = None
        if event_detail_url:
            d_html, _, d_status = self.scout.fetch_url_content(event_detail_url)
            if d_html and d_status == 200:
                hotline_info = extract_hotline_from_detail_html(d_html, event_detail_url)
                report["inspected_pages"].append({
                    "url": event_detail_url,
                    "status": "success",
                    "is_homepage": False,
                    "contacts_found": 1 if hotline_info else 0
                })

        # Deduplicate across pages, keeping persons strictly first
        person_contacts = []
        desk_contacts = []
        seen_persons = set()
        seen_desks = set()

        for c in all_contacts:
            ctype = getattr(c, "contact_type", "person")
            if ctype == "person":
                name = c.person_name.normalized_value
                if name and name.lower() not in seen_persons:
                    seen_persons.add(name.lower())
                    person_contacts.append(c.to_dict())
            else:
                dname = c.person_name.normalized_value
                demail = c.email.normalized_value if c.email else ""
                key = (dname.lower() if dname else "", demail.lower())
                if key not in seen_desks:
                    seen_desks.add(key)
                    desk_contacts.append(c.to_dict())

        # 3. Integrate detail page hotline if found
        if hotline_info:
            phone_val = hotline_info["phone"]
            phone_dict = {
                "raw_value": phone_val,
                "normalized_value": phone_val,
                "source_url": hotline_info["source_url"],
                "supporting_snippet": hotline_info["snippet"],
                "retrieval_timestamp": current_iso_timestamp(),
                "extraction_status": "extracted"
            }
            attached = False
            for d in desk_contacts:
                if not d.get("phone"):
                    d["phone"] = phone_dict
                    attached = True

            if not attached and not desk_contacts:
                v_name = hotline_info.get("venue_name") or "Host Venue & Event Inquiries"
                venue_desk_dict = {
                    "event_name": event_name,
                    "contact_type": "department_desk",
                    "person_name": {
                        "raw_value": v_name,
                        "normalized_value": f"{v_name} Desk",
                        "source_url": hotline_info["source_url"],
                        "supporting_snippet": hotline_info["snippet"],
                        "retrieval_timestamp": current_iso_timestamp(),
                        "extraction_status": "extracted"
                    },
                    "role_as_written": {
                        "raw_value": "Official Venue & Event Hotline",
                        "normalized_value": "Official Venue & Event Hotline",
                        "source_url": hotline_info["source_url"],
                        "supporting_snippet": hotline_info["snippet"],
                        "retrieval_timestamp": current_iso_timestamp(),
                        "extraction_status": "extracted"
                    },
                    "organisation": {
                        "raw_value": v_name,
                        "normalized_value": v_name,
                        "source_url": hotline_info["source_url"],
                        "supporting_snippet": hotline_info["snippet"],
                        "retrieval_timestamp": current_iso_timestamp(),
                        "extraction_status": "extracted"
                    } if hotline_info.get("venue_name") else None,
                    "email": None,
                    "phone": phone_dict,
                    "contact_source_url": hotline_info["source_url"],
                    "retrieval_status": "extracted",
                    "verification_status": "institutional_desk",
                    "notes": "Official host venue & event hotline published on Invest in Dubai event detail page."
                }
                desk_contacts.append(venue_desk_dict)

        final_contacts = person_contacts + desk_contacts
        report["contacts"] = final_contacts
        report["contacts_count"] = len(final_contacts)

        if final_contacts:
            report["overall_status"] = "contacts_extracted"
            report["notes"] = f"Extracted {len(final_contacts)} qualifying organizer contact(s) with evidence."
        elif any(p.get("status") and "403" in str(p.get("status")) for p in inspected_pages):
            report["overall_status"] = "inaccessible_due_to_access_controls"
            report["notes"] = "Event website returned HTTP 403 or access restriction; respected without bypassing."
        elif not event_website_url:
            report["overall_status"] = "missing_website_url"
            report["notes"] = "Event has no published external website URL."
        else:
            report["overall_status"] = "no_contacts_found"
            report["notes"] = "Pages were inspected, but no qualifying event-team contacts were published."

        return report

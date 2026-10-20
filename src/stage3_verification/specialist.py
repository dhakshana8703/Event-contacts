"""Specialist 3: Independent LinkedIn Discovery and Identity Verification Specialist.

Accepts contacts.json as independent input and performs live search & verification
without rerunning Stage 1 or Stage 2. Follows AGENTS.md Section 2 (Stage 3).
"""
import os
import re
import sys
import json
import csv
from typing import List, Dict, Any, Optional, Tuple

from src.models import FieldEvidence, current_iso_timestamp
from src.providers.base import BaseSearchProvider, SearchResult
from src.providers.search_mock import MockSearchProvider
from src.providers.search_serper import SerperSearchProvider
from src.providers.search_tavily import TavilySearchProvider

HONORIFIC_PREFIXES = [
    r'^h\.?e\.?\s+',
    r'^his\s+excellency\s+',
    r'^her\s+excellency\s+',
    r'^dr\.?\s+',
    r'^eng\.?\s+',
    r'^sheikh\s+',
    r'^sheikha\s+',
    r'^prof\.?\s+',
    r'^mr\.?\s+',
    r'^ms\.?\s+',
    r'^mrs\.?\s+',
]


def clean_person_name(name: str) -> str:
    """Strip common honorifics and extraneous titles from person name."""
    cleaned = name.strip()
    for pattern in HONORIFIC_PREFIXES:
        cleaned = re.sub(pattern, '', cleaned, flags=re.IGNORECASE).strip()
    return cleaned


def generate_search_queries(
    person_name: str,
    organization: Optional[str] = None,
    event_name: Optional[str] = None,
    role: Optional[str] = None
) -> List[str]:
    """
    Generate prioritized Google search queries targeting LinkedIn personal profiles.
    Follows AGENTS.md search priority:
    1. Name + Organization
    2. Name + Role / Event
    3. Name + Dubai / Location
    """
    clean_name = clean_person_name(person_name)
    queries: List[str] = []

    # Priority 1: Name + Organization (if org known and valid)
    if organization and len(organization.strip()) > 2:
        org_clean = organization.strip()
        queries.append(f'site:linkedin.com/in "{clean_name}" "{org_clean}"')

    # Priority 2: Name + Event Name
    if event_name and len(event_name.strip()) > 2:
        event_clean = event_name.split("-")[0].strip()  # Remove subheadings
        queries.append(f'site:linkedin.com/in "{clean_name}" "{event_clean}"')

    # Priority 3: Name + Role keywords
    if role and len(role.strip()) > 3:
        queries.append(f'site:linkedin.com/in "{clean_name}" "{role.strip()}"')

    # Priority 4: Name + Dubai
    queries.append(f'site:linkedin.com/in "{clean_name}" "Dubai"')

    # Deduplicate while preserving priority order
    seen = set()
    deduped = []
    for q in queries:
        if q not in seen:
            seen.add(q)
            deduped.append(q)

    return deduped


def evaluate_verification(
    person_name: str,
    organization: Optional[str],
    role: Optional[str],
    event_name: Optional[str],
    candidate_url: Optional[str],
    snippet: Optional[str],
    query_used: str
) -> Dict[str, Any]:
    """
    Evaluate candidate search evidence against contact identity per AGENTS.md rules.
    Rule: A name match alone is never sufficient.
    """
    if not candidate_url or not snippet:
        return {
            "status": "not_found",
            "justification": f"No credible personal LinkedIn profile found via query: {query_used}."
        }

    # Only accept personal profiles, not company directories or posts
    if "linkedin.com/in/" not in candidate_url:
        return {
            "status": "not_found",
            "justification": f"Candidate URL '{candidate_url}' is not a personal profile (linkedin.com/in/)."
        }

    clean_name = clean_person_name(person_name).lower()
    snippet_lower = snippet.lower()

    # Check person name tokens
    name_tokens = [tok for tok in clean_name.split() if len(tok) > 2]
    # At least first and last token must match
    if len(name_tokens) >= 2:
        name_match = (name_tokens[0] in snippet_lower) and (name_tokens[-1] in snippet_lower)
    elif len(name_tokens) == 1:
        name_match = name_tokens[0] in snippet_lower
    else:
        name_match = False

    if not name_match:
        return {
            "status": "not_found",
            "justification": f"Search snippet does not match candidate name '{person_name}'."
        }

    # Cross-verify with Organization, Event, or Role
    org_tokens = [t.lower() for t in (organization or "").split() if len(t) > 3]
    org_matched = any(t in snippet_lower for t in org_tokens) if org_tokens else False

    event_tokens = [t.lower() for t in (event_name or "").split() if len(t) > 3]
    event_matched = any(t in snippet_lower for t in event_tokens) if event_tokens else False

    role_tokens = [t.lower() for t in (role or "").split() if len(t) > 4]
    role_matched = any(t in snippet_lower for t in role_tokens) if role_tokens else False

    if org_matched or event_matched:
        justification = (
            f"Verified match: Name '{person_name}' and affiliation "
            f"('{organization if org_matched else event_name}') independently confirmed in search evidence."
        )
        return {
            "status": "verified",
            "justification": justification
        }
    elif role_matched:
        justification = (
            f"Candidate found: Name '{person_name}' and role '{role}' match, "
            f"but explicit organizational affiliation to '{organization or event_name}' requires manual confirmation."
        )
        return {
            "status": "needs_review",
            "justification": justification
        }
    else:
        # Strict AGENTS.md rule: A name match alone is never sufficient
        return {
            "status": "needs_review",
            "justification": (
                f"Plausible profile found for '{person_name}', but search snippet lacks explicit "
                f"supporting affiliation to organization '{organization}' or event '{event_name}'. Left unverified."
            )
        }


class LinkedInSpecialist:
    """Independent Specialist for LinkedIn Discovery and Verification."""

    def __init__(self, search_provider: Optional[BaseSearchProvider] = None):
        if search_provider:
            self.search_provider = search_provider
        elif os.getenv("SERPER_API_KEY"):
            self.search_provider = SerperSearchProvider()
        elif os.getenv("TAVILY_API_KEY"):
            self.search_provider = TavilySearchProvider()
        else:
            # Default to mock provider if no API keys present
            self.search_provider = MockSearchProvider()

    def process_single_contact(self, contact: Dict[str, Any]) -> Dict[str, Any]:
        """
        Discover and verify LinkedIn profile for a single contact record.
        Preserves all existing Stage 1 and Stage 2 fields untouched.
        """
        # Institutional department desks do not have individual personal LinkedIn profiles
        if contact.get("contact_type") == "department_desk":
            contact["verification_status"] = "institutional_desk"
            contact["notes"] = "Official department / inquiry desk published on event contact page."
            return contact

        person_name = contact.get("person_name", {}).get("normalized_value") or contact.get("person_name", {}).get("raw_value")
        if not person_name:
            contact["verification_status"] = "not_found"
            contact["notes"] = "Missing person name; search skipped."
            return contact

        org = contact.get("organisation", {}).get("normalized_value") if contact.get("organisation") else None
        role = contact.get("role_as_written", {}).get("normalized_value") if contact.get("role_as_written") else None
        event_name = contact.get("event_name")

        queries = generate_search_queries(
            person_name=person_name,
            organization=org,
            event_name=event_name,
            role=role
        )

        best_result: Optional[SearchResult] = None
        best_eval: Dict[str, Any] = {"status": "not_found", "justification": "No search performed."}
        query_executed: str = ""

        for q in queries:
            try:
                results = self.search_provider.search(q, num_results=3)
            except Exception as e:
                contact["verification_status"] = "search_unavailable"
                contact["notes"] = f"Search provider error: {e}"
                return contact

            # Find first personal profile
            for res in results:
                if "linkedin.com/in/" in res.url:
                    ev = evaluate_verification(
                        person_name=person_name,
                        organization=org,
                        role=role,
                        event_name=event_name,
                        candidate_url=res.url,
                        snippet=res.snippet,
                        query_used=q
                    )
                    if ev["status"] == "verified":
                        best_result = res
                        best_eval = ev
                        query_executed = q
                        break
                    elif ev["status"] == "needs_review" and best_eval["status"] != "verified":
                        best_result = res
                        best_eval = ev
                        query_executed = q

            if best_eval["status"] == "verified":
                break

        # Record findings
        if best_result and best_eval["status"] in ("verified", "needs_review"):
            contact["linkedin_url"] = {
                "raw_value": best_result.url,
                "normalized_value": best_result.url,
                "source_url": "https://www.linkedin.com",
                "supporting_snippet": f"Query: {query_executed} | Snippet: {best_result.snippet}",
                "retrieval_timestamp": current_iso_timestamp(),
                "extraction_status": best_eval["status"]
            }
        else:
            contact["linkedin_url"] = None

        contact["verification_status"] = best_eval["status"]
        contact["notes"] = best_eval["justification"]
        return contact

    def process_contacts_file(
        self,
        input_path: str,
        output_json_path: Optional[str] = None,
        output_csv_path: Optional[str] = None,
        limit: Optional[int] = None
    ) -> List[Dict[str, Any]]:
        """
        Run LinkedIn specialist over an entire contacts.json file.
        Updates both JSON and CSV exports.
        """
        if not os.path.exists(input_path):
            raise FileNotFoundError(f"Input file not found: {input_path}")

        with open(input_path, "r", encoding="utf-8") as f:
            contacts = json.load(f)

        output_json = output_json_path or input_path
        output_csv = output_csv_path or input_path.replace(".json", ".csv")

        processed: List[Dict[str, Any]] = []
        target_records = contacts[:limit] if limit else contacts

        print(f"[Specialist 3] Running LinkedIn Discovery & Verification on {len(target_records)} contact(s)...")

        for idx, contact in enumerate(target_records, start=1):
            name = contact.get("person_name", {}).get("normalized_value", "Unknown")
            print(f"  [{idx}/{len(target_records)}] Inspecting: {name}...")
            updated = self.process_single_contact(contact)
            processed.append(updated)
            print(f"    -> Status: {updated.get('verification_status')} | LinkedIn: {updated.get('linkedin_url', {}).get('normalized_value') if updated.get('linkedin_url') else 'null'}")

        # If limit was applied, keep remaining records untouched
        if limit and len(contacts) > limit:
            processed.extend(contacts[limit:])

        # Save JSON
        with open(output_json, "w", encoding="utf-8") as f:
            json.dump(processed, f, indent=2, ensure_ascii=False)

        # Save CSV
        fieldnames = [
            "Contact ID", "Event Name", "Organizer ID", "Contact Name",
            "Job Title (As Published)", "Responsibility Area", "Work Email",
            "Phone Number", "LinkedIn URL", "Source URL", "Verification Status", "Notes"
        ]
        with open(output_csv, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(f, fieldnames=fieldnames)
            writer.writeheader()
            for c in processed:
                writer.writerow({
                    "Contact ID": c.get("contact_id", ""),
                    "Event Name": c.get("event_name", ""),
                    "Organizer ID": c.get("organizer_id", ""),
                    "Contact Name": c.get("person_name", {}).get("normalized_value", "") if c.get("person_name") else "",
                    "Job Title (As Published)": c.get("role_as_written", {}).get("normalized_value", "") if c.get("role_as_written") else "",
                    "Responsibility Area": c.get("responsibility_area", "General Event Management"),
                    "Work Email": c.get("email", {}).get("normalized_value", "") if c.get("email") else "",
                    "Phone Number": c.get("phone", {}).get("normalized_value", "") if c.get("phone") else "",
                    "LinkedIn URL": c.get("linkedin_url", {}).get("normalized_value", "") if c.get("linkedin_url") else "",
                    "Source URL": c.get("contact_source_url", ""),
                    "Verification Status": c.get("verification_status", "needs_review"),
                    "Notes": c.get("notes", "") or ""
                })

        print(f"[Specialist 3 Complete] Updated: {output_json} & {output_csv}")
        return processed


if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser(description="Run Specialist 3: LinkedIn Discovery & Verification")
    parser.add_argument("--input", default="data/output/contacts.json", help="Path to input contacts.json")
    parser.add_argument("--limit", type=int, default=None, help="Limit number of contacts to process")
    args = parser.parse_args()

    specialist = LinkedInSpecialist()
    specialist.process_contacts_file(args.input, limit=args.limit)

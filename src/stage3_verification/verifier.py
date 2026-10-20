"""Stage 3: LinkedIn Profile Discovery and Verification Engine.

Follows AGENTS.md Section 2 (Stage 3):
- Prioritizes Name + Organization, then Name + Role/Event.
- Rejects name matches without independent affiliation evidence.
- Never fabricates LinkedIn URLs.
- Assigns strict status: verified, needs_review, not_found, search_unavailable.
"""
import os
import sys
import json
import csv
from typing import List, Dict, Any, Optional

# Ensure project root is in sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "..")))

from src.models import EventContact, FieldEvidence, current_iso_timestamp

OUTPUT_DIR = os.path.join(os.path.dirname(__file__), "..", "..", "data", "output")
CONTACTS_JSON_PATH = os.path.join(OUTPUT_DIR, "contacts.json")
CONTACTS_CSV_PATH = os.path.join(OUTPUT_DIR, "contacts.csv")


def evaluate_candidate_match(
    person_name: str,
    organization: Optional[str],
    role: Optional[str],
    candidate_url: Optional[str],
    snippet: Optional[str]
) -> Dict[str, Any]:
    """
    Evaluate candidate search evidence against contact identity per AGENTS.md rules.

    Statuses:
        verified: Name matches AND independent supporting evidence proves relevant affiliation.
        needs_review: Plausible candidate exists, but evidence is insufficient or ambiguous.
        not_found: No credible candidate found after search.
        search_unavailable: Search could not be performed.
    """
    if not candidate_url or not snippet:
        return {
            "status": "not_found",
            "justification": f"No public personal LinkedIn profile indexed or found for '{person_name}' associated with '{organization or role}'."
        }

    snippet_lower = snippet.lower()
    name_tokens = [t.lower() for t in person_name.split() if len(t) > 2]
    name_matched = all(tok in snippet_lower for tok in name_tokens)

    if not name_matched:
        return {
            "status": "not_found",
            "justification": f"Candidate snippet does not match full name '{person_name}'."
        }

    # Name matches. Now check independent supporting evidence (Organization or Role)
    org_matched = bool(organization and any(w.lower() in snippet_lower for w in organization.split() if len(w) > 3))
    role_matched = bool(role and any(w.lower() in snippet_lower for w in role.split() if len(w) > 4))

    if org_matched and role_matched:
        return {
            "status": "verified",
            "justification": f"Full name '{person_name}', organization '{organization}', and role '{role}' confirmed in public evidence."
        }
    elif org_matched or role_matched:
        return {
            "status": "verified",
            "justification": f"Full name '{person_name}' and matching affiliation ('{organization if org_matched else role}') confirmed."
        }
    else:
        # A name match alone is never sufficient per AGENTS.md
        return {
            "status": "needs_review",
            "justification": f"Name matched '{person_name}', but snippet lacks explicit supporting affiliation to '{organization}' or '{role}'. Left unverified."
        }


def run_stage3_verification(
    contacts_json_path: str = CONTACTS_JSON_PATH,
    contacts_csv_path: str = CONTACTS_CSV_PATH,
    limit: Optional[int] = None
) -> List[Dict[str, Any]]:
    """
    Perform Stage 3 LinkedIn discovery and verification dynamically using LinkedInSpecialist.
    Eliminates all hardcoded evidence dictionaries.
    """
    from src.stage3_verification.specialist import LinkedInSpecialist
    specialist = LinkedInSpecialist()
    return specialist.process_contacts_file(
        input_path=contacts_json_path,
        output_json_path=contacts_json_path,
        output_csv_path=contacts_csv_path,
        limit=limit
    )


if __name__ == "__main__":
    run_stage3_verification()

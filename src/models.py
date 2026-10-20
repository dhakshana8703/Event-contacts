"""Event Contacts POC - Core Data Models and Evidence Structures."""
from dataclasses import dataclass, field, asdict
from datetime import datetime, timezone
from typing import Optional, Any, Dict


def current_iso_timestamp() -> str:
    """Generate current UTC timestamp in ISO 8601 format."""
    return datetime.now(timezone.utc).isoformat()


@dataclass
class FieldEvidence:
    """Audit trail for an individual extracted field."""
    raw_value: Optional[str]
    normalized_value: Optional[str]
    source_url: str
    supporting_snippet: Optional[str] = None
    retrieval_timestamp: str = field(default_factory=current_iso_timestamp)
    extraction_status: str = "extracted"  # extracted, normalized, suspicious, not_found, null


@dataclass
class DiscoveredEvent:
    """Stage 1 Discovered Event record preserving URL tiers and evidence trail."""
    event_name: FieldEvidence
    listing_page_url: str
    event_page_url: Optional[str] = None
    event_website_url: Optional[FieldEvidence] = None
    category: Optional[FieldEvidence] = None
    dates_text: Optional[FieldEvidence] = None
    venue: Optional[FieldEvidence] = None
    phone: Optional[FieldEvidence] = None
    retrieval_status: str = "discovered"  # discovered, incomplete, failed
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert record and nested FieldEvidence into a serializable dict."""
        return asdict(self)


@dataclass
class OrganizerRecord:
    """Stage 2 Organizer record preserving provenance and organization type."""
    organizer_id: str
    organization_name: str
    organization_type: str  # Organizing Authority, Event Management Company, Venue Partner, Sponsor
    official_website: Optional[str] = None
    public_email: Optional[str] = None
    public_phone: Optional[str] = None
    source_urls: list = field(default_factory=list)
    supporting_evidence: Optional[str] = None
    verification_status: str = "verified"  # verified, needs_review, unverified
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert record into a serializable dict."""
        return asdict(self)


@dataclass
class EnrichedEvent:
    """Stage 2 Enriched Event combining Stage 1 fields with sales timing and organizer link."""
    event_id: str
    event_name: str
    listing_page_url: str
    event_page_url: Optional[str]
    event_website_url: Optional[str]
    category: Optional[str]
    dates_text: Optional[str]
    start_date: Optional[str]
    days_until_event: Optional[int]
    sales_priority: str  # Past, Urgent, Near-term, Upcoming, Long-term, Unknown
    primary_organizer_id: Optional[str]
    organizer_name: Optional[str]
    venue: Optional[str]
    retrieval_status: str
    verification_status: str = "verified"
    notes: Optional[str] = None

    def to_dict(self) -> Dict[str, Any]:
        """Convert record into a serializable dict."""
        return asdict(self)


@dataclass
class EventContact:
    """Stage 2 Event-team Contact record preserving field-level audit trail."""
    event_name: str
    person_name: FieldEvidence
    role_as_written: Optional[FieldEvidence] = None
    email: Optional[FieldEvidence] = None
    phone: Optional[FieldEvidence] = None
    organisation: Optional[FieldEvidence] = None
    contact_source_url: str = ""
    retrieval_status: str = "extracted"  # extracted, incomplete, inaccessible, not_found
    linkedin_url: Optional[FieldEvidence] = None
    verification_status: str = "needs_review"  # verified, needs_review, not_found, search_unavailable, unindexed_publicly
    notes: Optional[str] = None
    contact_id: Optional[str] = None
    organizer_id: Optional[str] = None
    responsibility_area: Optional[str] = None
    contact_type: str = "person"  # person, department_desk

    def to_dict(self) -> Dict[str, Any]:
        """Convert record and nested FieldEvidence into a serializable dict."""
        return asdict(self)


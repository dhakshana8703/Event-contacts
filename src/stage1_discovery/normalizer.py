"""URL and text normalization and validation utilities."""
import re
from urllib.parse import urlparse, urljoin
from typing import Tuple, Optional


def normalize_text(text: Optional[str]) -> Optional[str]:
    """
    Normalize text by stripping whitespace and zero-width characters (e.g., \\u200b).
    Preserves meaningful characters without rewriting titles.
    """
    if not text:
        return None
    # Strip zero-width space and surrounding whitespace
    cleaned = re.sub(r'[\u200b\u200c\u200d\ufeff]', '', text).strip()
    return cleaned if cleaned else None


def normalize_and_validate_url(
    raw_url: Optional[str],
    base_url: Optional[str] = None
) -> Tuple[Optional[str], str, Optional[str]]:
    """
    Normalize and validate a URL while keeping the raw string.

    Returns:
        (normalized_url, status, reason)
        where status is one of:
          - 'verified': clean, valid http/https URL with domain
          - 'normalized': valid after whitespace/prefix correction
          - 'suspicious': invalid structure, javascript:, mailto:, internal portal auth, etc.
          - 'null': raw_url was absent
    """
    if not raw_url or not raw_url.strip():
        return None, "null", "URL is missing or empty"

    cleaned = raw_url.strip()

    # Reject non-web schemes immediately as suspicious
    if cleaned.lower().startswith(('javascript:', 'mailto:', 'tel:', '#')):
        return None, "suspicious", f"Non-web scheme detected: {cleaned}"

    # Flag internal auth/account registration links as non-event websites
    if any(auth_path in cleaned.lower() for auth_path in ['/login', '/register', 'account.', 'auth.']):
        return cleaned, "suspicious", "Internal portal authentication/registration URL, not external event website"

    was_modified = False

    # Fix spaces between scheme and domain (e.g., 'http:// www.accessabilitiesexpo.com')
    if re.search(r'^[a-zA-Z]+://\s+', cleaned):
        cleaned = re.sub(r'^([a-zA-Z]+://)\s+', r'\1', cleaned)
        was_modified = True

    # Remove interior whitespace in general
    if ' ' in cleaned:
        cleaned = cleaned.replace(' ', '')
        was_modified = True

    # Handle relative URLs
    if cleaned.startswith('/'):
        if base_url:
            cleaned = urljoin(base_url, cleaned)
            was_modified = True
        else:
            return None, "suspicious", "Relative URL without base_url"

    parsed = urlparse(cleaned)

    # Validate scheme
    if parsed.scheme.lower() not in ('http', 'https'):
        # If no scheme, check if it starts with www. or valid host
        if cleaned.startswith('www.') or '.' in cleaned.split('/')[0]:
            cleaned = 'https://' + cleaned
            parsed = urlparse(cleaned)
            was_modified = True
        else:
            return None, "suspicious", f"Unsupported scheme: {parsed.scheme}"

    # Validate hostname
    if not parsed.netloc or '.' not in parsed.netloc:
        return None, "suspicious", f"Invalid hostname or domain: {parsed.netloc}"

    status = "normalized" if was_modified else "verified"
    return cleaned, status, None

# Nunify Dubai Business Events Pipeline — Operational Instructions & Architecture Invariants

> **CRITICAL NOTICE FOR ALL DEVELOPERS & AI AGENTS:**
> Read this document and `AGENTS.md` before making any changes to this repository.
> These rules and architectural invariants are non-negotiable.

---

## 1. Hard Architectural Invariants (Never Break These)

1. **Strictly In-Memory Processing (No Raw HTML Disk Dumps):**
   - **DO NOT** create directories like `data/raw_html/` or dump megabytes of crawled web pages to disk.
   - All page fetches must happen in-memory via `InMemoryBrowserClient` or `urllib.request`.
   - Evidence is stored strictly as **150–300 character quoted text snippets** in `contacts.json` and `events.json`.

2. **The Three Decoupled Specialists:**
   - **Specialist 1 (Web Scout — `src/stage2_contacts/scout.py`):**
     - Navigates event websites in-memory.
     - Inspects `href` slugs, DOM context, and aria labels to resolve vague buttons like *"Know More"*, *"Explore"*, or *"Governance"*.
     - Budget limit: Max 2–3 targeted pages per event.
   - **Specialist 2 (Contact Extractor — `src/stage2_contacts/extractor.py`):**
     - Extracts event-team organizers, directors, and committee members.
     - Semantic role classification: **DO NOT** drop containers purely by CSS class `.speaker` (dual-role leaders like Chairmen who also speak must be retained).
     - Anti-Hallucination Gate: If an LLM returns a snippet not found in page text, it is rejected. If an email/phone is not in the snippet, it is forced to `null`.
   - **Specialist 3 (LinkedIn Verifier — `src/stage3_verification/specialist.py`):**
     - Runs **independently** on `contacts.json` without needing Stage 1 or Stage 2.
     - Name Normalizer strips honorifics (`HE`, `H.E.`, `Dr.`, `Eng.`, `Sheikh`).
     - Tiered search queries: `site:linkedin.com/in "{Name}" "{Org}"`.
     - Rule: A matching name alone is **never** verified (`needs_review`). Independent organizational or event evidence in the snippet is required for `verified`.
     - Rejects non-personal pages (`linkedin.com/company/`).

3. **Offline Test Suite Integrity:**
   - All tests in `tests/` must run 100% offline in under 1 second without requiring live API keys.
   - Use `MockSearchProvider` and `MockLLMProvider` for testing.
   - Current test suite status: **64 passing tests** (`.\.venv\Scripts\python.exe -m pytest -v`).

4. **Credential Security:**
   - Secrets are loaded dynamically from `.env` via `src/__init__.py`.
   - **NEVER** hardcode keys or commit `.env` to Git.

---

## 2. Environment Setup & Configuration

The `.env` file lives in the project root (ignored by `.gitignore`):

```bash
# Live Search Provider (At least one required for live Stage 3 LinkedIn searches)
SERPER_API_KEY=your_serper_key_here
TAVILY_API_KEY=your_tavily_key_here

# LLM Reasoning Provider (At least one required for live Stage 2 LLM extraction)
GEMINI_API_KEY=your_gemini_key_here
NVIDIA_API_KEY=your_nvidia_key_here
GROQ_API_KEY=your_groq_key_here
```

---

## 3. How to Run Each Component

### A. Run Full Offline Test Suite
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### B. Run Specialist 3 (LinkedIn Verification) Independently
```powershell
# Run on all contacts in contacts.json
.\.venv\Scripts\python.exe -m src.stage3_verification.specialist --input data/output/contacts.json

# Run on a limited test batch (e.g. first 2 contacts)
.\.venv\Scripts\python.exe -m src.stage3_verification.specialist --input data/output/contacts.json --limit 2
```

### C. Run Stage 1 (Discover Events from Invest In Dubai Algolia API)
```powershell
.\.venv\Scripts\python.exe src/main.py
```

---

## 4. Output Schemas & Locations

All final deliverables live in `data/output/`:
* `events.json` & `events.csv`: 29 discovered events from Invest in Dubai with verified official websites.
* `events_enriched.json` & `events_enriched.csv`: Events linked to organizers and dynamic sales urgency buckets.
* `organizers.json` & `organizers.csv`: Catalog of organizing entities (DEWA, DWTC, OL Interior, etc.).
* `contacts.json` & `contacts.csv`: Contact records with field-level source evidence, candidate LinkedIn URLs, and verification justifications.

---

## 5. Verification Status Taxonomy

Every contact's LinkedIn status must be one of:
* `verified`: Name matches AND snippet confirms the organization or event affiliation.
* `needs_review`: Name matches, but snippet lacks explicit supporting affiliation or is ambiguous.
* `not_found`: No credible candidate profile found.
* `search_unavailable`: Search could not be performed due to missing API key or network failure.

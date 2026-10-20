# Nunify — Dubai Business Events Intelligence Pipeline

An evidence-first, automated intelligence pipeline designed for Nunify to discover business events in Dubai, extract organizing team contacts, and verify their LinkedIn profiles with strict anti-hallucination guarantees.

---

## 1. Business Objective & Three-Stage Pipeline

The pipeline follows three sequential, decoupled stages governed by [`AGENTS.md`](AGENTS.md):

```
┌────────────────────────────────────────────────────────────────────────┐
│ STAGE 1: Discover Events & Official Websites                           │
│ - Source: Official Invest In Dubai Algolia API backend                 │
│ - Output: 29 verified business events & official event URLs            │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STAGE 2: Scout & Extract Organizing Team Contacts                      │
│ - Specialist 1 (Scout): Navigates event websites in-memory             │
│ - Specialist 2 (Extractor): Extracts organizers with verbatim snippets │
│ - Output: contacts.json with field-level evidence and sales urgency    │
└───────────────────────────────────┬────────────────────────────────────┘
                                    │
                                    ▼
┌────────────────────────────────────────────────────────────────────────┐
│ STAGE 3: Discover & Verify LinkedIn Profiles                           │
│ - Specialist 3 (LinkedIn): Queries Google index (Serper/Tavily)        │
│ - Evaluator: Strict anti-hallucination verification against evidence   │
│ - Output: Final enriched contacts.json & Excel-ready contacts.csv      │
└────────────────────────────────────────────────────────────────────────┘
```

---

## 2. Setup & Execution

### Prerequisites
* Python 3.10+
* Virtual environment (`.venv`)

### Quick Setup
1. Clone / open the workspace:
   ```bash
   cd c:\Users\hp\Desktop\event-contacts
   ```
2. Activate virtual environment:
   ```powershell
   .\.venv\Scripts\Activate.ps1
   ```
3. Copy environment configuration:
   ```powershell
   Copy-Item .env.example .env
   ```
4. Open [`.env`](.env) and add your keys (e.g. `SERPER_API_KEY` or `GEMINI_API_KEY`).

---

## 3. Running the Pipeline & Specialists

### Run Offline Test Suite (64 Tests)
```powershell
.\.venv\Scripts\python.exe -m pytest -v
```

### Run Specialist 3 (LinkedIn Verification) Independently
Specialist 3 accepts `contacts.json` independently without needing to rerun Stages 1 or 2:
```powershell
# Run on all contacts
.\.venv\Scripts\python.exe -m src.stage3_verification.specialist --input data/output/contacts.json

# Run on a limited test batch (e.g. 2 contacts)
.\.venv\Scripts\python.exe -m src.stage3_verification.specialist --input data/output/contacts.json --limit 2
```

---

## 4. Where Every Output Field Originates

All outputs are saved in [`data/output/`](data/output/):

| Deliverable | Key Fields | Origin & Evidence |
| :--- | :--- | :--- |
| `events.csv` / `.json` | Event Name, Dates, Venue, Official Website URL | Invest in Dubai Algolia backend index (`prod104_vd_en`). Zero fabricated URLs. |
| `events_enriched.csv` | Sales Urgency Bucket, Days Until Event, Organizer ID | Calculated dynamically at runtime based on event start date. |
| `organizers.csv` | Organizer Name, Entity Type, Events Organized | Relational catalog linking organizers (DEWA, DWTC, OL Interior) to events. |
| `contacts.csv` / `.json` | Person Name, Job Title, Work Email, Phone, LinkedIn URL, Status, Notes | Extracted in-memory from event websites and verified via live search evidence. |

---

## 5. Strict Anti-Hallucination & Verification Rules

1. **Every Field Requires Source Snippet:** Each extracted name, title, email, and phone is stored with a `supporting_snippet` (150–300 character verbatim quote from the inspected page).
2. **Missing Data Stored as `null`:** If an email or phone is not explicitly published, it is stored as `null`. We never guess, infer from names, or transfer contact details between people.
3. **LinkedIn Name Match Alone Is Never Sufficient:** A matching name returns `needs_review` unless independent organizational or event affiliation is confirmed in the search snippet.
4. **Zero Raw HTML on Disk:** Pages are parsed in-memory, eliminating repository bloat.

---

## 6. How to Interpret Statuses

* **`verified`:** Name matches AND snippet confirms the organization or event affiliation.
* **`needs_review`:** Plausible candidate found, but evidence lacks explicit affiliation proof.
* **`not_found`:** No credible candidate profile found.
* **`search_unavailable`:** Search could not be performed due to missing API key or network error.

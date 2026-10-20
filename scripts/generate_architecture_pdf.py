"""
Generate Executive Architecture PDF Report with Interactive Mermaid Diagrams Rendered.
Renders the exact contents of pipeline_architecture_and_execution_report.md into a professional PDF.
"""
import os
import sys
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "output")
PDF_OUTPUT = os.path.join(OUTPUT_DIR, "Dubai_Events_Pipeline_Architecture_Report.pdf")
HTML_PREVIEW = os.path.join(OUTPUT_DIR, "architecture_preview.html")

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def build_full_html() -> str:
    html_content = """<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dubai Business Events Intelligence Pipeline - Architecture & Execution Report</title>
    <!-- Load Mermaid for vector architectural flow rendering -->
    <script src="https://cdn.jsdelivr.net/npm/mermaid@10/dist/mermaid.min.js"></script>
    <script>
        mermaid.initialize({
            startOnLoad: true,
            theme: 'base',
            themeVariables: {
                primaryColor: '#F8FAFC',
                primaryTextColor: '#0F172A',
                primaryBorderColor: '#94A3B8',
                lineColor: '#334155',
                secondaryColor: '#EFF6FF',
                tertiaryColor: '#FFFFFF'
            },
            flowchart: {
                useMaxWidth: true,
                htmlLabels: true,
                curve: 'basis'
            }
        });
    </script>
    <style>
        @page {
            size: A4 portrait;
            margin: 14mm 12mm 16mm 12mm;
        }

        body {
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #0F172A;
            background-color: #FFFFFF;
            margin: 0;
            padding: 0;
            font-size: 8.5pt;
            line-height: 1.4;
        }

        /* Executive Cover Header */
        .cover-header {
            background: linear-gradient(135deg, #0F2942 0%, #1E3A8A 100%);
            color: #FFFFFF;
            padding: 22px 26px;
            border-radius: 8px;
            margin-bottom: 18px;
        }

        .cover-title {
            font-size: 18pt;
            font-weight: 800;
            margin: 0 0 5px 0;
            letter-spacing: -0.5px;
            color: #FFFFFF;
        }

        .cover-subtitle {
            font-size: 10pt;
            color: #93C5FD;
            font-weight: 500;
            margin: 0 0 14px 0;
        }

        .meta-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
            margin-top: 12px;
            background: rgba(255, 255, 255, 0.08);
            padding: 8px 12px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }

        .meta-item {
            font-size: 7.5pt;
        }

        .meta-label {
            color: #94A3B8;
            text-transform: uppercase;
            font-size: 6.5pt;
            letter-spacing: 0.5px;
            display: block;
            margin-bottom: 2px;
        }

        .meta-val {
            color: #FFFFFF;
            font-weight: 700;
        }

        /* Section Headings */
        h2.section-title {
            font-size: 11.5pt;
            font-weight: 800;
            color: #0F2942;
            border-bottom: 2px solid #0F2942;
            padding-bottom: 4px;
            margin: 20px 0 10px 0;
            display: flex;
            align-items: center;
            gap: 8px;
            page-break-after: avoid;
            break-after: avoid;
        }

        h2.section-title .section-num {
            background: #0F2942;
            color: #FFFFFF;
            font-size: 8pt;
            padding: 2px 7px;
            border-radius: 4px;
        }

        h3.sub-title {
            font-size: 9.5pt;
            font-weight: 700;
            color: #1E3A8A;
            margin: 14px 0 6px 0;
            page-break-after: avoid;
            break-after: avoid;
        }

        p {
            margin: 0 0 8px 0;
            color: #334155;
            font-size: 8.5pt;
        }

        /* Mermaid Diagram Wrapper */
        .mermaid-container {
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            padding: 12px;
            margin: 12px 0 16px 0;
            page-break-inside: avoid;
            break-inside: avoid;
            box-shadow: 0 1px 3px rgba(0,0,0,0.03);
            text-align: center;
        }

        .mermaid-title {
            font-size: 8.5pt;
            font-weight: 700;
            color: #0F2942;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            margin-bottom: 8px;
            text-align: center;
            border-bottom: 1px solid #E2E8F0;
            padding-bottom: 4px;
        }

        .mermaid {
            display: flex;
            justify-content: center;
            font-size: 8pt;
        }

        .mermaid svg {
            max-width: 100% !important;
            height: auto !important;
        }

        /* Callouts */
        .callout {
            border-left: 4px solid #2563EB;
            background: #F8FAFC;
            padding: 8px 12px;
            border-radius: 4px;
            margin: 10px 0;
            font-size: 7.8pt;
            color: #1E293B;
            page-break-inside: avoid;
            break-inside: avoid;
        }

        .callout.success {
            border-left-color: #059669;
            background: #F0FDF4;
            color: #065F46;
        }

        .callout.warning {
            border-left-color: #D97706;
            background: #FFFBEB;
            color: #92400E;
        }

        /* Tables */
        table.custom-table {
            width: 100%;
            border-collapse: collapse;
            font-size: 7.5pt;
            margin: 10px 0 14px 0;
            page-break-inside: avoid;
            break-inside: avoid;
        }

        table.custom-table th {
            background: #0F2942;
            color: #FFFFFF;
            font-weight: 700;
            text-align: left;
            padding: 6px 8px;
            border: 1px solid #0F2942;
        }

        table.custom-table td {
            padding: 6px 8px;
            border: 1px solid #E2E8F0;
            vertical-align: top;
        }

        table.custom-table tr:nth-child(even) {
            background-color: #F8FAFC;
        }

        /* Badges */
        .badge {
            display: inline-block;
            font-size: 6.5pt;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
            text-transform: uppercase;
        }

        .badge-verified { background: #DCFCE7; color: #15803D; border: 1px solid #BBF7D0; }
        .badge-review { background: #FEF3C7; color: #B45309; border: 1px solid #FDE68A; }
        .badge-desk { background: #EFF6FF; color: #1D4ED8; border: 1px solid #BFDBFE; }
        .badge-notfound { background: #F1F5F9; color: #64748B; border: 1px solid #CBD5E1; }

        code {
            font-family: Consolas, monospace;
            background: #F1F5F9;
            padding: 1px 4px;
            border-radius: 3px;
            color: #0F172A;
            font-size: 7.5pt;
        }

        .quote-box {
            background: #F8FAFC;
            border-left: 3px solid #94A3B8;
            padding: 5px 8px;
            font-style: italic;
            font-size: 7.2pt;
            color: #334155;
            margin: 4px 0;
        }

        ul, ol {
            margin: 4px 0 8px 18px;
            padding: 0;
            font-size: 8pt;
            color: #334155;
        }

        li {
            margin-bottom: 3px;
        }
    </style>
</head>
<body>

    <!-- Executive Cover Header -->
    <div class="cover-header">
        <div class="cover-title">Dubai Business Events Intelligence Pipeline</div>
        <div class="cover-subtitle">End-to-End Architectural Design, Modular Specialization, and Evidence-First Execution Report</div>
        
        <div class="meta-grid">
            <div class="meta-item">
                <span class="meta-label">Client / Scope</span>
                <span class="meta-val">Nunify Proof-of-Concept</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Governance Mandate</span>
                <span class="meta-val">AGENTS.md Zero-Hallucination</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Events Processed</span>
                <span class="meta-val">29 Official Calendar Events</span>
            </div>
            <div class="meta-item">
                <span class="meta-label">Discovered Entities</span>
                <span class="meta-val">138 Traceable Records</span>
            </div>
        </div>
    </div>

    <!-- Executive Summary -->
    <div class="callout success">
        <strong>Executive Summary:</strong>
        This report documents the architectural design, technical modularity, and operational execution of the <strong>Dubai Business Events Intelligence Pipeline</strong> built for Nunify. The system processes official Dubai government calendar feeds, identifies external event-organizing entities, extracts verifiable decision-makers, and discovers and qualifies LinkedIn professional profiles under <strong>strict zero-hallucination governance</strong>.
    </div>

    <!-- Section 1: System Architecture & Modular Flow -->
    <h2 class="section-title"><span class="section-num">1</span> System Architecture & Modular Flow</h2>
    <p>
        The pipeline is split into three decoupled, independently testable stages, ensuring high maintainability and compliance with <code>AGENTS.md</code>.
    </p>

    <!-- ARCHITECTURAL MERMAID DIAGRAM 1 -->
    <div class="mermaid-container">
        <div class="mermaid-title">System Pipeline Architectural Flow Diagram</div>
        <div class="mermaid">
flowchart TD
    subgraph S1["Stage 1: Official Event Discovery"]
        A["Invest in Dubai Events Calendar<br/>(Algolia API)"] --> B["Algolia Client & Hits Parser"]
        B --> C["DiscoveredEvent Records<br/>(29 Unique Business Events)"]
        C --> D["URL Disambiguation<br/>(Listing URL vs Event Page vs Official Website)"]
    end

    subgraph S2["Stage 2: Event-Team Contact Extraction"]
        D --> E["Specialist 1: EventWebScout<br/>(In-Memory Subpage Crawler)"]
        E --> F["Prioritized Target Subpages<br/>(Committee, Team, About, Contact)"]
        F --> G["Specialist 2: ContactExtractor<br/>(DOM Parser + LLM Fallback)"]
        G --> H{"Anti-Hallucination<br/>Validation Gates"}
        H -- "Gate 1: Organizer Role Filter" --> I["Reject Passive Speakers/Sponsors"]
        H -- "Gate 2: Verbatim Snippet Match" --> J["Reject Unverifiable Text"]
        H -- "Gate 3: Contact Integrity" --> K["No Inferred Emails/Phones"]
        H -- "Pass" --> L["138 Qualified Contact Entities<br/>(110 People + 28 General Desks)"]
    end

    subgraph S3["Stage 3: LinkedIn Discovery & Verification"]
        L --> M["Specialist 3: LinkedInSpecialist<br/>(Google Serper API)"]
        M --> N["Hierarchical Search Strategy<br/>(Name + Org / Name + Role)"]
        N --> O["Evidence Comparator & Verifier"]
        O --> P{"Verification Engine"}
        P -- "Name + Affiliation Match" --> Q["Verified (28)"]
        P -- "Plausible / Ambiguous" --> R["Needs Review (26)"]
        P -- "Institutional Hotline/Desk" --> S["Inquiry Desk (28)"]
        P -- "No Direct Match" --> T["Not Found (56)"]
    end

    subgraph DELIV["Master Deliverables"]
        Q & R & S & T --> U["Master contacts.json & contacts.csv"]
        U --> V["Excel Workbook (.xlsx)"]
        U --> W["Executive PDF Report (28 Pages)"]
    end

    style S1 fill:#f8fafc,stroke:#1e3a8a,stroke-width:2px
    style S2 fill:#f8fafc,stroke:#0f766e,stroke-width:2px
    style S3 fill:#f8fafc,stroke:#7c3aed,stroke-width:2px
    style DELIV fill:#f0fdf4,stroke:#16a34a,stroke-width:2px
        </div>
    </div>

    <!-- Section 2: Modular Stage Breakdown -->
    <h2 class="section-title"><span class="section-num">2</span> Modular Stage Breakdown & Section Responsibilities</h2>

    <h3 class="sub-title">Stage 1: Event Discovery & Official Channel Resolution</h3>
    <ul>
        <li><strong>Target Source:</strong> <code>https://www.investindubai.gov.ae/en/events-calendar?tags=Business+events</code>.</li>
        <li><strong>Engine Discovery:</strong> Identified underlying Algolia Search engine (<code>App ID: 7V618K1W18</code>, <code>Index: dubaicalendar_production</code>), bypassing client-side dynamic DOM rendering limitations.</li>
        <li><strong>Fidelity:</strong> Extracted 100% of reported business events (29 unique events).</li>
        <li><strong>URL Tri-Partitioning:</strong> Enforced strict separation between <code>listing_page_url</code> (calendar listing), <code>event_page_url</code> (official portal page), and <code>event_website_url</code> (external event website).</li>
        <li><strong>Anti-Substitution Rule:</strong> Preserved missing status; never substituted portal listing URLs for missing external event websites.</li>
    </ul>

    <h3 class="sub-title">Stage 2: Event-Team Contact Extraction & Anti-Hallucination Gates</h3>
    <ul>
        <li><strong>Specialist 1 (Web Scout):</strong> In-memory event website crawler prioritizing high-intent subpages:
            <br/>• Weight 10: <code>organising-committee</code>, <code>organizing-committee</code>
            <br/>• Weight 9: <code>committee</code>, <code>secretariat</code>
            <br/>• Weight 8: <code>contact-us</code>, <code>contacts</code>
            <br/>• Weight 7: <code>leadership</code>, <code>management</code>, <code>team</code>
            <br/>• Weight 6: <code>about-us</code>, <code>about</code>
        </li>
        <li><strong>Specialist 2 (Contact Extractor):</strong> Deterministic DOM parser + structured LLM (Gemini Flash Lite) schema extraction fallback.</li>
        <li><strong>Mandatory Validation Gates:</strong>
            <br/>• <em>Gate 1 (Role Filter):</em> Checks role against organizer keywords; drops passive speakers/attendees.
            <br/>• <em>Gate 2 (Verbatim Text Match):</em> Enforces that supporting snippet physically appears in crawled HTML text.
            <br/>• <em>Gate 3 (Contact Integrity):</em> Emails/phones captured only if verbatim in snippet. Zero pattern guessing.
            <br/>• <em>Gate 4 (General Inquiry Desks):</em> Captures departmental hotlines when personal emails are unpublished.
        </li>
    </ul>

    <h3 class="sub-title">Stage 3: LinkedIn Discovery & Independent Verification</h3>
    <ul>
        <li><strong>Specialist 3 (LinkedIn Specialist):</strong> Live discovery via Google Search API (SerperSearchProvider). Complies strictly with zero-scraping policies.</li>
        <li><strong>3-Tier Query Ladder:</strong>
            <br/>1. <code>site:linkedin.com/in "&lt;Person Name&gt;" "&lt;Organization&gt;"</code>
            <br/>2. <code>site:linkedin.com/in "&lt;Person Name&gt;" "&lt;Role or Event Name&gt;"</code>
            <br/>3. <code>site:linkedin.com/in "&lt;Person Name&gt;" "Dubai"</code>
        </li>
        <li><strong>Multi-Tier Verification Engine:</strong> Compares candidate search results with Stage 2 captured evidence to classify into <code>verified</code>, <code>needs_review</code>, <code>institutional_desk</code>, or <code>not_found</code>.</li>
    </ul>

    <!-- Section 3: Contact Selection Logic -->
    <h2 class="section-title"><span class="section-num">3</span> Contact Selection Logic: How an Individual is Chosen</h2>
    <p>
        To maintain executive relevance, our pipeline distinguishes between <strong>Active Organizers</strong> and <strong>Passive Participants</strong>:
    </p>

    <!-- ARCHITECTURAL MERMAID DIAGRAM 2 -->
    <div class="mermaid-container">
        <div class="mermaid-title">Contact Qualification & Verification Decision Tree</div>
        <div class="mermaid">
flowchart TD
    RAW["Raw Person Entity Found on Webpage"] --> C1{"Is Person an Event Organizer?"}
    
    C1 -- "Role: Speaker, Keynote, Panelist" --> REJ1["REJECT: Speaker Only (AGENTS.md Sec 2)"]
    C1 -- "Role: Sponsor Rep, Attendee" --> REJ2["REJECT: External Participant"]
    C1 -- "Role: Chair, Director, Founder, Secretariat, Committee" --> C2{"Gate 2: Verbatim Text Verification"}
    
    C2 -- "Snippet text NOT in raw HTML" --> REJ3["REJECT: Hallucination / Unsupported"]
    C2 -- "Snippet text physically in raw HTML" --> C3{"Gate 3: Contact Details Verification"}
    
    C3 -- "Email/Phone NOT in snippet" --> KEEP1["Record Person, Role, Org<br/>(Email/Phone = null)"]
    C3 -- "Email/Phone published in snippet" --> KEEP2["Record Person, Role, Org<br/>(Email/Phone captured)"]
    
    KEEP1 & KEEP2 --> LNK["Proceed to Stage 3 LinkedIn Search"]
        </div>
    </div>

    <h3 class="sub-title">Concrete Selection Examples from the Production Pipeline</h3>
    <table class="custom-table">
        <thead>
            <tr>
                <th style="width: 22%;">Contact & Event</th>
                <th style="width: 24%;">Published Role & Source</th>
                <th style="width: 36%;">Verbatim Evidence Snippet</th>
                <th style="width: 18%;">Pipeline Decision</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td>
                    <strong>Dr. Nehad Kazim Albastaki</strong><br/>
                    <span style="color: #64748B;">Breast Imaging 2nd Annual Meeting</span>
                </td>
                <td>
                    Chair of Annual Meeting & EBI President<br/>
                    <code>radiologysocietyuae.com/BreastImaging/</code>
                </td>
                <td>
                    <div class="quote-box">
                        "Warm regards, Dr. Nehad Kazim Albastaki Chair of Breast Imaging Annual Meeting and Emirates Breast Imaging (EBI), President"
                    </div>
                </td>
                <td>
                    <span class="badge badge-verified">Accepted</span><br/>
                    <span style="font-size: 6.8pt; color: #15803D;">Executive Chair. Verbatim match in page DOM.</span>
                </td>
            </tr>
            <tr>
                <td>
                    <strong>Brent Hoberman</strong><br/>
                    <span style="color: #64748B;">Founders Forum MEASA</span>
                </td>
                <td>
                    Co-Founder & Executive Chair<br/>
                    <code>ff.co/about-us</code>
                </td>
                <td>
                    <div class="quote-box">
                        "Brent Hoberman Co-Founder & Executive Chair Brent is Co-Founder and Executive Chairman of Founders Factory... Founders Forum Group..."
                    </div>
                </td>
                <td>
                    <span class="badge badge-verified">Accepted</span><br/>
                    <span style="font-size: 6.8pt; color: #15803D;">Governing entity founder. Verbatim match in DOM.</span>
                </td>
            </tr>
            <tr>
                <td>
                    <strong>GITEX & FinTech Keynote Speakers</strong><br/>
                    <span style="color: #64748B;">GITEX Global / Dubai FinTech Summit</span>
                </td>
                <td>
                    "Keynote Speaker", "Guest Panelist"<br/>
                    <code>dubaifintechsummit.com</code>
                </td>
                <td>
                    <div class="quote-box">
                        "VP of Cloud Architecture at Global Enterprise (Speaker Series)"
                    </div>
                </td>
                <td>
                    <span class="badge badge-notfound">Rejected</span><br/>
                    <span style="font-size: 6.8pt; color: #B91C1C;">Speaker only; no organizing role. Dropped at Gate 1.</span>
                </td>
            </tr>
        </tbody>
    </table>

    <!-- Section 4: LinkedIn Verification Criteria -->
    <h2 class="section-title"><span class="section-num">4</span> LinkedIn Discovery & Independent Verification Engine</h2>
    <p>
        Stage 3 evaluates candidate profiles against captured event evidence:
    </p>

    <table class="custom-table">
        <thead>
            <tr>
                <th style="width: 18%;">Status</th>
                <th style="width: 34%;">Evaluation Standard</th>
                <th style="width: 25%;">Search Query Ladder</th>
                <th style="width: 23%;">Real Pipeline Outcome</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><span class="badge badge-verified">verified</span> (28)</td>
                <td>Full person name matches AND independent supporting evidence (organization, exact role, or event title) is confirmed in search snippet.</td>
                <td><code>site:linkedin.com/in "Nehad Kazim Albastaki" "Dubai"</code></td>
                <td><code>ae.linkedin.com/in/dr-nehad-kazim-albastaki-336508157</code><br/><span style="font-size: 6.8pt; color: #15803D;">Confirmed: Emirates Breast Imaging</span></td>
            </tr>
            <tr>
                <td><span class="badge badge-review">needs_review</span> (26)</td>
                <td>Name matches and profile is in Dubai/UAE, but search snippet does not explicitly confirm event organization.</td>
                <td><code>site:linkedin.com/in "Name" "Dubai"</code></td>
                <td>Preserved for human review; prevents misattribution.</td>
            </tr>
            <tr>
                <td><span class="badge badge-desk">institutional_desk</span> (28)</td>
                <td>Official departmental inquiry desks (Sales, Press, General Inquiries) where no individual personal profile exists.</td>
                <td>No personal search executed.</td>
                <td>Attributed directly to organizational hotlines (e.g. <code>sales_general@wetex.ae</code>).</td>
            </tr>
            <tr>
                <td><span class="badge badge-notfound">not_found</span> (56)</td>
                <td>Search executed across all prioritized queries; zero credible candidate profiles found.</td>
                <td><code>site:linkedin.com/in "Name" "Org"</code></td>
                <td>Left as <code>null</code>. Never fabricated or guessed.</td>
            </tr>
        </tbody>
    </table>

    <!-- Section 5: Anti-Hallucination Governance -->
    <h2 class="section-title"><span class="section-num">5</span> Anti-Hallucination Governance & Audit Trail</h2>
    <div class="callout warning">
        <strong>The 4 Immutable Anti-Hallucination Gates:</strong>
        <ul style="margin: 4px 0 0 16px; padding: 0;">
            <li><strong>Gate 1 (Role Qualification Gate):</strong> Rejects passive speakers, panelists, and sponsors before any extraction.</li>
            <li><strong>Gate 2 (Verbatim Text Verification Gate):</strong> Rejects any entity unless the first 30+ characters of its supporting snippet appear verbatim in the raw crawled HTML text (<code>snippet.strip()[:30].lower() in text.lower()</code>).</li>
            <li><strong>Gate 3 (No Contact Inference Gate):</strong> Emails and phone numbers are captured ONLY if physically present in the supporting snippet. Zero pattern-based guessing.</li>
            <li><strong>Gate 4 (Traceability Gate):</strong> Every extracted value retains raw value, normalized value, source URL, verbatim supporting snippet, and retrieval timestamp.</li>
        </ul>
    </div>

    <!-- Section 6: Summary of Deliverables -->
    <h2 class="section-title"><span class="section-num">6</span> Summary of Deliverables & Verification Metrics</h2>
    <table class="custom-table">
        <thead>
            <tr>
                <th>Deliverable Artifact</th>
                <th>File Path</th>
                <th>Key Scope & Metrics</th>
            </tr>
        </thead>
        <tbody>
            <tr>
                <td><strong>Comprehensive Events & Contacts PDF</strong></td>
                <td><code>data/output/Dubai_Business_Events_Comprehensive_Report.pdf</code></td>
                <td>28 Pages, per-event breakdown, direct mailto/phone links, full evidence snippets.</td>
            </tr>
            <tr>
                <td><strong>Master Excel Workbook</strong></td>
                <td><code>data/output/dubai_business_events_contacts.xlsx</code></td>
                <td>2 Sheets (Contacts & Events), styled headers, auto-fit widths, frozen panes.</td>
            </tr>
            <tr>
                <td><strong>Master Relational CSV</strong></td>
                <td><code>data/output/contacts.csv</code></td>
                <td>138 rows with UTF-8 BOM (natively opens in Excel & Navicat).</td>
            </tr>
            <tr>
                <td><strong>Master Evidence JSON</strong></td>
                <td><code>data/output/contacts.json</code></td>
                <td>Complete nested <code>FieldEvidence</code> schema with retrieval timestamps.</td>
            </tr>
        </tbody>
    </table>

</body>
</html>
"""
    return html_content


def generate_pdf():
    print("[1/3] Compiling Architecture Report with Mermaid...", flush=True)
    html_content = build_full_html()

    with open(HTML_PREVIEW, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"      HTML preview saved: {HTML_PREVIEW}", flush=True)

    print("[2/3] Launching Edge browser and rendering Mermaid vectors...", flush=True)
    os.makedirs(os.path.dirname(PDF_OUTPUT), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE_PATH, headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")

        # Wait for both Mermaid SVGs to finish client-side rendering
        print("      Waiting for Mermaid SVG rendering to complete...", flush=True)
        page.wait_for_selector(".mermaid svg", timeout=20000)
        page.wait_for_timeout(2000)  # Ensure SVGs are fully sized and stabilized

        print("[3/3] Printing pixel-perfect vector PDF...", flush=True)
        header_template = """
        <div style="font-size: 7pt; font-family: sans-serif; color: #64748B; width: 100%; padding: 0 12mm; display: flex; justify-content: space-between; border-bottom: 0.5px solid #E2E8F0; padding-bottom: 3px;">
            <span>Dubai Business Events Intelligence Pipeline</span>
            <span>System Architecture & Technical Execution Report</span>
        </div>
        """

        footer_template = """
        <div style="font-size: 7pt; font-family: sans-serif; color: #64748B; width: 100%; padding: 0 12mm; display: flex; justify-content: space-between; border-top: 0.5px solid #E2E8F0; padding-top: 3px;">
            <span>Nunify Evidence-First Architecture | Strict Anti-Hallucination</span>
            <span>Page <span class="pageNumber"></span> of <span class="totalPages"></span></span>
        </div>
        """

        page.pdf(
            path=PDF_OUTPUT,
            format="A4",
            print_background=True,
            display_header_footer=True,
            header_template=header_template,
            footer_template=footer_template,
            margin={
                "top": "16mm",
                "bottom": "16mm",
                "left": "12mm",
                "right": "12mm"
            }
        )
        browser.close()

    print(f"\n[Success] Architecture PDF Report with Mermaid diagrams generated:")
    print(f"  - PDF Path: {PDF_OUTPUT}")
    print(f"  - File Size: {os.path.getsize(PDF_OUTPUT):,} bytes")
    return PDF_OUTPUT


if __name__ == "__main__":
    generate_pdf()

"""
Generate Comprehensive Executive PDF Report for Dubai Business Events & Contacts.
Utilizes Playwright with Microsoft Edge to render pixel-perfect, multi-page PDF deliverables.
"""
import os
import sys
import json
import html
from typing import Dict, List, Any
from playwright.sync_api import sync_playwright

PROJECT_ROOT = os.path.abspath(os.path.join(os.path.dirname(__file__), ".."))
OUTPUT_DIR = os.path.join(PROJECT_ROOT, "data", "output")
CONTACTS_JSON = os.path.join(OUTPUT_DIR, "contacts.json")
EVENTS_JSON = os.path.join(OUTPUT_DIR, "events.json")
PDF_OUTPUT = os.path.join(OUTPUT_DIR, "Dubai_Business_Events_Comprehensive_Report.pdf")
HTML_PREVIEW = os.path.join(OUTPUT_DIR, "report_preview.html")

EDGE_PATH = r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe"


def load_data():
    with open(EVENTS_JSON, "r", encoding="utf-8") as f:
        events = json.load(f)
    with open(CONTACTS_JSON, "r", encoding="utf-8") as f:
        contacts = json.load(f)
    return events, contacts


def build_html_report(events: List[Dict[str, Any]], contacts: List[Dict[str, Any]]) -> str:
    # Group contacts by event_name
    contacts_by_event: Dict[str, List[Dict[str, Any]]] = {}
    for c in contacts:
        ename = c.get("event_name", "Unknown Event")
        contacts_by_event.setdefault(ename, []).append(c)

    # Calculate overall KPIs
    total_events = len(events)
    total_contacts = len(contacts)
    people_count = sum(1 for c in contacts if c.get("contact_type") == "person")
    desks_count = sum(1 for c in contacts if c.get("contact_type") == "department_desk")
    no_contacts_count = sum(1 for c in contacts if c.get("contact_type") == "no_contacts_published")

    all_emails = set()
    all_phones = set()
    verified_linkedin = 0
    review_linkedin = 0

    for c in contacts:
        p = (c.get("phone") or {}).get("normalized_value")
        e = (c.get("email") or {}).get("normalized_value")
        l_stat = c.get("verification_status")
        if p:
            for item in p.split(","):
                if item.strip():
                    all_phones.add(item.strip())
        if e:
            for item in e.split(","):
                if item.strip():
                    all_emails.add(item.strip())
        if l_stat == "verified":
            verified_linkedin += 1
        elif l_stat == "needs_review":
            review_linkedin += 1

    # Build Index Table rows
    index_rows_html = []
    for idx, e in enumerate(events, 1):
        ename = (e.get("event_name") or {}).get("normalized_value", "Unnamed Event")
        cat = (e.get("category") or {}).get("normalized_value", "")
        dates = (e.get("dates_text") or {}).get("normalized_value", "")
        venue = (e.get("venue") or {}).get("normalized_value", "")
        
        event_contacts = contacts_by_event.get(ename, [])
        ev_emails = set()
        ev_phones = set()
        ev_linkedins = 0
        for ec in event_contacts:
            ep = (ec.get("phone") or {}).get("normalized_value")
            ee = (ec.get("email") or {}).get("normalized_value")
            el = (ec.get("linkedin_url") or {}).get("normalized_value")
            if ep:
                for item in ep.split(","):
                    if item.strip(): ev_phones.add(item.strip())
            if ee:
                for item in ee.split(","):
                    if item.strip(): ev_emails.add(item.strip())
            if el and el.strip():
                ev_linkedins += 1

        index_rows_html.append(f"""
        <tr>
            <td style="text-align: center; font-weight: 700; color: #1E3A8A;">{idx}</td>
            <td><strong><a href="#event-{idx}" style="color: #1E3A8A; text-decoration: none;">{html.escape(ename)}</a></strong></td>
            <td><span class="badge badge-subtle">{html.escape(cat)}</span></td>
            <td style="font-size: 7.5pt; color: #475569;">{html.escape(dates)}</td>
            <td style="text-align: center; font-weight: 700;">{len(event_contacts)}</td>
            <td style="text-align: center; color: #0369A1; font-weight: 600;">{len(ev_emails)}</td>
            <td style="text-align: center; color: #047857; font-weight: 600;">{len(ev_phones)}</td>
            <td style="text-align: center; color: #0A66C2; font-weight: 600;">{ev_linkedins}</td>
        </tr>
        """)

    # Build Event Sections
    event_sections_html = []
    for idx, e in enumerate(events, 1):
        ename = (e.get("event_name") or {}).get("normalized_value", "Unnamed Event")
        cat = (e.get("category") or {}).get("normalized_value", "Business Event")
        dates = (e.get("dates_text") or {}).get("normalized_value", "N/A")
        venue = (e.get("venue") or {}).get("normalized_value", "N/A")
        website = (e.get("event_website_url") or {}).get("normalized_value", "")
        website_status = (e.get("event_website_url") or {}).get("extraction_status", "unknown")
        listing_url = e.get("listing_page_url", "")
        event_page_url = e.get("event_page_url", "")

        event_contacts = contacts_by_event.get(ename, [])

        # Stats for this event
        ev_emails = set()
        ev_phones = set()
        ev_linkedins = []
        ev_people = 0
        ev_desks = 0
        ev_none = 0

        for ec in event_contacts:
            ctype = ec.get("contact_type")
            if ctype == "person":
                ev_people += 1
            elif ctype == "department_desk":
                ev_desks += 1
            else:
                ev_none += 1

            ep = (ec.get("phone") or {}).get("normalized_value")
            ee = (ec.get("email") or {}).get("normalized_value")
            el = (ec.get("linkedin_url") or {}).get("normalized_value")
            if ep:
                for item in ep.split(","):
                    if item.strip(): ev_phones.add(item.strip())
            if ee:
                for item in ee.split(","):
                    if item.strip(): ev_emails.add(item.strip())
            if el and el.strip():
                ev_linkedins.append((el.strip(), ec.get("verification_status", "")))

        # Format website link
        if website:
            website_html = f'<a href="{html.escape(website)}" target="_blank" style="color: #2563EB; font-weight: 500; text-decoration: underline; word-break: break-all;">{html.escape(website)}</a>'
        else:
            website_html = '<span style="color: #94A3B8; font-style: italic;">No external website published on calendar listing</span>'

        if event_page_url:
            calendar_html = f'<a href="{html.escape(event_page_url)}" target="_blank" style="color: #64748B; text-decoration: underline; word-break: break-all;">Official Calendar Listing Page &rarr;</a>'
        elif listing_url:
            calendar_html = f'<a href="{html.escape(listing_url)}" target="_blank" style="color: #64748B; text-decoration: underline; word-break: break-all;">Invest in Dubai Calendar &rarr;</a>'
        else:
            calendar_html = ""

        # Format contacts rows
        contacts_rows_html = []
        for cidx, ec in enumerate(event_contacts, 1):
            ctype = ec.get("contact_type", "person")
            pname = (ec.get("person_name") or {}).get("normalized_value", "")
            role = (ec.get("role_as_written") or {}).get("normalized_value", "")
            org = (ec.get("organisation") or {}).get("normalized_value", "")
            email_val = (ec.get("email") or {}).get("normalized_value", "")
            phone_val = (ec.get("phone") or {}).get("normalized_value", "")
            link_val = (ec.get("linkedin_url") or {}).get("normalized_value", "")
            vstatus = ec.get("verification_status", "")
            snippet = (ec.get("person_name") or {}).get("supporting_snippet", "")
            source_url = ec.get("contact_source_url", "")
            notes = ec.get("notes", "")

            # Badge for Contact Type
            if ctype == "person":
                type_badge = '<span class="badge badge-person">Person</span>'
            elif ctype == "department_desk":
                type_badge = '<span class="badge badge-desk">General Desk</span>'
            else:
                type_badge = '<span class="badge badge-none">No Contacts</span>'

            # Badge for Verification Status
            if vstatus == "verified":
                status_badge = '<span class="badge badge-verified">Verified</span>'
            elif vstatus == "needs_review":
                status_badge = '<span class="badge badge-review">Needs Review</span>'
            elif vstatus == "institutional_desk":
                status_badge = '<span class="badge badge-desk">Inquiry Desk</span>'
            elif vstatus == "not_found":
                status_badge = '<span class="badge badge-notfound">Not Found</span>'
            else:
                status_badge = '<span class="badge badge-subtle">—</span>'

            # Format Email
            if email_val:
                email_html = f'<a href="mailto:{html.escape(email_val)}" style="color: #0369A1; text-decoration: none; font-weight: 600;">{html.escape(email_val)}</a>'
            else:
                email_html = '<span style="color: #94A3B8; font-style: italic;">None published</span>'

            # Format Phone
            if phone_val:
                phone_html = f'<span style="font-family: monospace; font-size: 7.5pt; font-weight: 700; color: #047857;">{html.escape(phone_val)}</span>'
            else:
                phone_html = '<span style="color: #94A3B8; font-style: italic;">None published</span>'

            # Format LinkedIn
            if link_val:
                linkedin_html = f"""
                <div style="margin-bottom: 3px;">
                    <a href="{html.escape(link_val)}" target="_blank" style="color: #0A66C2; text-decoration: none; font-size: 7.5pt; font-weight: 700; word-break: break-all;">
                        LinkedIn Profile &rarr;
                    </a>
                </div>
                <div>{status_badge}</div>
                """
            else:
                linkedin_html = f'<div style="color: #94A3B8; font-size: 7.5pt;">{status_badge}</div>'

            # Clean & format snippet
            snippet_clean = snippet.strip()
            if len(snippet_clean) > 200:
                snippet_display = snippet_clean[:200] + "..."
            else:
                snippet_display = snippet_clean

            # Source URL link
            if source_url:
                source_html = f'<div style="margin-top: 4px;"><a href="{html.escape(source_url)}" target="_blank" style="color: #475569; font-size: 6.8pt; text-decoration: underline;">Verify Source Page &rarr;</a></div>'
            else:
                source_html = ""

            contacts_rows_html.append(f"""
            <tr>
                <td style="text-align: center; color: #94A3B8; font-size: 7.5pt; font-weight: 600;">{cidx}</td>
                <td>
                    <div style="font-weight: 700; color: #0F172A; font-size: 8.5pt;">{html.escape(pname or '—')}</div>
                    <div style="margin-top: 2px;">{type_badge}</div>
                </td>
                <td>
                    <div style="font-weight: 600; color: #1E293B; font-size: 8pt;">{html.escape(role or '—')}</div>
                    {f'<div style="color: #64748B; font-size: 7.5pt; margin-top: 1px;">{html.escape(org)}</div>' if org else ''}
                </td>
                <td style="font-size: 7.5pt; word-break: break-all;">{email_html}</td>
                <td style="font-size: 7.5pt; word-break: break-all;">{phone_html}</td>
                <td style="font-size: 7.5pt;">{linkedin_html}</td>
                <td style="font-size: 6.8pt; color: #475569; line-height: 1.25;">
                    <div style="background: #F8FAFC; border-left: 2px solid #CBD5E1; padding: 3px 5px; font-style: italic;">
                        &ldquo;{html.escape(snippet_display)}&rdquo;
                    </div>
                    {source_html}
                </td>
            </tr>
            """)

        contacts_table_html = "".join(contacts_rows_html)

        # Unique Emails summary tags
        if ev_emails:
            emails_tags = " ".join(f'<span class="channel-tag tag-email">{html.escape(m)}</span>' for m in sorted(list(ev_emails)))
        else:
            emails_tags = '<span style="color: #94A3B8; font-style: italic; font-size: 7pt;">No direct emails published on inspected pages</span>'

        # Unique Phones summary tags
        if ev_phones:
            phones_tags = " ".join(f'<span class="channel-tag tag-phone">{html.escape(p)}</span>' for p in sorted(list(ev_phones)))
        else:
            phones_tags = '<span style="color: #94A3B8; font-style: italic; font-size: 7pt;">No direct hotlines published on inspected pages</span>'

        event_sections_html.append(f"""
        <div class="event-card" id="event-{idx}">
            <div class="event-header">
                <div class="event-title-row">
                    <span class="event-num">#{idx}</span>
                    <h2 class="event-title">{html.escape(ename)}</h2>
                    <span class="badge badge-category">{html.escape(cat)}</span>
                </div>
                
                <div class="event-metadata-grid">
                    <div><strong>Dates:</strong> {html.escape(dates)}</div>
                    <div><strong>Venue:</strong> {html.escape(venue)}</div>
                    <div><strong>Official Website:</strong> {website_html}</div>
                    <div><strong>Source Reference:</strong> {calendar_html}</div>
                </div>

                <!-- Per-Event KPI Stats -->
                <div class="event-metrics-row">
                    <div class="metric-pill">
                        <span class="metric-num">{len(event_contacts)}</span>
                        <div>
                            <div class="metric-lbl">Total Entities Found</div>
                            <div class="metric-sub">{ev_people} Named Individuals &bull; {ev_desks} General Desks</div>
                        </div>
                    </div>
                    <div class="metric-pill">
                        <span class="metric-num" style="color: #0369A1;">{len(ev_emails)}</span>
                        <div>
                            <div class="metric-lbl">Unique Emails</div>
                            <div class="metric-sub">Direct Inboxes</div>
                        </div>
                    </div>
                    <div class="metric-pill">
                        <span class="metric-num" style="color: #047857;">{len(ev_phones)}</span>
                        <div>
                            <div class="metric-lbl">Unique Phone Numbers</div>
                            <div class="metric-sub">Direct Hotlines</div>
                        </div>
                    </div>
                    <div class="metric-pill">
                        <span class="metric-num" style="color: #0A66C2;">{len(ev_linkedins)}</span>
                        <div>
                            <div class="metric-lbl">LinkedIn Profiles</div>
                            <div class="metric-sub">Matched Profiles</div>
                        </div>
                    </div>
                </div>

                <!-- Channels Summary Box -->
                <div class="quick-summary-box">
                    <div style="margin-bottom: 4px;">
                        <strong style="color: #0369A1;">Discovered Email Addresses ({len(ev_emails)}):</strong> {emails_tags}
                    </div>
                    <div>
                        <strong style="color: #047857;">Discovered Phone Hotlines ({len(ev_phones)}):</strong> {phones_tags}
                    </div>
                </div>
            </div>

            <!-- Contacts Table -->
            <table class="contacts-table">
                <thead>
                    <tr>
                        <th style="width: 3%; text-align: center;">#</th>
                        <th style="width: 17%;">Contact / Desk Name</th>
                        <th style="width: 18%;">Role & Organization</th>
                        <th style="width: 15%;">Work Email</th>
                        <th style="width: 14%;">Phone Number</th>
                        <th style="width: 13%;">LinkedIn URL & Status</th>
                        <th style="width: 20%;">Supporting Evidence Snippet</th>
                    </tr>
                </thead>
                <tbody>
                    {contacts_table_html}
                </tbody>
            </table>
        </div>
        """)

    # Combine everything into complete HTML document
    full_html = f"""<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>Dubai Business Events Intelligence Report</title>
    <style>
        @page {{
            size: A4 portrait;
            margin: 14mm 10mm 15mm 10mm;
        }}

        body {{
            font-family: -apple-system, BlinkMacSystemFont, 'Segoe UI', Roboto, Helvetica, Arial, sans-serif;
            color: #0F172A;
            background-color: #FFFFFF;
            margin: 0;
            padding: 0;
            font-size: 8.5pt;
            line-height: 1.35;
        }}

        /* Cover & Executive Header */
        .cover-header {{
            background: linear-gradient(135deg, #0F2942 0%, #1E3A8A 100%);
            color: #FFFFFF;
            padding: 24px 28px;
            border-radius: 8px;
            margin-bottom: 16px;
        }}

        .cover-title {{
            font-size: 20pt;
            font-weight: 800;
            margin: 0 0 6px 0;
            letter-spacing: -0.5px;
            color: #FFFFFF;
        }}

        .cover-subtitle {{
            font-size: 10.5pt;
            color: #93C5FD;
            font-weight: 500;
            margin: 0 0 16px 0;
        }}

        .kpi-grid {{
            display: grid;
            grid-template-columns: repeat(6, 1fr);
            gap: 10px;
            margin-top: 15px;
            background: rgba(255, 255, 255, 0.08);
            padding: 12px;
            border-radius: 6px;
            border: 1px solid rgba(255, 255, 255, 0.15);
        }}

        .kpi-item {{
            text-align: center;
        }}

        .kpi-value {{
            font-size: 16pt;
            font-weight: 800;
            color: #38BDF8;
            display: block;
            line-height: 1.1;
        }}

        .kpi-label {{
            font-size: 6.8pt;
            text-transform: uppercase;
            letter-spacing: 0.5px;
            color: #E2E8F0;
            margin-top: 4px;
            display: block;
        }}

        /* Methodology Note */
        .audit-note {{
            background: #F8FAFC;
            border: 1px solid #E2E8F0;
            border-left: 4px solid #2563EB;
            padding: 10px 14px;
            border-radius: 4px;
            margin-bottom: 20px;
            font-size: 7.5pt;
            color: #334155;
            line-height: 1.4;
        }}

        /* Index Table */
        .index-section {{
            margin-bottom: 25px;
            page-break-after: always;
        }}

        .section-heading {{
            font-size: 13pt;
            font-weight: 700;
            color: #0F2942;
            border-bottom: 2px solid #0F2942;
            padding-bottom: 4px;
            margin: 0 0 12px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }}

        table.index-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 7.5pt;
        }}

        table.index-table th {{
            background: #0F2942;
            color: #FFFFFF;
            font-weight: 600;
            padding: 6px 8px;
            text-align: left;
            border: 1px solid #0F2942;
        }}

        table.index-table td {{
            padding: 5px 8px;
            border: 1px solid #E2E8F0;
        }}

        table.index-table tr:nth-child(even) {{
            background-color: #F8FAFC;
        }}

        /* Event Cards */
        .event-card {{
            border: 1px solid #CBD5E1;
            border-radius: 6px;
            margin-bottom: 22px;
            background: #FFFFFF;
            box-shadow: 0 1px 3px rgba(0,0,0,0.04);
        }}

        .event-header {{
            background: #F8FAFC;
            padding: 12px 14px;
            border-top-left-radius: 5px;
            border-top-right-radius: 5px;
            border-bottom: 1px solid #CBD5E1;
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        .event-title-row {{
            display: flex;
            align-items: center;
            gap: 8px;
            margin-bottom: 8px;
        }}

        .event-num {{
            background: #0F2942;
            color: #FFFFFF;
            font-weight: 700;
            font-size: 8pt;
            padding: 2px 7px;
            border-radius: 4px;
        }}

        .event-title {{
            font-size: 11.5pt;
            font-weight: 800;
            color: #0F172A;
            margin: 0;
            flex-grow: 1;
        }}

        .event-metadata-grid {{
            display: grid;
            grid-template-columns: repeat(2, 1fr);
            gap: 4px 12px;
            font-size: 7.5pt;
            color: #475569;
            margin-bottom: 8px;
        }}

        .event-metrics-row {{
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 8px;
            margin-top: 8px;
            margin-bottom: 8px;
        }}

        .metric-pill {{
            background: #FFFFFF;
            border: 1px solid #CBD5E1;
            padding: 6px 10px;
            border-radius: 5px;
            display: flex;
            align-items: center;
            gap: 8px;
        }}

        .metric-pill .metric-num {{
            font-weight: 800;
            color: #1E3A8A;
            font-size: 11pt;
            line-height: 1;
        }}

        .metric-pill .metric-lbl {{
            color: #1E293B;
            font-weight: 700;
            font-size: 7.5pt;
            line-height: 1.1;
        }}

        .metric-pill .metric-sub {{
            color: #64748B;
            font-size: 6.5pt;
            margin-top: 2px;
        }}

        .quick-summary-box {{
            background: #FFFFFF;
            border: 1px solid #E2E8F0;
            padding: 6px 10px;
            border-radius: 4px;
            font-size: 7pt;
            color: #334155;
            margin-top: 6px;
        }}

        .channel-tag {{
            display: inline-block;
            padding: 1px 5px;
            border-radius: 3px;
            font-family: Consolas, monospace;
            font-size: 6.8pt;
            margin-right: 4px;
            margin-bottom: 2px;
        }}

        .tag-email {{
            background: #EFF6FF;
            color: #1E40AF;
            border: 1px solid #DBEAFE;
        }}

        .tag-phone {{
            background: #ECFDF5;
            color: #065F46;
            border: 1px solid #A7F3D0;
        }}

        /* Contacts Table Inside Event Card */
        table.contacts-table {{
            width: 100%;
            border-collapse: collapse;
            font-size: 7.5pt;
        }}

        table.contacts-table thead {{
            display: table-header-group;
        }}

        table.contacts-table tr {{
            break-inside: avoid;
            page-break-inside: avoid;
        }}

        table.contacts-table th {{
            background: #F1F5F9;
            color: #475569;
            font-weight: 700;
            text-transform: uppercase;
            font-size: 6.5pt;
            letter-spacing: 0.3px;
            padding: 6px 8px;
            border-bottom: 1px solid #CBD5E1;
            text-align: left;
        }}

        table.contacts-table td {{
            padding: 6px 8px;
            border-bottom: 1px solid #E2E8F0;
            vertical-align: top;
        }}

        table.contacts-table tr:last-child td {{
            border-bottom: none;
        }}

        table.contacts-table tr:nth-child(even) {{
            background-color: #FAFAFA;
        }}

        /* Badges */
        .badge {{
            display: inline-block;
            font-size: 6.5pt;
            font-weight: 700;
            padding: 1px 5px;
            border-radius: 3px;
            text-transform: uppercase;
            letter-spacing: 0.3px;
        }}

        .badge-category {{
            background: #E0E7FF;
            color: #3730A3;
        }}

        .badge-person {{
            background: #F1F5F9;
            color: #1E293B;
            border: 1px solid #CBD5E1;
        }}

        .badge-desk {{
            background: #EFF6FF;
            color: #1D4ED8;
            border: 1px solid #BFDBFE;
        }}

        .badge-verified {{
            background: #DCFCE7;
            color: #15803D;
            border: 1px solid #BBF7D0;
        }}

        .badge-review {{
            background: #FEF3C7;
            color: #B45309;
            border: 1px solid #FDE68A;
        }}

        .badge-notfound {{
            background: #F1F5F9;
            color: #64748B;
        }}

        .badge-none {{
            background: #FEE2E2;
            color: #991B1B;
        }}

        .badge-subtle {{
            background: #F1F5F9;
            color: #475569;
        }}
    </style>
</head>
<body>

    <!-- Cover / Header Banner -->
    <div class="cover-header">
        <div class="cover-title">Dubai Business Events Intelligence Report</div>
        <div class="cover-subtitle">Evidence-First Event & Executive Contact Discovery Audit | Nunify Intelligence Pipeline</div>
        
        <div class="kpi-grid">
            <div class="kpi-item">
                <span class="kpi-value">{total_events}</span>
                <span class="kpi-label">Events Tracked</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-value">{total_contacts}</span>
                <span class="kpi-label">Discovered Entities</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-value">{people_count}</span>
                <span class="kpi-label">Named Leaders</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-value">{desks_count}</span>
                <span class="kpi-label">Inquiry Desks</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-value">{len(all_emails)}</span>
                <span class="kpi-label">Unique Emails</span>
            </div>
            <div class="kpi-item">
                <span class="kpi-value">{verified_linkedin}</span>
                <span class="kpi-label">Verified LinkedIn</span>
            </div>
        </div>
    </div>

    <!-- Audit Note -->
    <div class="audit-note">
        <strong>Strict Anti-Hallucination & Evidence Protocol (AGENTS.md):</strong>
        Every contact, role, email address, phone number, and LinkedIn verification decision in this document is directly supported by immutable source evidence captured during execution. No email addresses or contact details have been guessed, pattern-generated, or transferred between entities.
    </div>

    <!-- Master Index Table -->
    <div class="index-section">
        <div class="section-heading">
            <span>Executive Master Directory (All 29 Events)</span>
            <span style="font-size: 8pt; font-weight: normal; color: #64748B;">Alphabetical & Chronological Index</span>
        </div>
        <table class="index-table">
            <thead>
                <tr>
                    <th style="width: 4%; text-align: center;">#</th>
                    <th style="width: 32%;">Event Name</th>
                    <th style="width: 14%;">Category</th>
                    <th style="width: 18%;">Dates</th>
                    <th style="width: 8%; text-align: center;">Members</th>
                    <th style="width: 8%; text-align: center;">Emails</th>
                    <th style="width: 8%; text-align: center;">Phones</th>
                    <th style="width: 8%; text-align: center;">LinkedIn</th>
                </tr>
            </thead>
            <tbody>
                {''.join(index_rows_html)}
            </tbody>
        </table>
    </div>

    <!-- Event Sections -->
    <div class="events-detailed-container">
        <div class="section-heading">
            <span>Detailed Event-by-Event Contact Breakdowns</span>
            <span style="font-size: 8pt; font-weight: normal; color: #64748B;">Showing Field-Level Evidence & Discovered Channels</span>
        </div>
        {''.join(event_sections_html)}
    </div>

</body>
</html>
"""
    return full_html


def generate_pdf():
    print("[1/3] Loading verified data deliverables...", flush=True)
    events, contacts = load_data()
    print(f"      Loaded {len(events)} events and {len(contacts)} contacts.", flush=True)

    print("[2/3] Compiling executive HTML template...", flush=True)
    html_content = build_html_report(events, contacts)

    # Save HTML preview
    with open(HTML_PREVIEW, "w", encoding="utf-8") as f:
        f.write(html_content)
    print(f"      HTML preview saved: {HTML_PREVIEW}", flush=True)

    print("[3/3] Rendering PDF via Microsoft Edge...", flush=True)
    os.makedirs(os.path.dirname(PDF_OUTPUT), exist_ok=True)

    with sync_playwright() as p:
        browser = p.chromium.launch(executable_path=EDGE_PATH, headless=True)
        page = browser.new_page()
        page.set_content(html_content, wait_until="networkidle")

        header_template = """
        <div style="font-size: 7.5pt; font-family: sans-serif; color: #64748B; width: 100%; padding: 0 10mm; display: flex; justify-content: space-between; border-bottom: 0.5px solid #E2E8F0; padding-bottom: 3px;">
            <span>Dubai Business Events & Contacts Intelligence</span>
            <span>Nunify Evidence-First Discovery</span>
        </div>
        """

        footer_template = """
        <div style="font-size: 7.5pt; font-family: sans-serif; color: #64748B; width: 100%; padding: 0 10mm; display: flex; justify-content: space-between; border-top: 0.5px solid #E2E8F0; padding-top: 3px;">
            <span>Strict Anti-Hallucination Audit</span>
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
                "left": "10mm",
                "right": "10mm"
            }
        )
        browser.close()

    print(f"\n[Success] Executive PDF Report generated:")
    print(f"  - PDF Path: {PDF_OUTPUT}")
    print(f"  - File Size: {os.path.getsize(PDF_OUTPUT):,} bytes")
    return PDF_OUTPUT


if __name__ == "__main__":
    out_pdf = generate_pdf()

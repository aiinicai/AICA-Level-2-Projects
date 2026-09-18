"""
build_ppt.py
Creates an enterprise 16:9 widescreen PowerPoint presentation (.pptx)
for the LC Analyser Capstone Project.
"""

import os
from pptx import Presentation
from pptx.util import Inches, Pt
from pptx.dml.color import RGBColor
from pptx.enum.text import PP_ALIGN, MSO_ANCHOR
from pptx.enum.shapes import MSO_SHAPE

def create_deck():
    prs = Presentation()
    prs.slide_width = Inches(13.333)
    prs.slide_height = Inches(7.5)
    blank_layout = prs.slide_layouts[6] # completely blank

    # Colors
    C_NAVY_DARK = RGBColor(15, 41, 66)      # #0F2942
    C_NAVY_LIGHT = RGBColor(30, 58, 138)    # #1E3A8A
    C_ROYAL_BLUE = RGBColor(37, 99, 235)    # #2563EB
    C_SLATE_DARK = RGBColor(15, 23, 42)     # #0F172A
    C_SLATE_MUTED = RGBColor(100, 116, 139) # #64748B
    C_BG_CARD = RGBColor(248, 250, 252)     # #F8FAFC
    C_BORDER_CARD = RGBColor(226, 232, 240) # #E2E8F0
    C_WHITE = RGBColor(255, 255, 255)
    C_GREEN = RGBColor(5, 150, 105)         # #059669
    C_RED = RGBColor(220, 38, 38)           # #DC2626
    C_AMBER = RGBColor(217, 119, 6)         # #D97706
    C_ICE_BLUE = RGBColor(235, 243, 250)    # #EBF3FA

    def add_header(slide, category_tag, title_text, dark=False):
        """Adds a consistent branded header to a content slide."""
        # Top accent bar
        accent = slide.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(0.12))
        accent.fill.solid()
        accent.fill.fore_color.rgb = C_ROYAL_BLUE
        accent.line.fill.background()

        # Category Tag
        tx_tag = slide.shapes.add_textbox(Inches(0.8), Inches(0.4), Inches(11.7), Inches(0.35))
        tf_tag = tx_tag.text_frame
        tf_tag.word_wrap = True
        tf_tag.margin_left = tf_tag.margin_top = tf_tag.margin_right = tf_tag.margin_bottom = 0
        p_tag = tf_tag.paragraphs[0]
        p_tag.text = category_tag.upper()
        p_tag.font.name = "Segoe UI"
        p_tag.font.size = Pt(11)
        p_tag.font.bold = True
        p_tag.font.color.rgb = C_ROYAL_BLUE if not dark else C_ICE_BLUE

        # Slide Title
        tx_title = slide.shapes.add_textbox(Inches(0.8), Inches(0.75), Inches(11.7), Inches(0.65))
        tf_title = tx_title.text_frame
        tf_title.word_wrap = True
        tf_title.margin_left = tf_title.margin_top = tf_title.margin_right = tf_title.margin_bottom = 0
        p_title = tf_title.paragraphs[0]
        p_title.text = title_text
        p_title.font.name = "Segoe UI"
        p_title.font.size = Pt(22)
        p_title.font.bold = True
        p_title.font.color.rgb = C_NAVY_DARK if not dark else C_WHITE

    def add_card(slide, left, top, width, height, bg_color=C_BG_CARD, border_color=C_BORDER_CARD):
        """Adds a rounded clean background card for content grouping."""
        card = slide.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, height)
        card.fill.solid()
        card.fill.fore_color.rgb = bg_color
        if border_color:
            card.line.color.rgb = border_color
            card.line.width = Pt(1)
        else:
            card.line.fill.background()
        return card

    def add_notes(slide, notes_text):
        """Adds presenter speaking track notes to the slide."""
        notes_slide = slide.notes_slide
        tf = notes_slide.notes_text_frame
        tf.text = notes_text

    # =========================================================================
    # SLIDE 1: Title Slide (Dark Background)
    # =========================================================================
    s1 = prs.slides.add_slide(blank_layout)
    bg1 = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg1.fill.solid()
    bg1.fill.fore_color.rgb = C_NAVY_DARK
    bg1.line.fill.background()

    # Left decorative accent pillar
    bar = s1.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0.8), Inches(1.8), Inches(0.18), Inches(3.8))
    bar.fill.solid()
    bar.fill.fore_color.rgb = C_ROYAL_BLUE
    bar.line.fill.background()

    # Title box
    tx_t = s1.shapes.add_textbox(Inches(1.2), Inches(1.6), Inches(11.2), Inches(4.2))
    tf_t = tx_t.text_frame
    tf_t.word_wrap = True

    p0 = tf_t.paragraphs[0]
    p0.text = "ICAI AICA LEVEL 2 — CAPSTONE PROJECT"
    p0.font.name = "Segoe UI"
    p0.font.size = Pt(13)
    p0.font.bold = True
    p0.font.color.rgb = C_ROYAL_BLUE

    p1 = tf_t.add_paragraph()
    p1.text = "LC Analyser"
    p1.font.name = "Segoe UI"
    p1.font.size = Pt(40)
    p1.font.bold = True
    p1.font.color.rgb = C_WHITE
    p1.space_before = Pt(8)

    p2 = tf_t.add_paragraph()
    p2.text = "Automated Letter of Credit Scrutiny, Discrepancy & Risk Auditor"
    p2.font.name = "Segoe UI"
    p2.font.size = Pt(20)
    p2.font.color.rgb = C_ICE_BLUE
    p2.space_before = Pt(6)

    p3 = tf_t.add_paragraph()
    p3.text = "A two-stage hybrid AI engineering journey (Claude + Antigravity) delivering an offline, UCP 600 compliant desktop suite for trade finance professionals and Chartered Accountants."
    p3.font.name = "Segoe UI"
    p3.font.size = Pt(13)
    p3.font.color.rgb = C_SLATE_MUTED
    p3.space_before = Pt(14)

    p4 = tf_t.add_paragraph()
    p4.text = "Author: Shree Gopal Jajoo  |  Technology: Python 3.14 · Tkinter · SQLite · ReportLab · PyInstaller"
    p4.font.name = "Segoe UI"
    p4.font.size = Pt(12)
    p4.font.bold = True
    p4.font.color.rgb = C_WHITE
    p4.space_before = Pt(24)

    add_notes(s1, "Good morning/afternoon respected mentors and peers. I am proud to present 'LC Analyser', an enterprise desktop software engineered to solve one of the most critical and risk-prone bottlenecks in international trade finance: the examination of Letters of Credit under international regulatory standards.")

    # =========================================================================
    # SLIDE 2: The Trade Finance Dilemma
    # =========================================================================
    s2 = prs.slides.add_slide(blank_layout)
    add_header(s2, "The Problem Statement", "The High-Stakes World of Documentary Credits: Critical Bottlenecks")

    cards_data_s2 = [
        ("The Scale & Error Rate", C_RED, [
            "Over $3 Trillion in global merchandise trade moves under Letters of Credit annually.",
            "60% to 70% of first-time document presentations are rejected by banks due to discrepancies.",
            "Each discrepancy costs $75 to $150 in direct bank charges, plus lost cash discounts and working capital interest."
        ]),
        ("Strict Compliance (UCP 600)", C_AMBER, [
            "Under UCP 600 Article 14, banks examine documents on their face alone for strict compliance.",
            "Even a single missing comma, misspelled entity name, or 1-day timeline gap permits the issuing bank to dishonor payment.",
            "Disputes delay container releases, triggering heavy port demurrage and shipping line detention penalties."
        ]),
        ("Manual Fatigue & Soft Clauses", C_NAVY_LIGHT, [
            "Manual review takes 3 to 4 hours per LC across 30+ SWIFT MT700 field tags and fine print.",
            "High risk of overlooking 'Soft Clauses' — buyer sample approval traps that destroy the bank's irrevocable guarantee.",
            "Auditors lack standardized digital checklists, leaving working capital exposed to human oversight."
        ])
    ]

    for idx, (title, accent_col, bullets) in enumerate(cards_data_s2):
        left = Inches(0.8 + idx * 3.95)
        top = Inches(1.6)
        width = Inches(3.75)
        height = Inches(5.2)

        add_card(s2, left, top, width, height)

        # Top color accent on card
        c_top = s2.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, Inches(0.45))
        c_top.fill.solid()
        c_top.fill.fore_color.rgb = accent_col
        c_top.line.fill.background()

        tx = s2.shapes.add_textbox(left + Inches(0.2), top + Inches(0.08), width - Inches(0.4), Inches(0.35))
        p = tx.text_frame.paragraphs[0]
        p.text = title
        p.font.name = "Segoe UI"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = C_WHITE

        # Content bullets
        tx_b = s2.shapes.add_textbox(left + Inches(0.2), top + Inches(0.65), width - Inches(0.4), height - Inches(0.8))
        tf_b = tx_b.text_frame
        tf_b.word_wrap = True
        for b_idx, bullet in enumerate(bullets):
            pb = tf_b.paragraphs[0] if b_idx == 0 else tf_b.add_paragraph()
            pb.text = "• " + bullet
            pb.font.name = "Segoe UI"
            pb.font.size = Pt(12)
            pb.font.color.rgb = C_SLATE_DARK
            pb.space_before = Pt(12)

    add_notes(s2, "In trade finance, banks deal strictly with documents, not goods. Under UCP 600, strict compliance applies. A simple mismatch between shipment date and presentation period or a subtle soft clause can freeze millions of rupees in working capital. Currently, Chartered Accountants and trade professionals review these manually under intense time pressure.")

    # =========================================================================
    # SLIDE 3: Executive Overview
    # =========================================================================
    s3 = prs.slides.add_slide(blank_layout)
    add_header(s3, "Solution Overview", "Introducing LC Analyser: What Does It Do?")

    grid_s3 = [
        ("Instant PDF Ingestion", "Ingests text-based PDF copies of Letters of Credit directly from SWIFT MT700 prints or narrative formats, eliminating manual data re-entry."),
        ("Rule-Based Regulatory Scrutiny", "Deconstructs the LC into 4 core sections and 8 specialized sub-categories, auditing every clause against UCP 600 & ISBP 745 benchmarks."),
        ("Live KPI Risk Dashboard", "Visualizes compliance posture with dynamic badges: Green (In Order), Red (Requires Amendment), Amber (Needs Clarification), and Slate (Informational)."),
        ("Human-in-the-Loop Workspace", "Empowers auditors with an adjustable split-pane viewer to inspect original clause wording, toggle verdicts, and document custom audit remarks."),
        ("One-Click Report Generation", "Instantly produces comprehensive Word & PDF audit reports, executive sign-off summaries, and auto-drafted formal Amendment Request Letters."),
        ("100% Offline Air-Gapped Privacy", "Zero cloud calls or external API dependencies. All calculations, parsing, and storage execute strictly locally on the user's desktop.")
    ]

    for idx, (title, desc) in enumerate(grid_s3):
        col = idx % 3
        row = idx // 3
        left = Inches(0.8 + col * 3.95)
        top = Inches(1.6 + row * 2.65)
        width = Inches(3.75)
        height = Inches(2.4)

        add_card(s3, left, top, width, height)

        tx = s3.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), width - Inches(0.5), height - Inches(0.4))
        tf = tx.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.name = "Segoe UI"
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = C_NAVY_LIGHT

        p1 = tf.add_paragraph()
        p1.text = desc
        p1.font.name = "Segoe UI"
        p1.font.size = Pt(12)
        p1.font.color.rgb = C_SLATE_DARK
        p1.space_before = Pt(8)

    add_notes(s3, "LC Analyser is an offline, enterprise-grade desktop assistant. It takes a raw LC PDF, decomposes it clause by clause, flags discrepancies against international banking rules, tracks risk on a live KPI dashboard, and generates ready-to-send amendment letters to the buyer within seconds.")

    # =========================================================================
    # SLIDE 4: The Collaborative AI Build Journey
    # =========================================================================
    s4 = prs.slides.add_slide(blank_layout)
    add_header(s4, "Engineering Methodology", "The Two-Stage Collaborative AI Build Journey: Claude + Antigravity")

    # Stage 1 Card
    add_card(s4, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    top_c1 = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(0.8), Inches(1.6), Inches(5.6), Inches(0.6))
    top_c1.fill.solid()
    top_c1.fill.fore_color.rgb = C_ROYAL_BLUE
    top_c1.line.fill.background()

    tx_c1 = s4.shapes.add_textbox(Inches(1.0), Inches(1.72), Inches(5.2), Inches(0.4))
    tx_c1.text_frame.paragraphs[0].text = "STAGE 1: Algorithmic Foundation (Claude)"
    tx_c1.text_frame.paragraphs[0].font.name = "Segoe UI"
    tx_c1.text_frame.paragraphs[0].font.size = Pt(14)
    tx_c1.text_frame.paragraphs[0].font.bold = True
    tx_c1.text_frame.paragraphs[0].font.color.rgb = C_WHITE

    c1_bullets = [
        "Prompt-driven design of domain models (ClausePoint, AnalysisResult).",
        "PDF text stream extraction logic using pypdf.",
        "Regex-based SWIFT MT700 tag parsing engine (:20:, :31C:, :46A:, :47A:).",
        "Initial date-consistency rules matrix (expiry vs. shipment vs. 21-day rule).",
        "Baseline Tkinter concept and initial export scripts."
    ]
    tx_c1_b = s4.shapes.add_textbox(Inches(1.0), Inches(2.4), Inches(5.2), Inches(4.2))
    tf_c1 = tx_c1_b.text_frame
    tf_c1.word_wrap = True
    for idx, b in enumerate(c1_bullets):
        p = tf_c1.paragraphs[0] if idx == 0 else tf_c1.add_paragraph()
        p.text = "• " + b
        p.font.name = "Segoe UI"
        p.font.size = Pt(13)
        p.font.color.rgb = C_SLATE_DARK
        p.space_before = Pt(12)

    # Stage 2 Card
    add_card(s4, Inches(6.9), Inches(1.6), Inches(5.6), Inches(5.2))
    top_c2 = s4.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, Inches(6.9), Inches(1.6), Inches(5.6), Inches(0.6))
    top_c2.fill.solid()
    top_c2.fill.fore_color.rgb = C_NAVY_DARK
    top_c2.line.fill.background()

    tx_c2 = s4.shapes.add_textbox(Inches(7.1), Inches(1.72), Inches(5.2), Inches(0.4))
    tx_c2.text_frame.paragraphs[0].text = "STAGE 2: Enterprise Production (Antigravity)"
    tx_c2.text_frame.paragraphs[0].font.name = "Segoe UI"
    tx_c2.text_frame.paragraphs[0].font.size = Pt(14)
    tx_c2.text_frame.paragraphs[0].font.bold = True
    tx_c2.text_frame.paragraphs[0].font.color.rgb = C_WHITE

    c2_bullets = [
        "UI/UX Re-Engineering: Modern Deep Blue corporate theme & DPI awareness.",
        "Dual-Tab Architecture: Live Scrutiny Workspace + Saved Database Register.",
        "Integrated SQLite Database: Relational schema, auto-save & manual sync.",
        "Multi-Criteria Search Engine: Query by LC No., Bank, Buyer, Amount & Dates.",
        "Record Lifecycle (CRUD): Full state reload and safe cascading deletion.",
        "Standalone Deployment: Bundled into a zero-dependency Windows .exe."
    ]
    tx_c2_b = s4.shapes.add_textbox(Inches(7.1), Inches(2.4), Inches(5.2), Inches(4.2))
    tf_c2 = tx_c2_b.text_frame
    tf_c2.word_wrap = True
    for idx, b in enumerate(c2_bullets):
        p = tf_c2.paragraphs[0] if idx == 0 else tf_c2.add_paragraph()
        p.text = "• " + b
        p.font.name = "Segoe UI"
        p.font.size = Pt(13)
        p.font.color.rgb = C_SLATE_DARK
        p.space_before = Pt(10)

    add_notes(s4, "This project showcases how modern software development leverages multi-agent AI collaboration. I began by obtaining the core algorithmic logic and parsing scripts from Claude. Then, I brought the project to Google Antigravity to build out the entire enterprise architecture: modern UI, persistent SQLite database, historical search, and deployment packaging.")

    # =========================================================================
    # SLIDE 5: Phase 1 — Foundational Engine Built by Claude
    # =========================================================================
    s5 = prs.slides.add_slide(blank_layout)
    add_header(s5, "Stage 1 Breakdown", "Phase 1: Algorithmic Logic & Field Extraction (Claude)")

    s5_boxes = [
        ("PDF Ingestion (pdf_extract.py)", "Extracts raw text streams from selectable PDF documents using pypdf. Validates file header integrity, normalizes page boundaries, and guards against malformed or password-protected files."),
        ("SWIFT MT700 Parser (lc_parser.py)", "Regex-driven parser handling both raw SWIFT tags (:20:, :31C:, :40A:, :46A:, :47A:, :71B:) and bank reprint conventions (F20:, F46A:). Accurately splits narrative conditions into atomic clauses."),
        ("Domain Models (models.py)", "Standardizes core dataclasses: ClausePoint (holding field tag, summary, rule citation, suggested verdict, user verdict, and remarks) and AnalysisResult (aggregating all clause points and document metadata)."),
        ("Rules Engine (rules_engine.py)", "Encodes UCP 600 provisions: checks date consistency (Art 14c - 21 day presentation window vs. expiry), amount tolerance percentages (Art 30), partial shipment/transshipment rules (Art 31 & 20), and banking fee allocations.")
    ]

    for idx, (title, desc) in enumerate(s5_boxes):
        left = Inches(0.8 + (idx % 2) * 5.95)
        top = Inches(1.6 + (idx // 2) * 2.65)
        width = Inches(5.75)
        height = Inches(2.4)

        add_card(s5, left, top, width, height)

        tx = s5.shapes.add_textbox(left + Inches(0.3), top + Inches(0.2), width - Inches(0.6), height - Inches(0.4))
        tf = tx.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.name = "Segoe UI"
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = C_NAVY_LIGHT

        p1 = tf.add_paragraph()
        p1.text = desc
        p1.font.name = "Segoe UI"
        p1.font.size = Pt(12)
        p1.font.color.rgb = C_SLATE_DARK
        p1.space_before = Pt(8)

    add_notes(s5, "In Stage 1 with Claude, we established the algorithmic backbone: accurately parsing notoriously difficult SWIFT message formats, standardizing date representations to DD/MM/YYYY, and executing first-pass validation checks against core UCP 600 rules.")

    # =========================================================================
    # SLIDE 6: Phase 2 — Frontend UI/UX Overhaul by Antigravity
    # =========================================================================
    s6 = prs.slides.add_slide(blank_layout)
    add_header(s6, "Stage 2 Breakdown", "Phase 2: Modern Enterprise Interface Design (Antigravity)")

    s6_pillars = [
        ("Enterprise Blue Visual Identity", [
            "Crafted a cohesive, executive palette: Corporate Deep Navy (#0F2942), Midnight Blue (#1E3A8A), and Royal Blue (#2563EB).",
            "Added Windows Per-Monitor DPI awareness via ctypes for crisp rendering on modern high-resolution displays.",
            "High-contrast visual hierarchy prevents visual fatigue during multi-hour document audits."
        ]),
        ("Dual-Tab Navigation System", [
            "Tab 1: Live Analysis & Workspace — dedicated to active document review, clause inspection, verdict toggling, and export generation.",
            "Tab 2: Saved Analyses & Database Register — provides an archive view, advanced search filters, and record management.",
            "Enables seamless switching between auditing new LCs and retrieving historical client files."
        ]),
        ("Live Real-Time KPI Dashboard", [
            "Status cards at the top of the interface track risk points live across 4 standard verdicts:",
            "  • In Order / Correct (Emerald Green)",
            "  • Requires Amendment (Crimson Red)",
            "  • Needs Clarification (Amber Orange)",
            "  • Informational / N/A (Slate Grey)",
            "Dynamic badge counts update instantly as the auditor toggles verdict radio buttons."
        ])
    ]

    for idx, (title, bullets) in enumerate(s6_pillars):
        left = Inches(0.8 + idx * 3.95)
        top = Inches(1.6)
        width = Inches(3.75)
        height = Inches(5.2)

        add_card(s6, left, top, width, height)

        tx = s6.shapes.add_textbox(left + Inches(0.25), top + Inches(0.25), width - Inches(0.5), height - Inches(0.5))
        tf = tx.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.name = "Segoe UI"
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = C_NAVY_LIGHT

        for b_idx, bullet in enumerate(bullets):
            p = tf.add_paragraph()
            p.text = bullet
            p.font.name = "Segoe UI"
            p.font.size = Pt(12)
            p.font.color.rgb = C_SLATE_DARK
            p.space_before = Pt(8)

    add_notes(s6, "When we moved to Antigravity, our focus shifted to professional usability. Antigravity designed a native, responsive desktop GUI. We implemented a dual-tab layout separating live working analysis from the historical repository, complete with a dynamic KPI dashboard that tracks risk metrics in real-time.")

    # =========================================================================
    # SLIDE 7: Interactive Clause Workspace & Split-Pane Inspector
    # =========================================================================
    s7 = prs.slides.add_slide(blank_layout)
    add_header(s7, "Auditor Workflow", "Interactive Clause Workspace & Split-Pane Inspector")

    # Left: Category Tabs
    add_card(s7, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    tx_c7_1 = s7.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.8))
    tf_c7_1 = tx_c7_1.text_frame
    tf_c7_1.word_wrap = True

    p = tf_c7_1.paragraphs[0]
    p.text = "4 Structured Core Sections & 8 Sub-Heads"
    p.font.name = "Segoe UI"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY_LIGHT

    cats = [
        "1. Main Summary: LC Number, Parties, Financial Value, Tenor, and Expiry/Shipment Dates.",
        "2. Goods & Services: Item descriptions, tolerance (+/-%), and unit rate controls.",
        "3. Documents Required (8 Dedicated Sub-Tabs):",
        "    • Transport Documents (Bills of Lading / LR)",
        "    • Certificate of Origin & Legalization",
        "    • Commercial Invoices & Packing Lists",
        "    • Bills of Exchange & Financial Instruments",
        "    • Certifications & Surveyor Inspection (Soft Clause Traps)",
        "    • Insurance Policies & Min 110% CIF Coverage",
        "    • Intimation & Telecommunication Advices",
        "    • Other Miscellaneous Documentary Requirements",
        "4. Bank Charges: Allocation of banking fees between Applicant and Beneficiary (Art 37c)."
    ]
    for c in cats:
        p = tf_c7_1.add_paragraph()
        p.text = c
        p.font.name = "Segoe UI"
        p.font.size = Pt(11)
        p.font.color.rgb = C_SLATE_DARK
        p.space_before = Pt(4)

    # Right: Split-Pane Inspector
    add_card(s7, Inches(6.9), Inches(1.6), Inches(5.6), Inches(5.2))
    tx_c7_2 = s7.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.2), Inches(4.8))
    tf_c7_2 = tx_c7_2.text_frame
    tf_c7_2.word_wrap = True

    p = tf_c7_2.paragraphs[0]
    p.text = "Split-Pane Clause Inspector & Auditor Overrides"
    p.font.name = "Segoe UI"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY_LIGHT

    inspect_bullets = [
        "Side-by-Side Clause Verification: Clicking 'View' on any clause immediately loads the exact raw source text in the resizable right-hand inspector.",
        "Zero Blind Spots: Drag the divider to resize the pane or click 'Show Full Document Text' to inspect surrounding context.",
        "One-Click Copy: Instant 'Copy to Clipboard' button allows auditors to copy tricky wording directly into emails or drafting tools.",
        "Full Verdict Override: Radio buttons permit the auditor to switch suggested verdicts (Correct, Requires Amendment, Needs Clarification, Informational).",
        "Custom Audit Trail: Enter tailored remarks in 'Your Remarks' — these notes flow directly into generated amendment letters and audit reports."
    ]
    for b in inspect_bullets:
        p = tf_c7_2.add_paragraph()
        p.text = "• " + b
        p.font.name = "Segoe UI"
        p.font.size = Pt(12)
        p.font.color.rgb = C_SLATE_DARK
        p.space_before = Pt(8)

    add_notes(s7, "Auditing an LC cannot be a black-box operation. Antigravity engineered an adjustable split-pane viewer. An auditor can click 'View' next to any clause to see the exact text extracted from the PDF, verify the rule engine's findings, toggle the verdict, and type custom notes that flow directly into audit reports.")

    # =========================================================================
    # SLIDE 8: Data Persistence Layer — SQLite Integration
    # =========================================================================
    s8 = prs.slides.add_slide(blank_layout)
    add_header(s8, "Database Architecture", "Zero-Configuration Portable Database Architecture (database.py)")

    # Left: Schema
    add_card(s8, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    tx_s8_1 = s8.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.8))
    tf_s8_1 = tx_s8_1.text_frame
    tf_s8_1.word_wrap = True

    p = tf_s8_1.paragraphs[0]
    p.text = "Relational SQLite Schema"
    p.font.name = "Segoe UI"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY_LIGHT

    schema_info = [
        "1. Master Table: lc_records",
        "    • Primary Key: id (Auto-increment)",
        "    • Identification: dc_number, lc_type, source_filename",
        "    • Parties: issuer_name, applicant_name, beneficiary_name",
        "    • Financials: currency, amount_text, amount_num",
        "    • Dates: issue_date, expiry_date, shipment_date",
        "    • Metrics: total_points, amendment_count, clarification_count, correct_count, full_text",
        "2. Child Table: lc_clause_records",
        "    • Relational FK: lc_id REFERENCES lc_records(id) ON DELETE CASCADE",
        "    • Content: section_name, subsection_name, field_tag, clause_title, summary_text, rule_notes",
        "    • State: suggested_verdict, user_verdict, user_remarks"
    ]
    for s in schema_info:
        p = tf_s8_1.add_paragraph()
        p.text = s
        p.font.name = "Segoe UI"
        p.font.size = Pt(11)
        p.font.color.rgb = C_SLATE_DARK
        p.space_before = Pt(4)

    # Right: Persistence Workflow
    add_card(s8, Inches(6.9), Inches(1.6), Inches(5.6), Inches(5.2))
    tx_s8_2 = s8.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.2), Inches(4.8))
    tf_s8_2 = tx_s8_2.text_frame
    tf_s8_2.word_wrap = True

    p = tf_s8_2.paragraphs[0]
    p.text = "Persistence Features & Workflow"
    p.font.name = "Segoe UI"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY_LIGHT

    features_s8 = [
        "Zero Configuration: SQLite is embedded directly. No server installation, configuration, or database admin required.",
        "Automatic Snapshot Logging: Analyzing an LC automatically commits a baseline record to lc_database.db.",
        "Manual Sync ('Save / Update Database'): Persists the auditor's customized remarks and verdict adjustments without overwriting original raw text.",
        "ACID Relational Integrity: Enforces PRAGMA foreign_keys = ON and transaction atomicity. If a record is deleted, all child clauses are cleanly purged.",
        "Portable Storage: The single database file (lc_database.db) travels with the application, allowing seamless backup and portability."
    ]
    for f in features_s8:
        p = tf_s8_2.add_paragraph()
        p.text = "• " + f
        p.font.name = "Segoe UI"
        p.font.size = Pt(12)
        p.font.color.rgb = C_SLATE_DARK
        p.space_before = Pt(8)

    add_notes(s8, "To make this a true enterprise tool, Antigravity built a complete persistence layer from scratch using SQLite. The database maintains full relational integrity. Every LC record is linked to its individual clause points, verdicts, and custom remarks, ensuring an immutable audit trail.")

    # =========================================================================
    # SLIDE 9: Multi-Criteria Search & Record Management
    # =========================================================================
    s9 = prs.slides.add_slide(blank_layout)
    add_header(s9, "Historical Repository", "Multi-Criteria Search & Historical Record Management")

    s9_cards = [
        ("Multi-Field Search Filters", [
            "Query past audits instantly across multiple business dimensions:",
            "  • Documentary Credit Number (SWIFT Field 20)",
            "  • Issuer Bank Name (Field 51A / 52A)",
            "  • Applicant / Buyer Name (Field 50)",
            "  • Beneficiary / Exporter Name (Field 59)",
            "  • Currency & Minimum Credit Amount",
            "  • Issue, Expiry, and Shipment Date Ranges",
            "Parameterized SQL queries guarantee high-speed search and guard against SQL injection."
        ]),
        ("One-Click Workspace Reload", [
            "Tab 2 displays all historical analyses in an interactive tabular grid with status badges.",
            "Selecting any archived record and clicking 'Open Selected Analysis' reloads the full state into Tab 1.",
            "Restores the exact document text, all category points, user verdict toggles, and customized remarks.",
            "Allows auditors to revisit an LC months later, update remarks, or re-export documents instantly."
        ]),
        ("Safe Record Deletion (CRUD)", [
            "Auditors can prune obsolete test records or completed client files directly from the UI.",
            "Clicking 'Delete Analysis' triggers a native Windows confirmation dialog preventing accidental loss.",
            "Foreign-key cascading deletion ensures all related clause points and remarks are wiped cleanly without leaving orphan data."
        ])
    ]

    for idx, (title, bullets) in enumerate(s9_cards):
        left = Inches(0.8 + idx * 3.95)
        top = Inches(1.6)
        width = Inches(3.75)
        height = Inches(5.2)

        add_card(s9, left, top, width, height)

        tx = s9.shapes.add_textbox(left + Inches(0.25), top + Inches(0.25), width - Inches(0.5), height - Inches(0.5))
        tf = tx.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.name = "Segoe UI"
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = C_NAVY_LIGHT

        for bullet in bullets:
            p = tf.add_paragraph()
            p.text = bullet
            p.font.name = "Segoe UI"
            p.font.size = Pt(12)
            p.font.color.rgb = C_SLATE_DARK
            p.space_before = Pt(8)

    add_notes(s9, "Auditors and trade desks handle dozens of LCs every month. Tab 2 provides an interactive historical search engine. You can search by LC number, issuing bank, or buyer name, reload an entire past audit into your workspace with one click, or safely delete archived records.")

    # =========================================================================
    # SLIDE 10: One-Click Document Generation & Amendment Drafter
    # =========================================================================
    s10 = prs.slides.add_slide(blank_layout)
    add_header(s10, "Reporting Suite", "One-Click Document Generation & Automated Amendment Drafter")

    docs_s10 = [
        ("Complete Working File (Word & PDF)", C_ROYAL_BLUE, [
            "Comprehensive, section-by-section working paper containing all 4 sections and 8 sub-heads.",
            "Includes color-coded verdict badges, full clause summaries, UCP 600 rule notes, and auditor remarks.",
            "Available in editable Word (.docx) format for internal file documentation and high-quality PDF (via ReportLab) for client submission."
        ]),
        ("Finalized Summary Sheet (Word)", C_GREEN, [
            "Executive sign-off sheet designed for CFOs, credit committees, or senior audit partners.",
            "Intelligently re-sorts every analyzed point into three dedicated review tables:",
            "  1. Points Confirmed Correct / In Order",
            "  2. Points Requiring Amendment",
            "  3. Other Remarks (Needs Clarification / Informational)"
        ]),
        ("Automated Amendment Letter (Word)", C_RED, [
            "Auto-generates a ready-to-send formal LC Amendment Request letter addressed to the Applicant / Issuing Bank.",
            "Automatically extracts Field 50 (Applicant) and Field 59 (Beneficiary) to populate letterhead and signature blocks.",
            "Lists every point marked 'Requires Amendment' alongside the auditor's specific requested modification."
        ])
    ]

    for idx, (title, accent_col, bullets) in enumerate(docs_s10):
        left = Inches(0.8 + idx * 3.95)
        top = Inches(1.6)
        width = Inches(3.75)
        height = Inches(5.2)

        add_card(s10, left, top, width, height)

        c_top = s10.shapes.add_shape(MSO_SHAPE.ROUNDED_RECTANGLE, left, top, width, Inches(0.45))
        c_top.fill.solid()
        c_top.fill.fore_color.rgb = accent_col
        c_top.line.fill.background()

        tx = s10.shapes.add_textbox(left + Inches(0.2), top + Inches(0.08), width - Inches(0.4), Inches(0.35))
        p = tx.text_frame.paragraphs[0]
        p.text = title.split(' (')[0]
        p.font.name = "Segoe UI"
        p.font.size = Pt(13)
        p.font.bold = True
        p.font.color.rgb = C_WHITE

        tx_b = s10.shapes.add_textbox(left + Inches(0.2), top + Inches(0.65), width - Inches(0.4), height - Inches(0.8))
        tf_b = tx_b.text_frame
        tf_b.word_wrap = True
        for b_idx, bullet in enumerate(bullets):
            pb = tf_b.paragraphs[0] if b_idx == 0 else tf_b.add_paragraph()
            pb.text = "• " + bullet
            pb.font.name = "Segoe UI"
            pb.font.size = Pt(12)
            pb.font.color.rgb = C_SLATE_DARK
            pb.space_before = Pt(10)

    add_notes(s10, "The true time-saver is the automated documentation engine. Instead of manually drafting emails or memos, a single click produces a complete PDF audit report, an executive sign-off summary, or an official, formal Amendment Request Letter ready to send to the issuing bank.")

    # =========================================================================
    # SLIDE 11: System Architecture & Data Pipeline
    # =========================================================================
    s11 = prs.slides.add_slide(blank_layout)
    add_header(s11, "Technical Architecture", "End-to-End System Architecture & Modular Data Flow")

    arch_steps = [
        ("1. Ingestion Layer", "pdf_extract.py", "Reads binary PDF streams via pypdf; extracts textual layout; validates document headers against corrupt/unsupported files."),
        ("2. Parsing Layer", "lc_parser.py", "Regex pattern matcher splits SWIFT MT700 tags (:20:, :31C:, :46A:, :47A:, etc.); normalizes dates to DD/MM/YYYY; isolates narrative clauses."),
        ("3. Rules Matrix", "rules_engine.py", "Applies UCP 600 compliance rules: checks presentation window (Art 14c), tolerance (Art 30), transshipment (Art 20), and charges (Art 37c)."),
        ("4. Presentation GUI", "main.py", "Modern Tkinter desktop UI with Windows DPI scaling, dual-tab layout, real-time KPI status badges, and split-pane clause inspector."),
        ("5. Relational Store", "database.py", "Embedded SQLite storage (lc_database.db) with foreign-key cascade enforcement, auto-saving snapshots, and multi-criteria search."),
        ("6. Document Exporter", "exporter.py", "ReportLab PDF canvas renderer and python-docx template engine generating working files, sign-off summaries, and amendment letters.")
    ]

    for idx, (title, module_name, desc) in enumerate(arch_steps):
        col = idx % 3
        row = idx // 3
        left = Inches(0.8 + col * 3.95)
        top = Inches(1.6 + row * 2.65)
        width = Inches(3.75)
        height = Inches(2.4)

        add_card(s11, left, top, width, height)

        tx = s11.shapes.add_textbox(left + Inches(0.25), top + Inches(0.2), width - Inches(0.5), height - Inches(0.4))
        tf = tx.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.name = "Segoe UI"
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = C_NAVY_LIGHT

        p_mod = tf.add_paragraph()
        p_mod.text = f"Module: {module_name}"
        p_mod.font.name = "Segoe UI"
        p_mod.font.size = Pt(11)
        p_mod.font.bold = True
        p_mod.font.color.rgb = C_ROYAL_BLUE
        p_mod.space_before = Pt(2)

        p1 = tf.add_paragraph()
        p1.text = desc
        p1.font.name = "Segoe UI"
        p1.font.size = Pt(11)
        p1.font.color.rgb = C_SLATE_DARK
        p1.space_before = Pt(6)

    add_notes(s11, "Here is the complete architectural pipeline. It is modular and decoupled. Raw PDF bytes enter through pypdf, pass into our SWIFT parser, flow through the UCP 600 rule matrix, render onto the Tkinter interface, sync with SQLite, and output into professional Word and PDF reports.")

    # =========================================================================
    # SLIDE 12: Standalone Deployment — Single-File .exe Packaging
    # =========================================================================
    s12 = prs.slides.add_slide(blank_layout)
    add_header(s12, "Deployment & Distribution", "Enterprise Distribution: Zero-Installation Executable (LC_Analyser.exe)")

    # Left: Comparison
    add_card(s12, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2))
    tx_s12_1 = s12.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.8))
    tf_s12_1 = tx_s12_1.text_frame
    tf_s12_1.word_wrap = True

    p = tf_s12_1.paragraphs[0]
    p.text = "Traditional Setup vs. Standalone .exe"
    p.font.name = "Segoe UI"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY_LIGHT

    comp_points = [
        "The Deployment Barrier: Non-technical users (Chartered Accountants, trade finance desks, and audit trainees) lack Python installations and command-line comfort.",
        "Traditional Python App:",
        "  • Requires Python 3.9+ runtime installation",
        "  • Requires pip install -r requirements.txt",
        "  • Fragile dependency clashes and environment issues",
        "  • Console window remains open during execution",
        "LC Analyser Solution (LC_Analyser.exe):",
        "  • Single, double-clickable 41.4 MB Windows binary",
        "  • Zero prerequisite software or installations",
        "  • Clean launch with --noconsole (no ugly terminal)",
        "  • Fully portable: runs from Desktop or USB drive"
    ]
    for cp in comp_points:
        p = tf_s12_1.add_paragraph()
        p.text = cp
        p.font.name = "Segoe UI"
        p.font.size = Pt(11)
        p.font.color.rgb = C_SLATE_DARK
        p.space_before = Pt(4)

    # Right: Packaging Technicals
    add_card(s12, Inches(6.9), Inches(1.6), Inches(5.6), Inches(5.2))
    tx_s12_2 = s12.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.2), Inches(4.8))
    tf_s12_2 = tx_s12_2.text_frame
    tf_s12_2.word_wrap = True

    p = tf_s12_2.paragraphs[0]
    p.text = "PyInstaller Engineering & Portable DB"
    p.font.name = "Segoe UI"
    p.font.size = Pt(14)
    p.font.bold = True
    p.font.color.rgb = C_NAVY_LIGHT

    pyi_points = [
        "Comprehensive Asset Bundling: PyInstaller bundles all Python bytecode, the Tkinter GUI engine, reportlab fonts, and python-docx document templates into a unified archive.",
        "Portable Database Anchoring: Solved the temporary folder (_MEIPASS) trap. If packaged naively, PyInstaller writes database changes to temp folders that are wiped on exit.",
        "Dynamic sys.frozen Detection: Modified database.py to anchor DEFAULT_DB_PATH adjacent to sys.executable. Saved LCs, remarks, and verdicts persist permanently next to the .exe.",
        "Zero Loss Portability: Users can move LC_Analyser.exe and lc_database.db together across PCs without losing historical audit archives."
    ]
    for pp in pyi_points:
        p = tf_s12_2.add_paragraph()
        p.text = "• " + pp
        p.font.name = "Segoe UI"
        p.font.size = Pt(12)
        p.font.color.rgb = C_SLATE_DARK
        p.space_before = Pt(8)

    add_notes(s12, "To ensure real-world adoption, we packaged the entire software into a standalone executable: LC_Analyser.exe. There is no need to install Python, configure libraries, or use a command prompt. A Chartered Accountant can simply copy the executable to their desktop and double-click to start auditing.")

    # =========================================================================
    # SLIDE 13: Enterprise Security & Zero-Hallucination Guarantee
    # =========================================================================
    s13 = prs.slides.add_slide(blank_layout)
    add_header(s13, "Security & Compliance", "Data Privacy, Banking Secrecy & Deterministic Precision")

    pillars_s13 = [
        ("100% Air-Gapped Data Privacy", [
            "Commercial Confidentiality: Letters of Credit contain proprietary business data: profit margins, counterparty names, and credit lines.",
            "Zero Cloud Transmission: The software runs 100% locally on the host machine. Not a single byte is sent to external cloud APIs or public LLMs.",
            "Regulatory Compliance: Compliant with banking secrecy mandates, GDPR, and Indian data privacy standards. Safe for tier-1 bank audits."
        ]),
        ("Deterministic Precision", [
            "Zero Hallucination Risk: Generative AI models can occasionally hallucinate dates or miss nuanced banking rules.",
            "Explicit Rule-Based Verification: Every check is grounded strictly in codified ICC UCP 600 articles and ISBP 745 standards.",
            "Legally Defensible: Financial institutions require deterministic, explainable verdicts that stand up in trade dispute arbitrations."
        ]),
        ("Audit Reproducibility", [
            "Consistent Results: Processing the same LC copy will always yield identical, reproducible compliance results.",
            "Transparent Logic: Every verdict is accompanied by explicit rule notes citing the exact UCP 600 article (e.g., Art 14c, Art 30).",
            "Human Oversight: Suggested verdicts act as a first-pass draft, leaving final sign-off in the qualified auditor's hands."
        ])
    ]

    for idx, (title, bullets) in enumerate(pillars_s13):
        left = Inches(0.8 + idx * 3.95)
        top = Inches(1.6)
        width = Inches(3.75)
        height = Inches(5.2)

        add_card(s13, left, top, width, height)

        tx = s13.shapes.add_textbox(left + Inches(0.25), top + Inches(0.25), width - Inches(0.5), height - Inches(0.5))
        tf = tx.text_frame
        tf.word_wrap = True

        p0 = tf.paragraphs[0]
        p0.text = title
        p0.font.name = "Segoe UI"
        p0.font.size = Pt(14)
        p0.font.bold = True
        p0.font.color.rgb = C_NAVY_LIGHT

        for bullet in bullets:
            p = tf.add_paragraph()
            p.text = bullet
            p.font.name = "Segoe UI"
            p.font.size = Pt(12)
            p.font.color.rgb = C_SLATE_DARK
            p.space_before = Pt(8)

    add_notes(s13, "In trade finance, confidentiality is paramount. You cannot upload a client's multi-million dollar LC to public cloud APIs. LC Analyser operates completely offline. Furthermore, because it relies on deterministic UCP 600 rules rather than generative guesses, it delivers 100% reproducible, zero-hallucination accuracy.")

    # =========================================================================
    # SLIDE 14: Practical Value & ROI for Chartered Accountants
    # =========================================================================
    s14 = prs.slides.add_slide(blank_layout)
    add_header(s14, "Professional Impact", "Practical Impact: Transforming Practice for CAs & Trade Desks")

    # Table Card
    add_card(s14, Inches(0.8), Inches(1.6), Inches(11.7), Inches(5.2))
    tx_s14 = s14.shapes.add_textbox(Inches(1.1), Inches(1.8), Inches(11.1), Inches(4.8))
    tf_s14 = tx_s14.text_frame
    tf_s14.word_wrap = True

    p0 = tf_s14.paragraphs[0]
    p0.text = "Comparative ROI: Traditional Manual Audit vs. LC Analyser"
    p0.font.name = "Segoe UI"
    p0.font.size = Pt(15)
    p0.font.bold = True
    p0.font.color.rgb = C_NAVY_LIGHT

    roi_rows = [
        ("Average Scrutiny Time", "3 to 4 hours of intense manual line-by-line reading", "Under 30 seconds for complete parsing and rule evaluation"),
        ("Risk of Overlooked Traps", "High due to human fatigue, complex SWIFT tags, and fine print", "Near zero: automated checklist checks all 30+ mandatory parameters"),
        ("Amendment Turnaround", "1 to 2 business days to draft, approve, and send amendment letters", "Instant: one-click generation of formal, ready-to-send Word letters"),
        ("Audit Documentation", "Disorganized emails, sticky notes, and loose paper folders", "Structured SQLite database archive + executive Word/PDF sign-off sheets"),
        ("Direct Cost Savings", "Exposure to $75-$150 discrepancy fees and heavy port demurrage", "Eliminates pre-presentation discrepancies before shipment occurs"),
        ("Professional Practice Value", "Low-margin compliance chore often rushed under time pressure", "High-value advisory service: pre-shipment LC vetting for export clients")
    ]

    for title, manual, tool in roi_rows:
        p = tf_s14.add_paragraph()
        p.text = f"• {title}:  {manual}  ➔  {tool}"
        p.font.name = "Segoe UI"
        p.font.size = Pt(12)
        p.font.color.rgb = C_SLATE_DARK
        p.space_before = Pt(8)

    add_notes(s14, "For Chartered Accountants, time is currency. LC Analyser collapses a 4-hour manual review into 30 seconds. It protects clients from severe financial penalties, enhances working capital velocity, and equips audit teams with a professional, standardized documentation trail.")

    # =========================================================================
    # SLIDE 15: Conclusion & Future Roadmap (Dark Background)
    # =========================================================================
    s15 = prs.slides.add_slide(blank_layout)
    bg15 = s15.shapes.add_shape(MSO_SHAPE.RECTANGLE, Inches(0), Inches(0), Inches(13.333), Inches(7.5))
    bg15.fill.solid()
    bg15.fill.fore_color.rgb = C_NAVY_DARK
    bg15.line.fill.background()

    add_header(s15, "Looking Ahead", "Project Conclusion & Future Strategic Roadmap", dark=True)

    # Left: Accomplishments
    add_card(s15, Inches(0.8), Inches(1.6), Inches(5.6), Inches(5.2), bg_color=C_NAVY_LIGHT, border_color=C_ROYAL_BLUE)
    tx_s15_1 = s15.shapes.add_textbox(Inches(1.0), Inches(1.8), Inches(5.2), Inches(4.8))
    tf_s15_1 = tx_s15_1.text_frame
    tf_s15_1.word_wrap = True

    p = tf_s15_1.paragraphs[0]
    p.text = "Key Project Achievements"
    p.font.name = "Segoe UI"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_WHITE

    achieve_bullets = [
        "Built a complete, production-grade desktop application solving a real-world trade finance challenge.",
        "Demonstrated the power of multi-agent AI pair programming: combining Claude's algorithmic prototyping with Antigravity's enterprise architecture.",
        "Engineered a zero-dependency standalone executable (LC_Analyser.exe) ready for instant deployment on any Windows workstation.",
        "Ensured 100% offline air-gapped data privacy and legally defensible UCP 600 compliance."
    ]
    for b in achieve_bullets:
        p = tf_s15_1.add_paragraph()
        p.text = "• " + b
        p.font.name = "Segoe UI"
        p.font.size = Pt(12)
        p.font.color.rgb = C_ICE_BLUE
        p.space_before = Pt(12)

    # Right: Roadmap
    add_card(s15, Inches(6.9), Inches(1.6), Inches(5.6), Inches(5.2), bg_color=C_NAVY_LIGHT, border_color=C_ROYAL_BLUE)
    tx_s15_2 = s15.shapes.add_textbox(Inches(7.1), Inches(1.8), Inches(5.2), Inches(4.8))
    tf_s15_2 = tx_s15_2.text_frame
    tf_s15_2.word_wrap = True

    p = tf_s15_2.paragraphs[0]
    p.text = "Future Strategic Roadmap"
    p.font.name = "Segoe UI"
    p.font.size = Pt(15)
    p.font.bold = True
    p.font.color.rgb = C_WHITE

    roadmap_bullets = [
        "OCR Integration: Integrating native Windows OCR and Tesseract to support scanned paper and image-only LCs.",
        "Hybrid Local LLM Layer: Adding an optional local/private LLM module for semantic interpretation of complex, ambiguous narrative conditions.",
        "Core Banking & ERP Connectors: Direct synchronization with SAP, Tally Prime, and bank SWIFT gateways.",
        "Expanded Rulebooks: Incorporating Incoterms 2020 rules, eUCP (electronic credits), and Standby Letters of Credit (ISP98)."
    ]
    for b in roadmap_bullets:
        p = tf_s15_2.add_paragraph()
        p.text = "• " + b
        p.font.name = "Segoe UI"
        p.font.size = Pt(12)
        p.font.color.rgb = C_ICE_BLUE
        p.space_before = Pt(12)

    p_final = tf_s15_2.add_paragraph()
    p_final.text = "Open for Live Demonstration & Questions!"
    p_final.font.name = "Segoe UI"
    p_final.font.size = Pt(14)
    p_final.font.bold = True
    p_final.font.color.rgb = C_WHITE
    p_final.space_before = Pt(24)

    add_notes(s15, "To conclude, LC Analyser demonstrates the incredible potential when Chartered Accountants leverage modern AI pair programming tools to solve real-world problems. We have moved from concept to an enterprise-ready software solution. Thank you for your time and attention. I would be delighted to demonstrate the software live and take any questions.")

    output_path = "presentation_slides.pptx"
    prs.save(output_path)
    _modernize_pptx(output_path)
    print(f"Presentation saved successfully to {os.path.abspath(output_path)}")

def _modernize_pptx(filepath):
    """Upgrades python-pptx legacy 2010 metadata to modern Office 16 widescreen format."""
    import zipfile
    with zipfile.ZipFile(filepath, 'r') as zin:
        items = {}
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'docProps/app.xml':
                xml = data.decode('utf-8')
                xml = xml.replace('Microsoft Macintosh PowerPoint', 'Microsoft PowerPoint')
                xml = xml.replace('<PresentationFormat>On-screen Show (4:3)</PresentationFormat>', '<PresentationFormat>Widescreen</PresentationFormat>')
                xml = xml.replace('<AppVersion>14.0000</AppVersion>', '<AppVersion>16.0000</AppVersion>')
                data = xml.encode('utf-8')
            elif item.filename == 'ppt/presentation.xml':
                xml = data.decode('utf-8')
                xml = xml.replace('type="screen4x3"', 'type="screen16x9"')
                data = xml.encode('utf-8')
            items[item.filename] = (item, data)

    temp_path = filepath + '.tmp'
    with zipfile.ZipFile(temp_path, 'w', compression=zipfile.ZIP_DEFLATED) as zout:
        for fname, (item, data) in items.items():
            zout.writestr(item, data)
    os.replace(temp_path, filepath)

if __name__ == "__main__":
    create_deck()


from conftest import SAMPLE_REPORT

from judgment_analyzer.prompts import DISCLAIMER_TEXT, REPORT_SECTIONS
from judgment_analyzer.response_parser import MISSING_TEXT, TAB_GROUPS, parse_report


def test_parses_all_sections():
    report = parse_report(SAMPLE_REPORT)
    assert report.missing_sections == []
    assert "Civil Appeal No. 123 of 2024" in report.sections[1]
    assert "### Appellant" in report.sections[5]
    assert "### Compliance considerations" in report.sections[14]
    assert "not legal advice" in report.disclaimer


def test_numbered_items_inside_sections_are_not_headings():
    md = "## 4. Issues Before the Court\n**1. Whether the notice was valid**\n1. Second issue\n## 8. Final Decision or Order\nDismissed."
    report = parse_report(md)
    assert "Whether the notice was valid" in report.sections[4]
    assert report.sections[8] == "Dismissed."
    assert 1 not in report.sections


def test_tolerates_heading_variations():
    md = (
        "Here is the analysis.\n"
        "# 1) CASE DETAILS\nCourt: X\n"
        "### Section 2: Executive summary\nShort.\n"
        "**3. Material Facts**\nFacts here.\n"
        "## Ratio Decidendi\nPrinciple.\n"
        "## 7. Courts Analysis & Reasoning\nReasoned.\n"
    )
    report = parse_report(md)
    assert report.sections[1] == "Court: X"
    assert report.sections[2] == "Short."
    assert report.sections[3] == "Facts here."
    assert report.sections[9] == "Principle."
    assert report.sections[7] == "Reasoned."
    assert report.preamble == "Here is the analysis."


def test_missing_sections_are_labelled_and_disclaimer_enforced():
    report = parse_report("## 2. Executive Summary\nOnly this.")
    assert 1 in report.missing_sections and 14 in report.missing_sections
    assert report.section_body(1) == MISSING_TEXT
    assert DISCLAIMER_TEXT in report.disclaimer


def test_unstructured_response_not_lost():
    report = parse_report("The model ignored the format entirely.")
    assert "ignored the format" in report.sections[2]


def test_code_fence_wrapper_removed():
    report = parse_report("```markdown\n" + SAMPLE_REPORT + "\n```")
    assert report.missing_sections == []


def test_tab_grouping_and_order():
    report = parse_report(SAMPLE_REPORT)
    points = report.tab_markdown("Points for Consideration")
    assert points.index("## 1. Points for Consideration") < points.index("## Disclaimer")
    assert "## 1. Key Insights From the Judgment" in report.tab_markdown("Key Insights")
    full = report.to_markdown()
    positions = [full.index(f"## {s.number}. {s.title}") for s in REPORT_SECTIONS]
    assert positions == sorted(positions)
    assert full.rstrip().endswith(report.disclaimer.rstrip())
    covered = sorted(n for nums in TAB_GROUPS.values() for n in nums)
    assert covered == list(range(1, 15))


def test_empty_input():
    report = parse_report("")
    assert len(report.missing_sections) == 14


def test_tab_headings_renumbered_from_one_and_body_unchanged():
    report = parse_report(SAMPLE_REPORT)
    for tab, numbers in TAB_GROUPS.items():
        md = report.tab_markdown(tab)
        for position, number in enumerate(numbers, start=1):
            section = REPORT_SECTIONS[number - 1]
            assert f"## {position}. {section.title}" in md
            assert report.section_body(number) in md  # content untouched
    summary = report.tab_markdown("Summary")
    assert "## 4. Final Decision or Order" in summary and "## 8." not in summary
    legal = report.tab_markdown("Legal Analysis")
    assert legal.startswith("## 1. Issues Before the Court") and "## 8. Practical Implications" in legal
    assert report.tab_markdown("Points for Consideration").startswith("## 1. Points for Consideration")
    # numbered items inside a section keep their original numbering
    assert "1. Whether section 9" in legal
    # the Full Report keeps the original 1-14 numbering
    assert "## 8. Final Decision or Order" in report.to_markdown()
    assert "## 14. Points for Consideration" in report.to_markdown()


def test_apply_edit_tab_and_full_report():
    import pytest
    from judgment_analyzer.response_parser import apply_edit

    report = parse_report(SAMPLE_REPORT)
    # Summary tab uses renumbered headings (1-4); titles decide the section.
    md = report.tab_markdown("Summary").replace("The appeal was allowed (p. 3).", "Appeal allowed in full.")
    assert apply_edit(report, "Summary", md) == [2]
    assert report.sections[2] == "Appeal allowed in full."
    assert "## 2. Executive Summary\n\nAppeal allowed in full." in report.to_markdown()

    # deleting a heading empties that section only
    legal = report.tab_markdown("Legal Analysis")
    start = legal.index("## 6. Obiter Dicta")
    end = legal.index("## 7. Important Precedents")
    assert apply_edit(report, "Legal Analysis", legal[:start] + legal[end:]) == [10]
    assert report.section_body(10).startswith("_Not provided")

    # disclaimer cannot lose the 'not legal advice' wording
    pts = report.tab_markdown("Points for Consideration").replace(report.disclaimer, "Anything.")
    apply_edit(report, "Points for Consideration", pts)
    assert "not legal advice" in report.disclaimer.lower()

    # full report edit
    full = report.to_markdown().replace("Civil Appeal No. 123 of 2024", "Civil Appeal No. 123/2024")
    assert apply_edit(report, "Full Report", full) == [1]

    # safety checks
    for bad in ("just some text", "intro line\n## 1. Case Details\nx", report.to_markdown()):
        with pytest.raises(ValueError):
            apply_edit(report, "Key Insights" if bad == report.to_markdown() else "Summary", bad)
    with pytest.raises(ValueError):
        apply_edit(report, "Summary", "## Something else\ntext")

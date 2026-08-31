"""
RACM Column Schema — LOCKED STRUCTURE
Every RACM row the AI generates must follow this exact 17-column shape,
in this exact order. No column may be added, removed, renamed, or reordered.
"""

RACM_COLUMNS = [
    "Sr. No.",
    "COSO Component",
    "Sub-Process Name",
    "Risk ID",
    "Risk Description",
    "Control Objective",
    "Control Activity",
    "Financial Statement Assertion",
    "Control Type",
    "Manual / Automated",
    "Control Frequency",
    "Design Deficiency (Yes/No)",
    "Design Deficiency Description",
    "Operating Effectiveness Deficiency (Yes/No)",
    "Operating Deficiency Description",
    "Process Owner (Department)",
    "Reference (COSO Principle)",
]


def get_schema_as_text():
    """
    Converts the column list into a numbered plain-text instruction block
    we can paste directly into the AI's prompt, so it knows exactly
    what shape to output every single time.
    """
    lines = ["Every RACM row MUST contain exactly these 17 fields, in this exact order:"]
    for i, col in enumerate(RACM_COLUMNS, start=1):
        lines.append(f"  {i}. {col}")
    return "\n".join(lines)


def get_empty_row_template():
    """
    Returns a dictionary with all 17 columns present but empty —
    useful later as a safety check that the AI didn't skip any field.
    """
    return {col: "" for col in RACM_COLUMNS}


# Quick self-test: only runs if you execute THIS file directly
if __name__ == "__main__":
    print(get_schema_as_text())
    print("\nEmpty row template check:")
    print(get_empty_row_template())
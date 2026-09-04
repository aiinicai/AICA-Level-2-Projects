"""
COSO Internal Control – Integrated Framework
5 Components x 17 Principles
This is the master checklist our AI will compare every client SOP against.
"""

COSO_FRAMEWORK = [
    {
        "component": "Control Environment",
        "principles": [
            {"number": 1, "title": "Demonstrates Commitment to Integrity and Ethical Values"},
            {"number": 2, "title": "Board Exercises Oversight Responsibility"},
            {"number": 3, "title": "Establishes Structure, Authority, and Responsibility"},
            {"number": 4, "title": "Demonstrates Commitment to Competence"},
            {"number": 5, "title": "Enforces Accountability"},
        ]
    },
    {
        "component": "Risk Assessment",
        "principles": [
            {"number": 6, "title": "Specifies Suitable Objectives"},
            {"number": 7, "title": "Identifies and Analyzes Risk"},
            {"number": 8, "title": "Assesses Fraud Risk"},
            {"number": 9, "title": "Identifies and Analyzes Significant Change"},
        ]
    },
    {
        "component": "Control Activities",
        "principles": [
            {"number": 10, "title": "Selects and Develops Control Activities"},
            {"number": 11, "title": "Selects and Develops General Controls over Technology"},
            {"number": 12, "title": "Deploys through Policies and Procedures"},
        ]
    },
    {
        "component": "Information and Communication",
        "principles": [
            {"number": 13, "title": "Uses Relevant Information"},
            {"number": 14, "title": "Communicates Internally"},
            {"number": 15, "title": "Communicates Externally"},
        ]
    },
    {
        "component": "Monitoring Activities",
        "principles": [
            {"number": 16, "title": "Conducts Ongoing and/or Separate Evaluations"},
            {"number": 17, "title": "Evaluates and Communicates Deficiencies"},
        ]
    },
]


def get_framework_as_text():
    """
    Converts the structured framework above into a plain-text checklist
    that we can paste directly into instructions sent to the AI.
    """
    lines = []
    for comp in COSO_FRAMEWORK:
        lines.append(f"\nCOSO COMPONENT: {comp['component']}")
        for p in comp["principles"]:
            lines.append(f"  Principle {p['number']}: {p['title']}")
    return "\n".join(lines)


# Quick self-test: only runs if you execute THIS file directly
if __name__ == "__main__":
    print(get_framework_as_text())
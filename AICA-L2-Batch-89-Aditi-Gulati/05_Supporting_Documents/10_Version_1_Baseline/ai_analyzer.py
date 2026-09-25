"""SurakshaScan v1 AI analyzer (reconstructed). Placeholder only."""


def analyze_policy_text(text):
    status = "Requires verification (AI check not yet connected)"
    items = (
        "Categories of data collected",
        "Purpose of collection stated",
        "Data principal rights explained",
        "Grievance/Board complaint route mentioned",
        "Children/parental consent addressed",
        "Retention period mentioned",
        "Third parties/vendors mentioned",
        "Security measures mentioned",
    )
    return {
        "source": "simulated",
        "checks": {item: status for item in items},
        "note": ("This is placeholder output. Connect a real API key to get "
                 "genuine AI analysis."),
    }


def suggest_policy_draft(institution_name):
    return {
        "source": "simulated",
        "draft_text": ("[Placeholder] A suggested privacy policy draft for "
                       + institution_name +
                       " would appear here once the AI API is connected."),
    }

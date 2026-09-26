"""
AuditVault - Visual Design System and Custom CSS
Deep Blue (#0A2540), Clean Slate/White (#F8FAFC), Gold/Amber (#F59E0B) and Teal (#0D9488).
Provides Light and Dark Mode theming, card styling, status badges, and vault branding.
"""

def get_custom_css(theme: str = "light") -> str:
    """Return tailored CSS according to light/dark mode preference."""
    is_dark = (theme == "dark")

    # Dynamic palette variables
    bg_primary = "#0F172A" if is_dark else "#F8FAFC"
    bg_card = "#1E293B" if is_dark else "#FFFFFF"
    text_primary = "#F8FAFC" if is_dark else "#0F172A"
    text_secondary = "#94A3B8" if is_dark else "#475569"
    border_color = "#334155" if is_dark else "#E2E8F0"
    sidebar_bg = "#0A192F" if is_dark else "#0A2540"
    sidebar_text = "#E2E8F0"
    card_shadow = "0 4px 6px -1px rgba(0, 0, 0, 0.3)" if is_dark else "0 4px 12px rgba(10, 37, 64, 0.06)"

    return f"""
    <style>
        /* Base typography & container */
        @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@400;500;600;700;800&family=JetBrains+Mono:wght@400;500&display=swap');

        html, body, [class*="css"] {{
            font-family: 'Plus Jakarta Sans', -apple-system, BlinkMacSystemFont, sans-serif;
            color: {text_primary};
        }}

        .stApp {{
            background-color: {bg_primary};
        }}

        /* Sidebar Styling */
        [data-testid="stSidebar"] {{
            background-color: {sidebar_bg} !important;
            border-right: 1px solid {border_color};
        }}

        [data-testid="stSidebar"] * {{
            color: {sidebar_text} !important;
        }}

        [data-testid="stSidebar"] .stButton > button {{
            background-color: rgba(255, 255, 255, 0.08) !important;
            color: #FFFFFF !important;
            border: 1px solid rgba(255, 255, 255, 0.15) !important;
            border-radius: 8px !important;
            font-weight: 500 !important;
            transition: all 0.2s ease !important;
        }}

        [data-testid="stSidebar"] .stButton > button:hover {{
            background-color: rgba(245, 158, 11, 0.2) !important;
            border-color: #F59E0B !important;
            color: #F59E0B !important;
        }}

        /* Vault Brand Header */
        .vault-brand-container {{
            display: flex;
            align-items: center;
            gap: 12px;
            padding: 12px 6px 20px 6px;
            border-bottom: 1px solid rgba(255, 255, 255, 0.12);
            margin-bottom: 16px;
        }}

        .vault-logo-icon {{
            width: 42px;
            height: 42px;
            background: linear-gradient(135deg, #1E3A8A 0%, #0A2540 100%);
            border: 2px solid #F59E0B;
            border-radius: 10px;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 22px;
            box-shadow: 0 4px 10px rgba(245, 158, 11, 0.25);
        }}

        .vault-title {{
            font-size: 22px;
            font-weight: 800;
            letter-spacing: -0.5px;
            color: #FFFFFF !important;
            line-height: 1.1;
        }}

        .vault-tagline {{
            font-size: 11px;
            font-weight: 500;
            color: #F59E0B !important;
            letter-spacing: 0.3px;
        }}

        /* Impersonation Banner */
        .impersonation-banner {{
            background: linear-gradient(90deg, #D97706 0%, #B45309 100%);
            color: #FFFFFF !important;
            padding: 12px 20px;
            border-radius: 8px;
            margin-bottom: 20px;
            display: flex;
            align-items: center;
            justify-content: space-between;
            font-weight: 600;
            box-shadow: 0 4px 12px rgba(217, 119, 6, 0.3);
        }}

        /* Modern UI Cards */
        .vault-card {{
            background-color: {bg_card};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 20px;
            margin-bottom: 16px;
            box-shadow: {card_shadow};
            transition: transform 0.2s ease, box-shadow 0.2s ease;
        }}

        .vault-card:hover {{
            box-shadow: 0 8px 20px rgba(10, 37, 64, 0.12);
        }}

        /* KPI Metric Cards */
        .metric-card {{
            background-color: {bg_card};
            border: 1px solid {border_color};
            border-radius: 12px;
            padding: 18px;
            box-shadow: {card_shadow};
            border-left: 4px solid #1E3A8A;
        }}

        .metric-card.gold {{
            border-left-color: #F59E0B;
        }}
        .metric-card.green {{
            border-left-color: #10B981;
        }}
        .metric-card.red {{
            border-left-color: #EF4444;
        }}
        .metric-card.teal {{
            border-left-color: #0D9488;
        }}

        .metric-title {{
            font-size: 12px;
            font-weight: 600;
            text-transform: uppercase;
            letter-spacing: 0.6px;
            color: {text_secondary};
            margin-bottom: 6px;
        }}

        .metric-value {{
            font-size: 26px;
            font-weight: 800;
            color: {text_primary};
            line-height: 1.1;
        }}

        .metric-subtext {{
            font-size: 12px;
            color: {text_secondary};
            margin-top: 4px;
        }}

        /* Status Badges */
        .badge {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            padding: 4px 10px;
            border-radius: 20px;
            font-size: 11px;
            font-weight: 700;
            text-transform: uppercase;
            letter-spacing: 0.5px;
        }}

        .badge-draft {{
            background-color: rgba(100, 116, 139, 0.15);
            color: #64748B;
            border: 1px solid rgba(100, 116, 139, 0.3);
        }}

        .badge-assigned {{
            background-color: rgba(13, 148, 136, 0.15);
            color: #0D9488;
            border: 1px solid rgba(13, 148, 136, 0.3);
        }}

        .badge-inprogress {{
            background-color: rgba(37, 99, 235, 0.15);
            color: #2563EB;
            border: 1px solid rgba(37, 99, 235, 0.3);
        }}

        .badge-underreview {{
            background-color: rgba(245, 158, 11, 0.15);
            color: #D97706;
            border: 1px solid rgba(245, 158, 11, 0.3);
        }}

        .badge-completed {{
            background-color: rgba(16, 185, 129, 0.15);
            color: #059669;
            border: 1px solid rgba(16, 185, 129, 0.3);
        }}

        .badge-overdue {{
            background-color: rgba(239, 68, 68, 0.15);
            color: #DC2626;
            border: 1px solid rgba(239, 68, 68, 0.3);
        }}

        .badge-locked {{
            background-color: rgba(79, 70, 229, 0.15);
            color: #4F46E5;
            border: 1px solid rgba(79, 70, 229, 0.3);
        }}

        /* Field Lock Box */
        .manager-locked-box {{
            background-color: rgba(100, 116, 139, 0.08);
            border: 1px dashed rgba(100, 116, 139, 0.3);
            border-radius: 8px;
            padding: 12px;
            margin: 8px 0;
            position: relative;
        }}

        .lock-indicator {{
            display: inline-flex;
            align-items: center;
            gap: 4px;
            font-size: 11px;
            color: #64748B;
            font-weight: 600;
            margin-bottom: 6px;
        }}

        /* Buttons & Actions */
        .stButton > button {{
            border-radius: 8px;
            font-weight: 600;
            transition: all 0.2s ease;
        }}

        /* Primary Action Buttons */
        div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"] {{
            background: linear-gradient(135deg, #0A2540 0%, #1E3A8A 100%) !important;
            color: #FFFFFF !important;
            border: none !important;
            box-shadow: 0 4px 10px rgba(10, 37, 64, 0.25) !important;
        }}

        div[data-testid="stHorizontalBlock"] .stButton > button[kind="primary"]:hover {{
            background: linear-gradient(135deg, #1E3A8A 0%, #2563EB 100%) !important;
            box-shadow: 0 6px 14px rgba(37, 99, 235, 0.35) !important;
        }}

        /* DataTables & Grids */
        .dataframe {{
            border: 1px solid {border_color} !important;
            border-radius: 8px !important;
        }}

        /* Tabs custom styling */
        .stTabs [data-baseweb="tab-list"] {{
            gap: 8px;
            background-color: transparent;
            border-bottom: 2px solid {border_color};
            padding-bottom: 4px;
        }}

        .stTabs [data-baseweb="tab"] {{
            height: 44px;
            border-radius: 8px 8px 0 0;
            font-weight: 600;
            font-size: 14px;
            color: {text_secondary};
            padding: 0 16px;
            background-color: transparent;
            border: none;
        }}

        .stTabs [aria-selected="true"] {{
            background-color: rgba(30, 58, 138, 0.1) !important;
            color: #1E3A8A !important;
            border-bottom: 3px solid #1E3A8A !important;
        }}

        /* Guided Tour Modal Card */
        .tour-card {{
            background: linear-gradient(135deg, #0A2540 0%, #1E3A8A 100%);
            color: #FFFFFF !important;
            border-radius: 12px;
            padding: 24px;
            margin-bottom: 20px;
            box-shadow: 0 10px 25px rgba(10, 37, 64, 0.3);
            border: 1px solid rgba(245, 158, 11, 0.4);
        }}

        .tour-step-badge {{
            background-color: #F59E0B;
            color: #0A2540;
            padding: 3px 8px;
            border-radius: 12px;
            font-size: 11px;
            font-weight: 800;
            margin-bottom: 8px;
            display: inline-block;
        }}
    </style>
    """


def render_brand_header() -> str:
    """Return HTML for the sidebar logo and title."""
    return """
    <div class="vault-brand-container">
        <div class="vault-logo-icon">🛡️</div>
        <div>
            <div class="vault-title">AuditVault</div>
            <div class="vault-tagline">EVERY ENGAGEMENT. SECURELY VAULTED.</div>
        </div>
    </div>
    """


def render_status_badge(status: str) -> str:
    """Return HTML badge for engagement/task status."""
    st_clean = (status or "Draft").lower().replace(" ", "")
    badge_class = "badge-draft"
    icon = "📝"

    if "progress" in st_clean:
        badge_class = "badge-inprogress"
        icon = "🔄"
    elif "review" in st_clean:
        badge_class = "badge-underreview"
        icon = "🔍"
    elif "completed" in st_clean:
        badge_class = "badge-completed"
        icon = "✅"
    elif "assigned" in st_clean:
        badge_class = "badge-assigned"
        icon = "👥"
    elif "overdue" in st_clean:
        badge_class = "badge-overdue"
        icon = "⚠️"
    elif "locked" in st_clean:
        badge_class = "badge-locked"
        icon = "🔒"

    return f'<span class="badge {badge_class}">{icon} {status}</span>'


def render_kpi_card(title: str, value: str, subtext: str = "", color_theme: str = "blue") -> str:
    """Return HTML metric card."""
    return f"""
    <div class="metric-card {color_theme}">
        <div class="metric-title">{title}</div>
        <div class="metric-value">{value}</div>
        <div class="metric-subtext">{subtext}</div>
    </div>
    """

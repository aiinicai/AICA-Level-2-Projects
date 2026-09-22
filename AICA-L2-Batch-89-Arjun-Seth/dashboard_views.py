# Copyright © 2026 Arjun Seth. All rights reserved. Viewable for ICAI evaluation only.
# No permission to copy, modify, redistribute or use commercially without written permission.
"""Dashboard presentation helpers: palette, greeting, KPI card markup and the Plotly charts.

No Streamlit import here, so the text/markup helpers can be tested on their own. Plotly is
imported only when a figure is actually built.
"""
import html
import math
from datetime import datetime

from core.formatting import format_approx, format_compact_money, format_money

# Colour palette
PALETTE = {
    "navy": "#0F1B3D",
    "primary": "#2F5BEA",
    "blue": "#2F80ED",
    "green": "#27AE60",
    "purple": "#8B5CF6",
    "orange": "#F2994A",
}
STATUS_COLORS = {
    "Draft": "#9AA5B1",
    "Rejected": "#D9480F",
    "Pending Review": "#F2B233",
    "Approved": "#27AE60",
    "Active": "#2F80ED",
    "Expired": "#B0B7C3",
    "Terminated": "#E5534B",
}
CLASSIFICATION_COLORS = {"Operating lease": "#2F80ED", "Finance lease": "#8B5CF6"}


def local_now(timezone_name=None) -> datetime:
    """The current time in the visitor's own time zone (an IANA name such as 'Asia/Kolkata'); the server's local time if the
    zone is unknown or unavailable (Windows needs the ``tzdata`` package for named zones), so it never fails."""
    if timezone_name:
        try:
            from zoneinfo import ZoneInfo

            return datetime.now(ZoneInfo(str(timezone_name)))
        except Exception:
            pass
    return datetime.now()


def greeting(now: datetime, name: str) -> str:
    """'Good Morning, Test' / 'Good Afternoon, ...' / 'Good Evening, ...' by the hour of ``now`` (before noon, noon to 5 pm, after)."""
    part = "Morning" if now.hour < 12 else "Afternoon" if now.hour < 17 else "Evening"
    first = (name or "").split()[0] if (name or "").strip() else ""
    return "Good {}{}".format(part, ", " + first if first else "")


ICONS = {  # simple 24x24 stroke icons (inline SVG, so they never depend on an emoji font)
    "file": '<path d="M6 3h8l4 4v14H6z"/><path d="M14 3v4h4M9 12h6M9 16h6"/>',
    "coins": '<ellipse cx="12" cy="6" rx="7" ry="3"/><path d="M5 6v6c0 1.7 3.1 3 7 3s7-1.3 7-3V6M5 12v6c0 1.7 3.1 3 7 3s7-1.3 7-3v-6"/>',
    "layers": '<path d="M12 3l9 5-9 5-9-5z"/><path d="M3 13l9 5 9-5"/>',
    "wallet": '<path d="M3 7h16a2 2 0 0 1 2 2v9a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z"/><path d="M3 7l2-3h12v3"/><circle cx="16.5" cy="13.5" r="1"/>',
}


def icon_svg(name: str) -> str:
    inner = ICONS.get(name)
    if not inner:
        return ""
    return (
        '<svg viewBox="0 0 24 24" fill="none" stroke="currentColor" stroke-width="2" stroke-linecap="round" '
        'stroke-linejoin="round">{}</svg>'.format(inner)
    )


def kpi_card_html(
    label: str,
    value: str,
    sub: str = "",
    accent: str = "#2F80ED",
    direction: str = "none",
    variant: str = "classic",
    icon: str = None,
    compact: bool = False,
    full: str = None,
) -> str:
    """One KPI card as HTML (all text escaped).

    ``direction``: up, down, flat or none (colours the change). ``variant``: classic (coloured top edge), modern
    (icon badge and a change pill) or pro (glowing edge, icon and pill). ``compact`` shrinks the value so long
    amounts stay on one line; ``full`` adds the exact amount in small type underneath.
    """
    if direction not in ("up", "down", "flat", "none"):
        direction = "none"
    if variant not in ("classic", "modern", "pro"):
        variant = "classic"
    badge = '<span class="kpi-icon">{}</span>'.format(icon_svg(icon)) if icon and variant != "classic" else ""
    if variant != "classic" and sub and direction in ("up", "down", "flat"):
        sub_html = '<span class="kpi-pill kpi-pill-{}">{}</span>'.format(direction, html.escape(sub))
    else:
        sub_html = html.escape(sub) if sub else "&nbsp;"
    return (
        '<div class="kpi-card kpi-card--{variant}{compact}" style="--kpi-accent: {accent};">'
        '<div class="kpi-top">{badge}<div class="kpi-label">{label}</div></div>'
        '<div class="kpi-value">{value}</div>'
        "{full}"
        '<div class="kpi-sub kpi-{direction}">{sub}</div>'
        "</div>"
    ).format(
        variant=variant,
        compact=" kpi-compact" if compact else "",
        accent=html.escape(accent, quote=True),
        badge=badge,
        label=html.escape(label),
        value=html.escape(value),
        full='<div class="kpi-full">{}</div>'.format(html.escape(full)) if full else "",
        sub=sub_html,
        direction=direction,
    )


def stat_values(value, currency: str, style: str) -> tuple:
    """(compact text, exact text or None) for a stat block: '₹ 13.5 lakh' and '₹ 13,46,000.00'.
    The exact text is left out when the compact one already is the exact amount."""
    compact, exact = format_compact_money(value, currency, style), format_money(value, currency, style)
    has_unit = any(unit in compact for unit in ("lakh", "crore", "million", "billion"))
    return compact, (exact if has_unit else None)


def ring_svg_html(percent: float, color: str, track: str, label: str, text_color: str = "#1A2233") -> str:
    """A ring gauge (SVG) showing ``percent`` (0-100) with the percentage in the middle and a label underneath."""
    percent = max(0.0, min(100.0, float(percent)))
    circumference = 2 * math.pi * 36
    return (
        '<div class="ring"><svg viewBox="0 0 100 100">'
        '<circle cx="50" cy="50" r="36" fill="none" stroke="{track}" stroke-width="10"/>'
        '<circle class="ring-value" cx="50" cy="50" r="36" fill="none" stroke="{color}" stroke-width="10" '
        'stroke-linecap="round" stroke-dasharray="{dash:.2f} {circ:.2f}" transform="rotate(-90 50 50)" style="color:{color};"/>'
        '<text x="50" y="56" text-anchor="middle" font-size="18" font-weight="700" fill="{text}">{pct:.0f}%</text>'
        '</svg><div class="ring-label">{label}</div></div>'
    ).format(
        track=html.escape(track, quote=True),
        color=html.escape(color, quote=True),
        dash=circumference * percent / 100.0,
        circ=circumference,
        text=html.escape(text_color, quote=True),
        pct=percent,
        label=html.escape(label),
    )


def trend_sub(trend: dict) -> str:
    """'▲ +2.3% vs last month' (or the 'nothing to compare' text) for a KPI card's sub-line."""
    return "{} {}".format(trend["arrow"], trend["text"]).strip()


# --------------------------------------------------------------------------- #
# charts
# --------------------------------------------------------------------------- #
def _style_figure(figure, palette):
    """Text, legend and grid colours for a theme (charts stay transparent so the card shows through)."""
    if not palette:
        return figure
    figure.update_layout(font={"color": palette["text"]}, legend_font_color=palette["text"])
    figure.update_xaxes(gridcolor=palette["border"], zerolinecolor=palette["border"])
    figure.update_yaxes(gridcolor=palette["border"], zerolinecolor=palette["border"])
    return figure


def donut_figure(items: list, colors: dict, center_label: str = "Leases", palette: dict = None):
    """A donut (hole 0.6) with the total in the middle and a legend showing each count and percentage.

    ``items``: [(name, count)]. With no counts at all, an empty ring saying "No data" is returned.
    """
    import plotly.graph_objects as go

    total = sum(count for _, count in items)
    figure = go.Figure()
    if total <= 0:
        figure.add_trace(go.Pie(labels=["No data"], values=[1], hole=0.6, marker={"colors": ["#E6EBF5"]}, textinfo="none", hoverinfo="skip", showlegend=False))
        figure.add_annotation(text="No data", x=0.5, y=0.5, showarrow=False, font={"size": 18, "color": "#9AA5B1"})
    else:
        legend_labels = ["{}  -  {} ({:.0%})".format(name, count, count / total) for name, count in items]
        figure.add_trace(
            go.Pie(
                labels=legend_labels,
                values=[count for _, count in items],
                hole=0.6,
                sort=False,
                direction="clockwise",
                marker={"colors": [colors.get(name, "#9AA5B1") for name, _ in items]},
                textinfo="none",
                hovertemplate="%{label}<extra></extra>",
            )
        )
        figure.add_annotation(text="<b>{}</b><br>{}".format(total, center_label), x=0.5, y=0.5, showarrow=False, font={"size": 22})
    figure.update_layout(
        height=340,
        margin={"l": 10, "r": 10, "t": 10, "b": 10},
        legend={"orientation": "h", "yanchor": "top", "y": -0.02},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return _style_figure(figure, palette)


def maturity_figure(buckets: list, currency: str, style: str, color: str = None, palette: dict = None):
    """Vertical bars: undiscounted payments due in each of the next years, with a value label on every bar."""
    import plotly.graph_objects as go

    color = color or (palette["bar"] if palette else "#2F80ED")
    values = [bucket["value"] for bucket in buckets]
    figure = go.Figure(
        go.Bar(
            x=[bucket["label"] for bucket in buckets],
            y=values,
            text=[format_approx(value, style) if value else "" for value in values],
            textposition="outside",
            customdata=[
                "{}<br>{}".format(bucket["range"], format_money(bucket["value"], currency, style)) for bucket in buckets
            ],
            hovertemplate="%{customdata}<extra></extra>",
            marker_color=color,
        )
    )
    figure.update_yaxes(showticklabels=False, showgrid=False, range=[0, (max(values) if values and max(values) > 0 else 1) * 1.25])
    figure.update_xaxes(showgrid=False)
    figure.update_layout(
        height=340,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
        showlegend=False,
    )
    return _style_figure(figure, palette)


def status_pill_html(status: str) -> str:
    """A colour-coded status badge (text escaped; an unknown status is grey)."""
    color = STATUS_COLORS.get(status, "#9AA5B1")
    return '<span class="status-pill" style="color:{c}; background:{c}22; border:1px solid {c}55;">{t}</span>'.format(
        c=html.escape(color, quote=True), t=html.escape(str(status))
    )


def interest_principal_figure(
    monthly, currency: str, style: str, crossover_month=None, palette: dict = None, height: int = 340
):
    """Two lines over the coming months: Interest Expense and Principal Repayment (summed over the portfolio).

    ``monthly``: the DataFrame from ``core.dashboard.monthly_portfolio``. If ``crossover_month`` is given, a dotted
    marker shows where principal overtakes interest. Nothing is forced: the lines are the data.
    """
    import plotly.graph_objects as go

    months = list(monthly["month"])
    figure = go.Figure()
    for column, name, color in (
        ("interest", "Interest Expense", palette["interest"] if palette else PALETTE["orange"]),
        ("principal", "Principal Repayment", palette["principal"] if palette else PALETTE["blue"]),
    ):
        values = [float(v) for v in monthly[column]]
        figure.add_trace(
            go.Scatter(
                x=months,
                y=values,
                mode="lines",
                name=name,
                line={"color": color, "width": 3},
                customdata=[format_money(v, currency, style) for v in values],
                hovertemplate="%{x|%b %Y}<br>" + name + ": %{customdata}<extra></extra>",
            )
        )
    if crossover_month is not None:
        figure.add_shape(
            type="line", x0=crossover_month, x1=crossover_month, y0=0, y1=1, xref="x", yref="paper",
            line={"color": "#8A93A5", "width": 1, "dash": "dot"},
        )
        figure.add_annotation(
            x=crossover_month, y=1, xref="x", yref="paper", text="Principal overtakes interest", showarrow=False,
            yanchor="bottom", font={"size": 11, "color": "#5B6577"},
        )
    figure.update_xaxes(tickformat="%b %Y", showgrid=False)
    figure.update_yaxes(tickformat="~s", gridcolor="#E6EBF5")
    figure.update_layout(
        height=height,
        margin={"l": 10, "r": 10, "t": 30, "b": 10},
        legend={"orientation": "h", "yanchor": "bottom", "y": 1.02, "xanchor": "left", "x": 0},
        paper_bgcolor="rgba(0,0,0,0)",
        plot_bgcolor="rgba(0,0,0,0)",
    )
    return _style_figure(figure, palette)

"""
Netcrafty AI - Modern 12-Month Advertising Product-Costing & AI Diagnostic Software.
A colorful, engaging, full-featured Python dashboard with automated risk detection
and Google Gemini Generative AI financial auditing.
"""

import streamlit as st
import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
from io import BytesIO
import time

from engine import (
    NetcraftyModel, CHANNELS, CHANNEL_NAMES, CHANNEL_COLORS,
    LINKED_FIELDS, METRICS_CONFIG
)
from ai_analyzer import (
    HeuristicDiagnostic, GeminiAdvisor,
    load_api_config, save_api_config, test_gemini_connection,
    SUPPORTED_MODELS
)
from presets import PRESETS, apply_preset

# Page Configuration
st.set_page_config(
    page_title="Netcrafty AI · Advertising Costing & AI Diagnostic",
    page_icon="⚡",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Custom High-End Modern Styling (Glassmorphism + Vibrant Accents)
st.markdown("""
<style>
    @import url('https://fonts.googleapis.com/css2?family=Plus+Jakarta+Sans:wght@300;400;500;600;700;800&display=swap');

    html, body, [class*="css"] {
        font-family: 'Plus Jakarta Sans', system-ui, sans-serif;
    }

    /* Gradient Header Hero */
    .hero-banner {
        background: linear-gradient(135deg, #0F172A 0%, #1E1B4B 40%, #312E81 100%);
        border: 1px solid rgba(255, 255, 255, 0.1);
        border-radius: 16px;
        padding: 24px 28px;
        color: white;
        margin-bottom: 24px;
        box-shadow: 0 10px 30px rgba(15, 23, 42, 0.15);
    }
    .hero-banner h1 {
        font-size: 28px;
        font-weight: 800;
        margin: 0;
        letter-spacing: -0.5px;
        background: linear-gradient(90deg, #FFFFFF, #93C5FD, #C084FC);
        -webkit-background-clip: text;
        -webkit-text-fill-color: transparent;
    }
    .hero-banner p {
        color: #94A3B8;
        font-size: 14px;
        margin: 6px 0 0 0;
    }

    /* KPI Cards */
    .kpi-container {
        display: grid;
        grid-template-columns: repeat(auto-fit, minmax(200px, 1fr));
        gap: 14px;
        margin-bottom: 24px;
    }
    .kpi-card {
        background: white;
        border-radius: 14px;
        padding: 18px 20px;
        border: 1px solid #E2E8F0;
        box-shadow: 0 4px 12px rgba(0, 0, 0, 0.03);
        transition: transform 0.2s ease, box-shadow 0.2s ease;
    }
    .kpi-card:hover {
        transform: translateY(-2px);
        box-shadow: 0 8px 24px rgba(0, 0, 0, 0.08);
    }
    .kpi-label {
        font-size: 12px;
        font-weight: 600;
        color: #64748B;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }
    .kpi-value {
        font-size: 24px;
        font-weight: 800;
        color: #0F172A;
        margin-top: 6px;
    }
    .kpi-sub {
        font-size: 12px;
        color: #64748B;
        margin-top: 4px;
    }
    .positive-text { color: #10B981 !important; }
    .negative-text { color: #EF4444 !important; }

    /* Alert Cards */
    .alert-card {
        border-radius: 12px;
        padding: 16px 18px;
        margin-bottom: 14px;
        border-left: 5px solid;
    }
    .alert-critical {
        background: #FEF2F2;
        border-color: #EF4444;
        color: #991B1B;
    }
    .alert-warning {
        background: #FFFBEB;
        border-color: #F59E0B;
        color: #92400E;
    }
    .alert-opportunity {
        background: #ECFDF5;
        border-color: #10B981;
        color: #065F46;
    }
    .alert-card h4 {
        margin: 0 0 6px 0;
        font-size: 15px;
        font-weight: 700;
        display: flex;
        align-items: center;
        gap: 8px;
    }
    .alert-card p {
        margin: 4px 0 0 0;
        font-size: 13px;
        line-height: 1.5;
    }
    .alert-action {
        margin-top: 8px !important;
        font-weight: 600;
        font-size: 13px !important;
    }

    /* Channel Badges */
    .channel-badge {
        display: inline-block;
        padding: 3px 8px;
        border-radius: 6px;
        font-size: 11px;
        font-weight: 700;
        color: white;
    }
    .badge-wc { background: #4F46E5; }
    .badge-wp { background: #06B6D4; }
    .badge-ac { background: #10B981; }
    .badge-ap { background: #F59E0B; }

    /* Calculation Formula Tag */
    .calc-tag {
        font-size: 11px;
        background: #F1F5F9;
        color: #475569;
        border-radius: 4px;
        padding: 2px 6px;
        font-family: monospace;
    }

    /* Clean Streamlit tab styling */
    .stTabs [data-baseweb="tab-list"] {
        gap: 8px;
        background: #F8FAFC;
        padding: 6px;
        border-radius: 12px;
        border: 1px solid #E2E8F0;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 8px;
        font-weight: 600;
        padding: 8px 16px;
        color: #475569;
    }
    .stTabs [aria-selected="true"] {
        background: white !important;
        color: #4F46E5 !important;
        box-shadow: 0 2px 8px rgba(0, 0, 0, 0.05);
    }
</style>
""", unsafe_allow_html=True)


# Initialize Session State
if "model" not in st.session_state:
    st.session_state.model = NetcraftyModel()

if "api_config" not in st.session_state:
    st.session_state.api_config = load_api_config()

if "chat_history" not in st.session_state:
    st.session_state.chat_history = []

if "ai_audit_result" not in st.session_state:
    st.session_state.ai_audit_result = None

model: NetcraftyModel = st.session_state.model


# Top Hero Banner
st.markdown("""
<div class="hero-banner">
    <div style="display: flex; justify-content: space-between; align-items: center; flex-wrap: wrap; gap: 12px;">
        <div>
            <h1>⚡ Netcrafty AI · Financial & Advertising Costing Studio</h1>
            <p>12-Month Multi-Channel Unit Economics (Website COD/Prepaid & WhatsApp COD/Prepaid) with AI Health Diagnostics</p>
        </div>
        <div style="display: flex; gap: 10px;">
            <span class="channel-badge badge-wc">Website COD</span>
            <span class="channel-badge badge-wp">Website Prepaid</span>
            <span class="channel-badge badge-ac">WhatsApp COD</span>
            <span class="channel-badge badge-ap">WhatsApp Prepaid</span>
        </div>
    </div>
</div>
""", unsafe_allow_html=True)


# Compute Model Results
results = model.compute()
kpi = model.get_kpi_summary()
diagnostics = HeuristicDiagnostic.analyze(model)


# Quick Top Metrics Bar
col1, col2, col3, col4, col5 = st.columns(5)
with col1:
    st.metric(
        label="Total Delivered Orders",
        value=f"{kpi['total_delivered']:,.0f}",
        help="Total successfully delivered orders across all 4 channels in 12 months"
    )
with col2:
    st.metric(
        label="Recognized Revenue",
        value=f"₹{kpi['total_revenue']:,.0f}",
        help="Gross sales minus current deferred plus prior deferred"
    )
with col3:
    st.metric(
        label="Total 12-Month Costs",
        value=f"₹{kpi['total_costs']:,.0f}",
        help="Sum of advertising, staffing, product, shipping, packing, and allocated shared fixed costs"
    )
with col4:
    net_val = kpi["net_profit"]
    st.metric(
        label="Cumulative Net P&L",
        value=f"₹{net_val:,.0f}",
        delta=f"{kpi['profit_margin']:.1f}% Margin",
        delta_color="normal" if net_val >= 0 else "inverse",
        help="12-month net profit or loss"
    )
with col5:
    first_month = kpi["first_positive_month"]
    be_label = f"Month {first_month}" if first_month else "Not in 12 Mo"
    score_val = diagnostics["score"]
    st.metric(
        label="AI Health Score / Break-even",
        value=f"{score_val}/100",
        delta=f"Break-even: {be_label}",
        delta_color="normal" if first_month and first_month <= 6 else "inverse"
    )

st.markdown("<div style='height: 12px;'></div>", unsafe_allow_html=True)


# Main Tabs
tab_dash, tab_inputs, tab_matrix, tab_ai, tab_api = st.tabs([
    "📊 Executive Dashboard",
    "🎛️ Scenario & Month Studio",
    "📑 12-Month Detailed Matrix",
    "🤖 AI Financial Doctor",
    "🔑 API Integration & AI Setup"
])


# ==========================================
# TAB 1: EXECUTIVE DASHBOARD
# ==========================================
with tab_dash:
    st.subheader("📈 12-Month Performance & Unit Economics Trajectory")

    # Chart Row 1: Cumulative Profit Curve & Monthly Revenue vs Cost
    c1, c2 = st.columns([1.1, 1])

    with c1:
        months_labels = [r["month_label"] for r in results]
        cum_profits = [r["cumulative_profit"] for r in results]
        monthly_profits = [r["month_profit"] for r in results]

        fig_cum = go.Figure()
        # Zero line
        fig_cum.add_hline(y=0, line_dash="dash", line_color="#94A3B8", annotation_text="Break-even Zero Line")
        
        # Cumulative P&L Area
        fig_cum.add_trace(go.Scatter(
            x=months_labels,
            y=cum_profits,
            mode='lines+markers',
            name='Cumulative P&L',
            line=dict(color='#4F46E5', width=3),
            fill='tozeroy',
            fillcolor='rgba(79, 70, 229, 0.1)',
            marker=dict(size=8)
        ))

        # Monthly Profit Bar
        fig_cum.add_trace(go.Bar(
            x=months_labels,
            y=monthly_profits,
            name='Monthly Net Profit',
            marker_color=['#10B981' if p >= 0 else '#EF4444' for p in monthly_profits],
            opacity=0.6
        ))

        fig_cum.update_layout(
            title="Cumulative & Monthly Profit / Loss (₹)",
            margin=dict(l=10, r=10, t=40, b=10),
            height=360,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_cum, use_container_width=True)

    with c2:
        revs = [r["month_revenue"] for r in results]
        costs = [r["month_costs"] for r in results]

        fig_rev_cost = go.Figure()
        fig_rev_cost.add_trace(go.Bar(
            x=months_labels,
            y=revs,
            name='Recognized Revenue',
            marker_color='#10B981'
        ))
        fig_rev_cost.add_trace(go.Bar(
            x=months_labels,
            y=costs,
            name='Total Costs',
            marker_color='#F43F5E'
        ))

        fig_rev_cost.update_layout(
            barmode='group',
            title="Monthly Revenue vs. Total Costs (₹)",
            margin=dict(l=10, r=10, t=40, b=10),
            height=360,
            hovermode="x unified",
            legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
        )
        st.plotly_chart(fig_rev_cost, use_container_width=True)

    # Chart Row 2: Cost Breakdown & Channel Funnel
    c3, c4 = st.columns([1, 1.1])

    with c3:
        # 12-month Cost Composition Donut
        cost_categories = {
            "Advertising": sum(sum(r["rows"][c]["ads"] for c in CHANNELS) for r in results),
            "Product & Transit": sum(sum(r["rows"][c]["product"] for c in CHANNELS) for r in results),
            "Postage & Transit": sum(sum(r["rows"][c]["postage"] for c in CHANNELS) for r in results),
            "Packing": sum(sum(r["rows"][c]["packing"] for c in CHANNELS) for r in results),
            "Staffing": sum(sum(r["rows"][c]["staffing"] for c in CHANNELS) for r in results),
            "Agency Fee": sum(sum(r["rows"][c]["agency"] for c in CHANNELS) for r in results),
            "Server Cost": sum(sum(r["rows"][c]["server"] for c in CHANNELS) for r in results),
            "Influencer Cost": sum(sum(r["rows"][c]["influencer"] for c in CHANNELS) for r in results)
        }
        df_costs = pd.DataFrame(list(cost_categories.items()), columns=["Cost Head", "Amount"])
        df_costs = df_costs[df_costs["Amount"] > 0]

        fig_donut = px.pie(
            df_costs,
            names="Cost Head",
            values="Amount",
            hole=0.45,
            title="12-Month Total Cost Composition",
            color_discrete_sequence=px.colors.qualitative.Bold
        )
        fig_donut.update_traces(textposition='inside', textinfo='percent+label')
        fig_donut.update_layout(
            margin=dict(l=10, r=10, t=40, b=10),
            height=340,
            showlegend=False
        )
        st.plotly_chart(fig_donut, use_container_width=True)

    with c4:
        # Channel Funnel Comparison
        funnel_data = []
        for c in CHANNELS:
            tot_leads = sum(r["rows"][c]["volume"] for r in results)
            tot_conf = sum(r["rows"][c]["confirmed"] for r in results)
            tot_deliv = sum(r["rows"][c]["delivered"] for r in results)
            if tot_leads > 0:
                funnel_data.append({"Channel": CHANNEL_NAMES[c], "Stage": "1. Leads", "Count": tot_leads})
                funnel_data.append({"Channel": CHANNEL_NAMES[c], "Stage": "2. Confirmed", "Count": tot_conf})
                funnel_data.append({"Channel": CHANNEL_NAMES[c], "Stage": "3. Delivered", "Count": tot_deliv})

        if funnel_data:
            df_funnel = pd.DataFrame(funnel_data)
            fig_funnel = px.bar(
                df_funnel,
                x="Stage",
                y="Count",
                color="Channel",
                barmode="group",
                title="Conversion Funnel by Channel (Total 12 Months)",
                color_discrete_map={CHANNEL_NAMES[k]: CHANNEL_COLORS[k] for k in CHANNELS}
            )
            fig_funnel.update_layout(
                margin=dict(l=10, r=10, t=40, b=10),
                height=340,
                legend=dict(orientation="h", yanchor="bottom", y=1.02, xanchor="right", x=1)
            )
            st.plotly_chart(fig_funnel, use_container_width=True)
        else:
            st.info("No leads entered yet across channels.")


# ==========================================
# TAB 2: SCENARIO & MONTH STUDIO
# ==========================================
with tab_inputs:
    st.subheader("🎛️ Scenario Modeling & Monthly Assumptions Studio")

    # Preset Scenario Selector
    pcol1, pcol2, pcol3 = st.columns([2, 1, 1])
    with pcol1:
        selected_preset = st.selectbox(
            "🚀 Quick Load Scenario Preset:",
            options=list(PRESETS.keys()),
            help="Select a pre-built industry model to quickly see how it performs"
        )
        st.caption(PRESETS[selected_preset]["description"])

    with pcol2:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Apply Scenario to Model", use_container_width=True, type="primary"):
            apply_preset(model, selected_preset)
            st.success(f"Loaded '{selected_preset}' across all 12 months!")
            st.rerun()

    with pcol3:
        st.markdown("<div style='height: 28px;'></div>", unsafe_allow_html=True)
        if st.button("Apply Month 1 to All Months", use_container_width=True):
            model.cascade_month1_to_all()
            st.success("Copied Month 1 assumptions across all months!")
            st.rerun()

    st.markdown("---")

    # Month Selector
    month_options = [f"Month {i + 1}" for i in range(len(model.months))]
    chosen_month_str = st.radio("Select Month to Inspect & Edit:", month_options, horizontal=True)
    m_idx = month_options.index(chosen_month_str)
    cur_m = model.months[m_idx]

    if m_idx > 0:
        st.info(f"💡 You are editing **Month {m_idx + 1}**. Values shown in light blue are overridden from Month 1. Editing fields here will override Month 1 for this month.")

    # 1. Lead Splits Section
    st.markdown("#### 1. Lead Generation & Prepaid Splits")
    sc1, sc2 = st.columns(2)

    with sc1:
        st.markdown("##### 🌐 Website Sourcing")
        web_tot = st.number_input(
            "Website Total Leads",
            min_value=0.0,
            value=float(cur_m.splits["web"]["total"]),
            step=50.0,
            key=f"split_web_total_{m_idx}"
        )
        web_prep = st.slider(
            "Website Prepaid Leads %",
            min_value=0.0,
            max_value=100.0,
            value=float(cur_m.splits["web"]["prepaid"]),
            step=1.0,
            key=f"split_web_prepaid_{m_idx}"
        )
        if (web_tot != cur_m.splits["web"]["total"]) or (web_prep != cur_m.splits["web"]["prepaid"]):
            model.set_value(m_idx, "splitweb", "total", web_tot)
            model.set_value(m_idx, "splitweb", "prepaid", web_prep)
            st.rerun()

        # Dynamic Status Display
        wc_vol = cur_m.channels["wc"]["volume"]
        wp_vol = cur_m.channels["wp"]["volume"]
        wc_del = wc_vol * cur_m.channels["wc"]["confirm"] * cur_m.channels["wc"]["delivery"] / 10000.0
        wp_del = wp_vol * cur_m.channels["wp"]["confirm"] * cur_m.channels["wp"]["delivery"] / 10000.0
        st.markdown(f"""
        <div style="background: #EEF2FF; border: 1px solid #C7D2FE; border-radius: 8px; padding: 10px; font-size: 13px;">
            COD Leads: <strong>{wc_vol:,.1f}</strong> ({100 - web_prep:.0f}%) · Prepaid Leads: <strong>{wp_vol:,.1f}</strong> ({web_prep:.0f}%)<br>
            COD Delivered: <strong>{wc_del:,.1f}</strong> · Prepaid Delivered: <strong>{wp_del:,.1f}</strong> · <strong>Total Website Delivered: {wc_del + wp_del:,.1f}</strong>
        </div>
        """, unsafe_allow_html=True)

    with sc2:
        st.markdown("##### 💬 WhatsApp Sourcing")
        wa_tot = st.number_input(
            "WhatsApp Total Leads",
            min_value=0.0,
            value=float(cur_m.splits["wa"]["total"]),
            step=50.0,
            key=f"split_wa_total_{m_idx}"
        )
        wa_prep = st.slider(
            "WhatsApp Prepaid Leads %",
            min_value=0.0,
            max_value=100.0,
            value=float(cur_m.splits["wa"]["prepaid"]),
            step=1.0,
            key=f"split_wa_prepaid_{m_idx}"
        )
        if (wa_tot != cur_m.splits["wa"]["total"]) or (wa_prep != cur_m.splits["wa"]["prepaid"]):
            model.set_value(m_idx, "splitwa", "total", wa_tot)
            model.set_value(m_idx, "splitwa", "prepaid", wa_prep)
            st.rerun()

        # Dynamic Status Display
        ac_vol = cur_m.channels["ac"]["volume"]
        ap_vol = cur_m.channels["ap"]["volume"]
        ac_del = ac_vol * cur_m.channels["ac"]["confirm"] * cur_m.channels["ac"]["delivery"] / 10000.0
        ap_del = ap_vol * cur_m.channels["ap"]["confirm"] * cur_m.channels["ap"]["delivery"] / 10000.0
        st.markdown(f"""
        <div style="background: #ECFDF5; border: 1px solid #A7F3D0; border-radius: 8px; padding: 10px; font-size: 13px;">
            COD Leads: <strong>{ac_vol:,.1f}</strong> ({100 - wa_prep:.0f}%) · Prepaid Leads: <strong>{ap_vol:,.1f}</strong> ({wa_prep:.0f}%)<br>
            COD Delivered: <strong>{ac_del:,.1f}</strong> · Prepaid Delivered: <strong>{ap_del:,.1f}</strong> · <strong>Total WhatsApp Delivered: {ac_del + ap_del:,.1f}</strong>
        </div>
        """, unsafe_allow_html=True)

    st.markdown("---")

    # 2. Channel Economics Grid
    st.markdown("#### 2. Channel Unit Economics & Conversion Assumptions")
    
    col_wc, col_wp = st.columns(2)
    with col_wc:
        st.markdown("##### 🌐 Website COD (Primary Settings)")
        wc = cur_m.channels["wc"]
        wc_confirm = st.number_input("Confirmation % of Leads", 0.0, 100.0, float(wc["confirm"]), 1.0, key=f"wc_confirm_{m_idx}")
        wc_delivery = st.number_input("Delivery % of Confirmed Orders", 0.0, 100.0, float(wc["delivery"]), 1.0, key=f"wc_delivery_{m_idx}")
        wc_ad = st.number_input("Advertisement Cost Per Lead (₹)", 0.0, 10000.0, float(wc["ad"]), 10.0, key=f"wc_ad_{m_idx}")
        wc_product = st.number_input("Product Cost (₹)", 0.0, 50000.0, float(wc["product"]), 10.0, key=f"wc_prod_{m_idx}")
        wc_packing = st.number_input("Packing Cost / Confirmed Order (₹)", 0.0, 5000.0, float(wc["packing"]), 5.0, key=f"wc_pack_{m_idx}")
        wc_postage = st.number_input("Postage Cost / Confirmed Order (₹)", 0.0, 10000.0, float(wc["postage"]), 5.0, key=f"wc_post_{m_idx}")
        wc_price = st.number_input("Sale Price / Delivered Order (₹)", 0.0, 100000.0, float(wc["price"]), 50.0, key=f"wc_price_{m_idx}")
        wc_salary = st.number_input("Employee Monthly Salary (₹)", 0.0, 500000.0, float(wc["salary"]), 1000.0, key=f"wc_sal_{m_idx}")
        wc_cap = st.number_input("Leads Handled Per Employee", 1.0, 10000.0, float(wc["capacity"]), 10.0, key=f"wc_cap_{m_idx}")
        wc_uplift = st.number_input("Extra Product & Postage in Transit %", 0.0, 100.0, float(wc["uplift"]), 1.0, key=f"wc_up_{m_idx}")

        # Update if changed
        for k, v in [("confirm", wc_confirm), ("delivery", wc_delivery), ("ad", wc_ad), ("product", wc_product),
                     ("packing", wc_packing), ("postage", wc_postage), ("price", wc_price), ("salary", wc_salary),
                     ("capacity", wc_cap), ("uplift", wc_uplift)]:
            if v != wc[k]:
                model.set_value(m_idx, "wc", k, v)
                st.rerun()

    with col_wp:
        st.markdown("##### 💳 Website Prepaid (Linked to COD)")
        wp = cur_m.channels["wp"]
        st.caption("🔒 *Gray fields are synchronized to Website COD for the same month*")
        st.text_input("Confirmation % (Locked to COD)", f"{wp['confirm']}%", disabled=True)
        wp_delivery = st.number_input("Delivery % of Confirmed Orders (Editable)", 0.0, 100.0, float(wp["delivery"]), 1.0, key=f"wp_del_{m_idx}")
        st.text_input("Ad Cost Per Lead (Locked to COD)", f"₹{wp['ad']:,.0f}", disabled=True)
        st.text_input("Product Cost (Locked to COD)", f"₹{wp['product']:,.0f}", disabled=True)
        st.text_input("Packing Cost (Locked to COD)", f"₹{wp['packing']:,.0f}", disabled=True)
        st.text_input("Postage Cost (Locked to COD)", f"₹{wp['postage']:,.0f}", disabled=True)
        wp_price = st.number_input("Sale Price / Delivered Order (Editable)", 0.0, 100000.0, float(wp["price"]), 50.0, key=f"wp_price_{m_idx}")
        st.text_input("Employee Salary (Locked to COD)", f"₹{wp['salary']:,.0f}", disabled=True)
        st.text_input("Capacity Per Employee (Locked to COD)", f"{wp['capacity']:,.0f} leads", disabled=True)
        st.text_input("Transit Uplift % (Locked to COD)", f"{wp['uplift']}%", disabled=True)

        if wp_delivery != wp["delivery"]:
            model.set_value(m_idx, "wp", "delivery", wp_delivery)
            st.rerun()
        if wp_price != wp["price"]:
            model.set_value(m_idx, "wp", "price", wp_price)
            st.rerun()

    st.markdown("---")
    col_ac, col_ap = st.columns(2)
    with col_ac:
        st.markdown("##### 💬 WhatsApp COD (Primary Settings)")
        ac = cur_m.channels["ac"]
        ac_confirm = st.number_input("Confirmation % of Leads", 0.0, 100.0, float(ac["confirm"]), 1.0, key=f"ac_confirm_{m_idx}")
        ac_delivery = st.number_input("Delivery % of Confirmed Orders", 0.0, 100.0, float(ac["delivery"]), 1.0, key=f"ac_delivery_{m_idx}")
        ac_ad = st.number_input("Advertisement Cost Per Lead (₹)", 0.0, 10000.0, float(ac["ad"]), 5.0, key=f"ac_ad_{m_idx}")
        ac_product = st.number_input("Product Cost (₹)", 0.0, 50000.0, float(ac["product"]), 10.0, key=f"ac_prod_{m_idx}")
        ac_packing = st.number_input("Packing Cost / Confirmed Order (₹)", 0.0, 5000.0, float(ac["packing"]), 5.0, key=f"ac_pack_{m_idx}")
        ac_postage = st.number_input("Postage Cost / Confirmed Order (₹)", 0.0, 10000.0, float(ac["postage"]), 5.0, key=f"ac_post_{m_idx}")
        ac_price = st.number_input("Sale Price / Delivered Order (₹)", 0.0, 100000.0, float(ac["price"]), 50.0, key=f"ac_price_{m_idx}")
        ac_salary = st.number_input("Employee Monthly Salary (₹)", 0.0, 500000.0, float(ac["salary"]), 1000.0, key=f"ac_sal_{m_idx}")
        ac_cap = st.number_input("Leads Handled Per Employee", 1.0, 10000.0, float(ac["capacity"]), 10.0, key=f"ac_cap_{m_idx}")
        ac_uplift = st.number_input("Extra Product & Postage in Transit %", 0.0, 100.0, float(ac["uplift"]), 1.0, key=f"ac_up_{m_idx}")

        for k, v in [("confirm", ac_confirm), ("delivery", ac_delivery), ("ad", ac_ad), ("product", ac_product),
                     ("packing", ac_packing), ("postage", ac_postage), ("price", ac_price), ("salary", ac_salary),
                     ("capacity", ac_cap), ("uplift", ac_uplift)]:
            if v != ac[k]:
                model.set_value(m_idx, "ac", k, v)
                st.rerun()

    with col_ap:
        st.markdown("##### ⚡ WhatsApp Prepaid (Linked to COD)")
        ap = cur_m.channels["ap"]
        st.caption("🔒 *Gray fields are synchronized to WhatsApp COD for the same month*")
        st.text_input("Confirmation % (Locked to WA COD)", f"{ap['confirm']}%", disabled=True)
        ap_delivery = st.number_input("Delivery % of Confirmed Orders (Editable)", 0.0, 100.0, float(ap["delivery"]), 1.0, key=f"ap_del_{m_idx}")
        st.text_input("Ad Cost Per Lead (Locked to WA COD)", f"₹{ap['ad']:,.0f}", disabled=True)
        st.text_input("Product Cost (Locked to WA COD)", f"₹{ap['product']:,.0f}", disabled=True)
        st.text_input("Packing Cost (Locked to WA COD)", f"₹{ap['packing']:,.0f}", disabled=True)
        st.text_input("Postage Cost (Locked to WA COD)", f"₹{ap['postage']:,.0f}", disabled=True)
        ap_price = st.number_input("Sale Price / Delivered Order (Editable)", 0.0, 100000.0, float(ap["price"]), 50.0, key=f"ap_price_{m_idx}")
        st.text_input("Employee Salary (Locked to WA COD)", f"₹{ap['salary']:,.0f}", disabled=True)
        st.text_input("Capacity Per Employee (Locked to WA COD)", f"{ap['capacity']:,.0f} leads", disabled=True)
        st.text_input("Transit Uplift % (Locked to WA COD)", f"{ap['uplift']}%", disabled=True)

        if ap_delivery != ap["delivery"]:
            model.set_value(m_idx, "ap", "delivery", ap_delivery)
            st.rerun()
        if ap_price != ap["price"]:
            model.set_value(m_idx, "ap", "price", ap_price)
            st.rerun()

    st.markdown("---")
    # 3. Shared Overhead
    st.markdown("#### 3. Shared Fixed Overhead (Allocated Across Channels by Deliveries)")
    sh1, sh2, sh3 = st.columns(3)
    with sh1:
        sh_agency = st.number_input("Agency Fee (₹)", 0.0, 2000000.0, float(cur_m.shared["agency"]), 10000.0, key=f"sh_ag_{m_idx}")
    with sh2:
        sh_server = st.number_input("Server & Tech Infrastructure (₹)", 0.0, 1000000.0, float(cur_m.shared["server"]), 5000.0, key=f"sh_srv_{m_idx}")
    with sh3:
        sh_influencer = st.number_input("Influencer & Brand Marketing (₹)", 0.0, 2000000.0, float(cur_m.shared["influencer"]), 10000.0, key=f"sh_inf_{m_idx}")

    for k, v in [("agency", sh_agency), ("server", sh_server), ("influencer", sh_influencer)]:
        if v != cur_m.shared[k]:
            model.set_value(m_idx, "shared", k, v)
            st.rerun()


# ==========================================
# TAB 3: 12-MONTH DETAILED MATRIX
# ==========================================
with tab_matrix:
    st.subheader("📑 12-Month Four-Channel Financial Matrix")
    st.caption("Matches the Netcrafty HTML dashboard layout with side-by-side mathematical formulas and values.")

    m_filter = st.selectbox(
        "Display Month View:",
        options=["All Months Summary"] + [f"Month {i + 1}" for i in range(len(model.months))]
    )

    if m_filter == "All Months Summary":
        # Render high level month-by-month table
        summary_rows = []
        for r in results:
            summary_rows.append({
                "Month": r["month_label"],
                "Website Leads": r["rows"]["wc"]["volume"] + r["rows"]["wp"]["volume"],
                "WhatsApp Leads": r["rows"]["ac"]["volume"] + r["rows"]["ap"]["volume"],
                "Delivered Orders": f"{r['all_delivered']:,.1f}",
                "Web Staff": r["web_staff"],
                "WA Staff": r["wa_staff"],
                "Gross Sales": f"₹{sum(r['rows'][c]['gross'] for c in CHANNELS):,.0f}",
                "Recognized Rev": f"₹{r['month_revenue']:,.0f}",
                "Total Costs": f"₹{r['month_costs']:,.0f}",
                "Monthly P&L": f"₹{r['month_profit']:,.0f}",
                "Cumulative P&L": f"₹{r['cumulative_profit']:,.0f}"
            })
        df_sum = pd.DataFrame(summary_rows)
        st.dataframe(df_sum, use_container_width=True, hide_index=True)

    else:
        # Render single month detailed matrix
        view_idx = int(m_filter.replace("Month ", "")) - 1
        r = results[view_idx]
        cur_m = model.months[view_idx]

        matrix_data = []
        for item in METRICS_CONFIG:
            if item[0] == "group":
                matrix_data.append({
                    "Metric": f"🔹 {item[1]}",
                    "WC Calc": "", "WC Value": "",
                    "WP Calc": "", "WP Value": "",
                    "AC Calc": "", "AC Value": "",
                    "AP Calc": "", "AP Value": "",
                    "Total": ""
                })
                continue

            k, label, ftype = item
            row_dict = {"Metric": label}
            tot_val = 0.0

            for c in CHANNELS:
                val = r["rows"][c][k] if k != "cumulative" else 0.0
                tot_val += val
                calc_str = model.explain(k, c, r["rows"][c], view_idx)
                row_dict[f"{c.upper()} Calc"] = calc_str

                if ftype == "money":
                    row_dict[f"{c.upper()} Value"] = f"₹{val:,.1f}"
                else:
                    row_dict[f"{c.upper()} Value"] = f"{val:,.1f}"

            if k == "cumulative":
                row_dict["Total"] = f"₹{r['cumulative_profit']:,.1f}"
            elif k == "profit":
                row_dict["Total"] = f"₹{r['month_profit']:,.1f}"
            elif k == "received":
                row_dict["Total"] = f"₹{r['month_revenue']:,.1f}"
            elif k == "costs":
                row_dict["Total"] = f"₹{r['month_costs']:,.1f}"
            else:
                row_dict["Total"] = f"₹{tot_val:,.1f}" if ftype == "money" else f"{tot_val:,.1f}"

            matrix_data.append({
                "Metric": row_dict["Metric"],
                "Website COD (Calc)": row_dict.get("WC Calc", ""),
                "Website COD (Val)": row_dict.get("WC Value", ""),
                "Website Prepaid (Calc)": row_dict.get("WP Calc", ""),
                "Website Prepaid (Val)": row_dict.get("WP Value", ""),
                "WhatsApp COD (Calc)": row_dict.get("AC Calc", ""),
                "WhatsApp COD (Val)": row_dict.get("AC Value", ""),
                "WhatsApp Prepaid (Calc)": row_dict.get("AP Calc", ""),
                "WhatsApp Prepaid (Val)": row_dict.get("AP Value", ""),
                "Total": row_dict.get("Total", "")
            })

        df_month_matrix = pd.DataFrame(matrix_data)
        st.dataframe(df_month_matrix, use_container_width=True, hide_index=True)

    # Export Buttons (CSV and Excel)
    st.markdown("#### 📥 Export Financial Models")
    exp_col1, exp_col2 = st.columns(2)
    with exp_col1:
        full_df = model.export_dataframe()
        csv_bytes = full_df.to_csv(index=False).encode('utf-8')
        st.download_button(
            label="Download Complete 12-Month Detailed CSV",
            data=csv_bytes,
            file_name="netcrafty_12month_costing_detailed.csv",
            mime="text/csv",
            use_container_width=True
        )
    with exp_col2:
        output = BytesIO()
        with pd.ExcelWriter(output, engine='openpyxl') as writer:
            full_df.to_excel(writer, index=False, sheet_name="12MonthCosting")
        excel_data = output.getvalue()
        st.download_button(
            label="Download Styled Excel Workbook (.xlsx)",
            data=excel_data,
            file_name="netcrafty_financial_model.xlsx",
            mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            use_container_width=True
        )


# ==========================================
# TAB 4: AI FINANCIAL DOCTOR
# ==========================================
with tab_ai:
    st.subheader("🤖 AI Financial Doctor: Figures to Take Care Of")
    st.markdown("Automated algorithmic audit and generative AI strategic diagnosis to safeguard your profit margins.")

    score = diagnostics["score"]
    score_color = "#10B981" if score >= 75 else "#F59E0B" if score >= 50 else "#EF4444"
    st.markdown(f"""
    <div style="background: white; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px; margin-bottom: 20px;">
        <div style="display: flex; justify-content: space-between; align-items: center;">
            <div>
                <span style="font-size: 13px; font-weight: 700; color: #64748B; text-transform: uppercase;">Financial Viability Score</span>
                <h2 style="margin: 4px 0 0 0; color: {score_color}; font-size: 32px; font-weight: 800;">{score} / 100</h2>
            </div>
            <div style="text-align: right;">
                <span style="font-size: 12px; color: #64748B;">Identified Risk Points</span><br>
                <strong style="color: #EF4444; font-size: 16px;">{len(diagnostics['red_flags'])} Red Flags</strong> · 
                <strong style="color: #F59E0B; font-size: 16px;">{len(diagnostics['warnings'])} Warnings</strong>
            </div>
        </div>
        <div style="width: 100%; background: #E2E8F0; height: 10px; border-radius: 5px; margin-top: 12px; overflow: hidden;">
            <div style="width: {score}%; background: {score_color}; height: 100%; border-radius: 5px;"></div>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # 1. Critical Red Flags Section
    st.markdown("### 🚨 Critical Red Flags (Must Fix Immediately)")
    if diagnostics["red_flags"]:
        for flag in diagnostics["red_flags"]:
            st.markdown(f"""
            <div class="alert-card alert-critical">
                <h4>🔴 {flag['figure']} · {flag['metric']} ({flag['impact']})</h4>
                <p>{flag['detail']}</p>
                <p class="alert-action">🎯 Recommended Action: {flag['recommendation']}</p>
            </div>
            """, unsafe_allow_html=True)
    else:
        st.success("No critical red flags detected! Unit economics look healthy.")

    # 2. Warnings Section
    if diagnostics["warnings"]:
        st.markdown("### ⚠️ Key Operational Warnings (Figures to Monitor)")
        for warn in diagnostics["warnings"]:
            st.markdown(f"""
            <div class="alert-card alert-warning">
                <h4>🟡 {warn['figure']} · {warn['metric']} ({warn['impact']})</h4>
                <p>{warn['detail']}</p>
                <p class="alert-action">💡 Optimization Tip: {warn['recommendation']}</p>
            </div>
            """, unsafe_allow_html=True)

    # 3. Opportunities Section
    if diagnostics["opportunities"]:
        st.markdown("### 💡 High-Leverage Growth Opportunities")
        for opp in diagnostics["opportunities"]:
            st.markdown(f"""
            <div class="alert-card alert-opportunity">
                <h4>🟢 {opp['figure']} · {opp['metric']} ({opp['impact']})</h4>
                <p>{opp['detail']}</p>
                <p class="alert-action">🚀 Strategic Move: {opp['action']}</p>
            </div>
            """, unsafe_allow_html=True)

    st.markdown("---")

    # 4. Deep Generative AI Audit (Gemini)
    st.markdown("### 🧠 Live Generative AI Strategic Audit (Google Gemini)")
    api_key_stored = st.session_state.api_config.get("api_key", "").strip()

    gcol1, gcol2 = st.columns([1.5, 1])
    with gcol1:
        if not api_key_stored:
            st.warning("⚠️ No Gemini API Key configured. Please go to the **🔑 API Integration** tab to enter your key and unlock deep AI CFO reasoning.")
        else:
            st.info(f"Connected Model: **{st.session_state.api_config.get('model', 'gemini-3.8-flash')}** · Persona: **{st.session_state.api_config.get('persona', 'D2C CFO')}**")

    with gcol2:
        if st.button("🚀 Run Deep AI Financial Health Audit", type="primary", use_container_width=True, disabled=not api_key_stored):
            with st.spinner("Analyzing unit economics and generating CFO action roadmap..."):
                advisor = GeminiAdvisor(
                    api_key=api_key_stored,
                    model_name=st.session_state.api_config.get("model", "gemini-3.8-flash"),
                    persona=st.session_state.api_config.get("persona")
                )
                audit_text = advisor.generate_audit(model, diagnostics)
                st.session_state.ai_audit_result = audit_text

    if st.session_state.ai_audit_result:
        st.markdown("#### 📋 AI CFO Comprehensive Audit Report")
        st.markdown(st.session_state.ai_audit_result)

    st.markdown("---")

    # 5. Interactive Follow-Up Chat with AI CFO
    st.markdown("### 💬 Ask the AI Financial Advisor About Your Numbers")
    st.caption("Ask specific questions like *'How can I make Month 2 profitable?'* or *'What happens if I increase sale price by ₹150?'*")

    for msg in st.session_state.chat_history:
        with st.chat_message(msg["role"]):
            st.write(msg["content"])

    user_query = st.chat_input("Ask a financial question about your model...")
    if user_query:
        st.session_state.chat_history.append({"role": "user", "content": user_query})
        with st.chat_message("user"):
            st.write(user_query)

        if not api_key_stored:
            reply = "Please configure your Gemini API Key in the 'API Integration' tab to enable live interactive Q&A."
        else:
            with st.spinner("Thinking..."):
                advisor = GeminiAdvisor(
                    api_key=api_key_stored,
                    model_name=st.session_state.api_config.get("model", "gemini-3.8-flash")
                )
                reply = advisor.answer_question(user_query, model, st.session_state.chat_history)

        st.session_state.chat_history.append({"role": "assistant", "content": reply})
        with st.chat_message("assistant"):
            st.write(reply)


# ==========================================
# TAB 5: API INTEGRATION & AI SETUP
# ==========================================
with tab_api:
    st.subheader("🔑 API Key Integration & AI Engine Configuration")
    st.markdown("""
    Configure your **Google Gemini API Key** to enable live AI Financial Audits, intelligent figure monitoring,
    and interactive Q&A. Your key is stored securely in your local environment.
    """)

    cfg_col1, cfg_col2 = st.columns([1.2, 1])

    with cfg_col1:
        current_key = st.session_state.api_config.get("api_key", "")
        entered_key = st.text_input(
            "Google Gemini API Key",
            value=current_key,
            type="password",
            placeholder="AIzaSy...",
            help="Get your free or paid Gemini API key from https://aistudio.google.com"
        )

        model_options = SUPPORTED_MODELS + ["Custom Model Name..."]
        current_model = st.session_state.api_config.get("model", "gemini-3.8-flash")
        default_idx = model_options.index(current_model) if current_model in model_options else 0

        selected_model_option = st.selectbox(
            "Gemini Model",
            options=model_options,
            index=default_idx,
            help="Gemini 3.8 Flash is Google's active recommended model for fast, high-accuracy financial reasoning."
        )

        if selected_model_option == "Custom Model Name...":
            active_model = st.text_input("Enter Custom Model Identifier", value=current_model)
        else:
            active_model = selected_model_option

        selected_persona = st.selectbox(
            "AI Advisor Persona & Tone",
            options=[
                "Aggressive D2C Growth CFO & Profitability Auditor",
                "Conservative Risk-Averse E-Commerce Auditor",
                "Venture Capital & Unit Economics Specialist",
                "Tactical Media Buyer & Funnel Optimizer"
            ],
            index=0
        )

        btn_c1, btn_c2 = st.columns(2)
        with btn_c1:
            if st.button("💾 Save API Configuration", use_container_width=True, type="primary"):
                st.session_state.api_config["api_key"] = entered_key.strip()
                st.session_state.api_config["model"] = active_model.strip()
                st.session_state.api_config["persona"] = selected_persona
                save_api_config(st.session_state.api_config)
                st.success(f"Configuration saved! Using model: {active_model}")

        with btn_c2:
            if st.button("🔌 Test Connection", use_container_width=True):
                with st.spinner(f"Pinging Google Gemini API with {active_model}..."):
                    success, msg = test_gemini_connection(entered_key, active_model.strip())
                    if success:
                        st.success(f"✅ {msg}")
                    else:
                        st.error(f"❌ {msg}")

    with cfg_col2:
        st.markdown("""
        <div style="background: #F8FAFC; border: 1px solid #E2E8F0; border-radius: 12px; padding: 18px;">
            <h4 style="margin-top: 0; color: #1E293B;">🛡️ Security & Privacy Note</h4>
            <p style="font-size: 13px; color: #64748B; line-height: 1.6;">
                • Your API key is stored locally in <code>api_config.json</code> in your project directory.<br>
                • It is never transmitted to any third-party server other than direct HTTPS calls to Google Gemini's official API.<br>
                • You can obtain a free Gemini API key with generous quotas at <a href="https://aistudio.google.com" target="_blank">Google AI Studio</a>.
            </p>
            <h4 style="color: #1E293B; margin-top: 14px;">⚡ Features Unlocked with API Key:</h4>
            <ul style="font-size: 13px; color: #475569; padding-left: 20px; line-height: 1.6;">
                <li>Live Diagnostic Health Audits</li>
                <li>Direct identification of toxic figures</li>
                <li>Channel-specific optimization playbooks</li>
                <li>Interactive Financial Q&A Chat</li>
            </ul>
        </div>
        """, unsafe_allow_html=True)

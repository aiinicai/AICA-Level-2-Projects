"""
Real-Time Stock & Crypto Trend Predictor
========================================
Streamlit dashboard that pulls live NSE / BSE / global stock and crypto data,
cleans it, scrapes company insights with BeautifulSoup, and forecasts trends
with scikit-learn models and an optional TensorFlow LSTM.

Run:  streamlit run app.py
"""
from __future__ import annotations

import logging
import warnings
from html import escape
from datetime import datetime, timedelta, timezone

import streamlit as st

st.set_page_config(page_title="Stock & Crypto Trend Predictor", page_icon="📈",
                   layout="wide", initial_sidebar_state="expanded")

try:
    import numpy as np
    import pandas as pd

    from core import charts, data_fetcher as dfetch, insights, scraper
    from core.cleaning import clean_ohlcv
    from core.config import (APP_TITLE, CRYPTO_LIST, INDICES, NSE_WATCHLIST,
                             PERIOD_OPTIONS)
    from core.indicators import add_indicators
    from core.models import MIN_ROWS, forecast, tensorflow_available
except ImportError as _exc:  # friendly screen instead of a raw traceback
    _msg = str(_exc)
    st.title("⚠️ The app could not load its libraries")
    st.code(_msg)
    if "Application Control" in _msg or "DLL load failed" in _msg:
        st.error(
            "**Windows blocked a Python library file (a DLL).** This is a Windows "
            "security setting, not a bug in the app."
        )
        st.markdown(
            """
**Fix 1: reinstall known-good library versions (try this first)**
1. Close this window and the black console window.
2. Double-click **`install_dependencies.bat`** again. It reinstalls long-established
   versions that Windows usually trusts.

**Fix 2: if the error still appears, Smart App Control is blocking Python packages**
1. Open **Windows Security** → **App & browser control** → **Smart App Control settings**.
2. Set it to **Off**, then run `run_app.bat` again.
   *Note: on some Windows 11 versions Smart App Control cannot be turned back on
   without resetting Windows.*

**Work or college laptop?** The block comes from a policy set by your IT team.
Ask them to allow Python packages in this folder, or run the app on a personal computer.
"""
        )
    else:
        st.error("A required package is missing or broken. Run **install_dependencies.bat** "
                 "again to repair the installation.")
    st.stop()

warnings.filterwarnings("ignore")
logging.basicConfig(level=logging.WARNING)

IST = timezone(timedelta(hours=5, minutes=30))

st.markdown(
    """
    <style>
      .block-container {padding-top: 1.6rem; padding-bottom: 2rem;}
      div[data-testid="stMetric"] {background: rgba(148,163,184,0.10); border-radius: 10px;
            padding: 10px 14px; border: 1px solid rgba(148,163,184,0.25);}
      .pill {display:inline-block; padding:3px 12px; border-radius:999px; font-weight:600;
             font-size:0.9rem; color:white;}
      .small-note {color:#64748b; font-size:0.82rem;}
      /* Never truncate numbers in any remaining st.metric */
      div[data-testid="stMetricValue"], div[data-testid="stMetricValue"] > div,
      div[data-testid="stMetricDelta"], div[data-testid="stMetricDelta"] > div,
      div[data-testid="stMetricLabel"], div[data-testid="stMetricLabel"] p {
            white-space: normal !important; overflow: visible !important;
            text-overflow: clip !important; word-break: break-word;}
      div[data-testid="stMetricValue"] {font-size: clamp(1.05rem, 1.7vw, 1.6rem) !important;}
      /* Responsive value cards: wrap to new rows instead of cutting figures */
      .kpi-grid {display: grid; gap: 12px; margin: 6px 0 14px 0;
                 grid-template-columns: repeat(auto-fit, minmax(var(--minw, 190px), 1fr));}
      .kpi {background: rgba(148,163,184,0.10); border: 1px solid rgba(148,163,184,0.28);
            border-radius: 12px; padding: 12px 14px; min-width: 0;}
      .kpi .lbl {font-size: 0.82rem; color: #64748b; font-weight: 600; margin-bottom: 4px;
                 line-height: 1.25; overflow-wrap: anywhere;}
      .kpi .val {font-size: clamp(1.1rem, 1.55vw, 1.55rem); font-weight: 700; line-height: 1.25;
                 font-variant-numeric: tabular-nums; overflow-wrap: anywhere;}
      .kpi .dlt {font-size: 0.86rem; font-weight: 600; margin-top: 4px; line-height: 1.3;
                 overflow-wrap: anywhere;}
      .kpi .up {color: #16a34a;} .kpi .down {color: #dc2626;} .kpi .off {color: #64748b;}
    </style>
    """,
    unsafe_allow_html=True,
)

# --------------------------------------------------------------------------- #
# Streamlit-version-safe display helpers
# --------------------------------------------------------------------------- #
try:
    _ST_VER = tuple(int(p) for p in st.__version__.split(".")[:2])
except Exception:
    _ST_VER = (1, 40)
_NEW_WIDTH_API = _ST_VER >= (1, 50)


def show_chart(fig, key: str):
    if fig is None:
        return
    if _NEW_WIDTH_API:
        st.plotly_chart(fig, width="stretch", key=key)
    else:
        st.plotly_chart(fig, use_container_width=True, key=key)


def show_table(df: pd.DataFrame, key: str, **kwargs):
    if _NEW_WIDTH_API:
        st.dataframe(df, width="stretch", key=key, **kwargs)
    else:
        st.dataframe(df, use_container_width=True, key=key, **kwargs)


def verdict_pill(verdict: str) -> str:
    color = {"Bullish": "#15803d", "Mildly Bullish": "#22c55e", "Neutral": "#64748b",
             "Mildly Bearish": "#f97316", "Bearish": "#b91c1c"}.get(verdict, "#64748b")
    return f'<span class="pill" style="background:{color}">{verdict}</span>'


def _tone(delta, tone: str) -> str:
    if tone != "auto":
        return tone
    d = str(delta or "").strip()
    return "down" if d.startswith(("-", "−", "▼")) else "up" if d.startswith(("+", "▲")) else "off"


def cards(items, min_width: int = 190):
    """Render value cards in a responsive grid. Values wrap instead of being cut.

    items: list of dicts {label, value, delta=None, tone="auto"|"up"|"down"|"off"}
    """
    html_parts = []
    for it in items:
        label, value = escape(str(it["label"])), escape(str(it["value"]))
        delta = it.get("delta")
        d_html = ""
        if delta not in (None, ""):
            tone = _tone(delta, it.get("tone", "auto"))
            arrow = {"up": "▲ ", "down": "▼ "}.get(tone, "")
            d_html = f'<div class="dlt {tone}">{arrow}{escape(str(delta))}</div>'
        html_parts.append(f'<div class="kpi"><div class="lbl">{label}</div>'
                          f'<div class="val">{value}</div>{d_html}</div>')
    st.markdown(f'<div class="kpi-grid" style="--minw:{int(min_width)}px">'
                + "".join(html_parts) + "</div>", unsafe_allow_html=True)


def fmt_price(v, cur: str = "") -> str:
    try:
        v = float(v)
    except (TypeError, ValueError):
        return "—"
    if np.isnan(v):
        return "—"
    return f"{cur}{v:,.2f}" if abs(v) >= 1 else f"{cur}{v:,.6f}"


# --------------------------------------------------------------------------- #
# Cached data loaders
# --------------------------------------------------------------------------- #
@st.cache_data(ttl=300, show_spinner=False)
def load_history(symbol: str, period: str, interval: str = "1d"):
    raw = dfetch.get_history(symbol, period, interval)
    return clean_ohlcv(raw)


@st.cache_data(ttl=3600, show_spinner=False)
def load_info(symbol: str) -> dict:
    return dfetch.get_info(symbol)


@st.cache_data(ttl=3600, show_spinner=False)
def load_financials(symbol: str):
    return dfetch.get_financials(symbol)


@st.cache_data(ttl=1800, show_spinner=False)
def load_news(symbol: str, query: str) -> list[dict]:
    news = dfetch.get_yahoo_news(symbol, 10)
    seen = {n["title"].lower() for n in news}
    for n in scraper.scrape_google_news(query, 15):
        if n["title"].lower() not in seen:
            news.append(n)
            seen.add(n["title"].lower())
    for n in news:
        n["sentiment"] = scraper.headline_sentiment(n["title"] + " " + n.get("summary", ""))
    return news


@st.cache_data(ttl=6 * 3600, show_spinner=False)
def load_screener(symbol: str) -> dict:
    return scraper.scrape_screener(symbol)


@st.cache_data(ttl=600, show_spinner=False)
def load_google_finance(symbol: str, exchange: str) -> dict:
    return scraper.scrape_google_finance(symbol, exchange)


@st.cache_data(ttl=120, show_spinner=False)
def load_batch(symbols: tuple) -> pd.DataFrame:
    return dfetch.get_batch_quotes(list(symbols))


@st.cache_data(ttl=120, show_spinner=False)
def load_crypto_board(vs: str) -> tuple[pd.DataFrame, str]:
    ids = [v[0] for v in CRYPTO_LIST.values()]
    df = dfetch.get_crypto_markets(ids, vs.lower())
    if not df.empty:
        return df, "CoinGecko"
    stems = {k: v[1] for k, v in CRYPTO_LIST.items()}
    return dfetch.get_crypto_markets_fallback(stems, vs.upper()), "Yahoo Finance"


@st.cache_data(ttl=300, show_spinner=False)
def load_nse_indices() -> pd.DataFrame:
    return scraper.fetch_nse_indices()


@st.cache_data(ttl=300, show_spinner=False)
def load_market_status() -> list[dict]:
    return scraper.fetch_nse_market_status()


@st.cache_data(ttl=3600, show_spinner=False)
def search(query: str) -> list[dict]:
    return dfetch.search_symbols(query)


@st.cache_data(ttl=1800, show_spinner=False)
def run_forecast(symbol: str, period: str, horizon: int, use_lstm: bool,
                 calendar_days: bool):
    df, _ = load_history(symbol, period)
    return forecast(df["Close"], horizon=horizon, use_lstm=use_lstm,
                    calendar_days=calendar_days)


@st.cache_resource(show_spinner=False)
def tf_ok() -> bool:
    return tensorflow_available()


# --------------------------------------------------------------------------- #
# Sidebar
# --------------------------------------------------------------------------- #
with st.sidebar:
    st.header("⚙️ Settings")
    period = st.selectbox("History period", PERIOD_OPTIONS, index=2, key="sb_period",
                          help="Longer history = more training data for the models.")
    horizon = st.slider("Forecast horizon (trading days)", 5, 60, 15, step=5, key="sb_horizon")
    lstm_available = tf_ok()
    use_lstm = st.toggle("Include LSTM deep-learning model (TensorFlow)", value=False,
                         key="sb_lstm",
                         disabled=not lstm_available,
                         help="Adds ~20-60 s per stock. "
                              + ("" if lstm_available else
                                 "TensorFlow is not installed – run install_dependencies.bat."))
    st.divider()
    chart_type = st.radio("Price chart", ["Candlestick", "Line"], horizontal=True, key="sb_chart")
    show_sma = st.checkbox("Moving averages (20/50/200)", value=True, key="sb_sma")
    show_bb = st.checkbox("Bollinger Bands", value=True, key="sb_bb")
    st.divider()
    auto_refresh = st.toggle("Auto-refresh market board (60 s)", value=False, key="sb_auto")
    if st.button("🔄 Refresh all live data", key="refresh_btn"):
        st.cache_data.clear()
        st.rerun()
    st.caption(f"Last loaded: {datetime.now(IST):%d %b %Y, %I:%M:%S %p} IST")
    st.caption("⚠️ Educational tool – not investment advice.")


# --------------------------------------------------------------------------- #
# Reusable: full stock analysis view
# --------------------------------------------------------------------------- #
def render_stock_analysis(ysym: str, display_name: str, key: str, crypto: bool = False):
    with st.spinner(f"Fetching live data for {ysym} …"):
        df, report = load_history(ysym, period)
    if df.empty or len(df) < 30:
        st.error(f"Could not load enough price data for **{ysym}**. The symbol may be "
                 "invalid, delisted, or Yahoo Finance is temporarily unreachable. "
                 "Try the NSE/BSE variant (e.g. `.NS` ↔ `.BO`) or press *Refresh*.")
        return

    info = {} if crypto else load_info(ysym)
    cur_code = info.get("currency") or ("INR" if ysym.endswith((".NS", ".BO", "-INR"))
                                        else "USD")
    cur = dfetch.currency_symbol(cur_code)
    name = info.get("longName") or info.get("shortName") or display_name
    ind = add_indicators(df)
    last, prev = float(df["Close"].iloc[-1]), float(df["Close"].iloc[-2])
    chg, chg_pct = last - prev, (last / prev - 1) * 100

    st.subheader(f"{name}  ·  `{ysym}`")
    meta = " · ".join(x for x in [info.get("sector"), info.get("industry"),
                                   info.get("exchange") or info.get("fullExchangeName")] if x)
    if meta:
        st.caption(meta)

    hi52 = info.get("fiftyTwoWeekHigh") or df["High"].iloc[-252:].max()
    lo52 = info.get("fiftyTwoWeekLow") or df["Low"].iloc[-252:].min()
    cards([
        {"label": "Last Price", "value": fmt_price(last, cur),
         "delta": f"{chg:+,.2f} ({chg_pct:+.2f}%)"},
        {"label": "Previous Close", "value": fmt_price(prev, cur)},
        {"label": "Day Open", "value": fmt_price(df["Open"].iloc[-1], cur)},
        {"label": "Day High", "value": fmt_price(df["High"].iloc[-1], cur)},
        {"label": "Day Low", "value": fmt_price(df["Low"].iloc[-1], cur)},
        {"label": "52-Week High", "value": fmt_price(hi52, cur),
         "delta": f"{(last / float(hi52) - 1) * 100:+.1f}% from high", "tone": "off"},
        {"label": "52-Week Low", "value": fmt_price(lo52, cur),
         "delta": f"{(last / float(lo52) - 1) * 100:+.1f}% from low", "tone": "off"},
        {"label": "Market Cap",
         "value": insights.fmt_big(info.get("marketCap"), cur) if info else "—"},
        {"label": "Volume", "value": f"{df['Volume'].iloc[-1]:,.0f}"},
    ], min_width=175)
    st.caption(f"Data as of {df.index[-1]:%d %b %Y} · {len(df):,} clean rows "
               f"(removed {report['duplicates_removed']} duplicates, "
               f"{report['invalid_rows_removed']} invalid rows; filled "
               f"{report['missing_filled']} gaps; {report['outliers_flagged']} extreme moves flagged)")

    tech = insights.technical_signals(ind)
    perf = insights.performance_summary(df["Close"])

    t_chart, t_ins, t_fc, t_fin, t_news, t_data = st.tabs(
        ["📈 Charts", "💡 Insights · Pros & Cons", "🔮 ML Forecast", "🏦 Financials",
         "📰 News & Sentiment", "🗂️ Data"])

    # ---------------- Charts
    with t_chart:
        show_chart(charts.price_chart(ind, f"{name} – price & volume", show_sma, show_bb,
                                      chart_type), key=f"{key}_price")
        show_chart(charts.rsi_macd_chart(ind), key=f"{key}_rsimacd")
        a, b = st.columns(2)
        with a:
            show_chart(charts.returns_histogram(df["Close"]), key=f"{key}_hist")
        with b:
            bench = "^NSEI" if ysym.endswith((".NS", ".BO")) else (
                "BTC-USD" if crypto else "^GSPC")
            if bench != ysym:
                bdf, _ = load_history(bench, period)
                series = {name: df["Close"]}
                if not bdf.empty:
                    series[{"^NSEI": "NIFTY 50", "^GSPC": "S&P 500"}.get(bench, bench)] = \
                        bdf["Close"].reindex(df.index).ffill()
                show_chart(charts.normalized_compare(series, "Relative performance vs benchmark"),
                           key=f"{key}_bench")

    # ---------------- Insights
    with t_ins:
        st.markdown(f"#### Technical verdict: {verdict_pill(tech['verdict'])}",
                    unsafe_allow_html=True)
        cards([{"label": f"Return · {label}",
                 "value": "—" if val is None else f"{val:+.2f}%",
                 "delta": None if val is None else ("gain" if val >= 0 else "loss"),
                 "tone": "off" if val is None else ("up" if val >= 0 else "down")}
               for label, val in perf.items()], min_width=150)

        left, right = st.columns(2)
        with left:
            st.markdown("##### 📊 Technical signals")
            icon = {"bull": "🟢", "bear": "🔴", "neutral": "⚪"}
            for kind, text in tech["signals"]:
                st.markdown(f"{icon[kind]} {text}")
        with right:
            st.markdown("##### ⚖️ Risk profile")
            risk = insights.risk_summary(df["Close"], 365 if crypto else 252)
            cards([{"label": k, "value": "—" if v is None else
                     (f"{v:.2f}" if "Ratio" in k else f"{v:.2f}%")}
                   for k, v in risk.items()], min_width=160)

        pros, cons = insights.fundamental_pros_cons(info, tech)
        st.markdown("##### ✅ Pros and ❌ Cons (auto-generated from live data)")
        p, n = st.columns(2)
        with p:
            st.success("**Pros**\n\n" + ("\n".join(f"- {x}" for x in pros) if pros
                                         else "- No clear strengths detected from available data."))
        with n:
            st.error("**Cons**\n\n" + ("\n".join(f"- {x}" for x in cons) if cons
                                       else "- No clear weaknesses detected from available data."))

        base = dfetch.base_symbol(ysym)
        if not crypto and ysym.endswith((".NS", ".BO")):
            with st.spinner("Scraping Screener.in with BeautifulSoup …"):
                scr = load_screener(base)
            if scr:
                st.markdown(f"##### 🔎 Screener.in analysis ([source]({scr.get('url', '')}))")
                if scr.get("pros") or scr.get("cons"):
                    p2, n2 = st.columns(2)
                    with p2:
                        st.success("**Pros (Screener.in)**\n\n" +
                                   "\n".join(f"- {x}" for x in scr.get("pros", [])[:8]))
                    with n2:
                        st.error("**Cons (Screener.in)**\n\n" +
                                 "\n".join(f"- {x}" for x in scr.get("cons", [])[:8]))
                if scr.get("ratios"):
                    cards([{"label": k, "value": v}
                           for k, v in list(scr["ratios"].items())[:12]], min_width=190)
                fig = charts.shareholding_chart(scr.get("shareholding"))
                if fig is not None:
                    show_chart(fig, key=f"{key}_share")
            else:
                st.caption("Screener.in data unavailable right now (site unreachable or "
                           "symbol not listed there).")

        about = "" if crypto else info.get("longBusinessSummary", "")
        if not crypto:
            st.markdown("##### 🏢 About the company")
        if not about and not crypto:
            gexch = {"NS": "NSE", "BO": "BOM"}.get(ysym.split(".")[-1]) if "." in ysym else \
                {"NMS": "NASDAQ", "NGM": "NASDAQ", "NCM": "NASDAQ", "NYQ": "NYSE"}.get(
                    info.get("exchange", ""), "NASDAQ")
            gf = load_google_finance(base, gexch)
            about = gf.get("about", "") if gf else ""
            if not about and ysym.endswith((".NS", ".BO")):
                about = (load_screener(base) or {}).get("about", "")
        if not crypto:
            st.write(about or "Company description not available.")
        extra = []
        for label, keyname in [("Website", "website"), ("Employees", "fullTimeEmployees"),
                               ("Headquarters", "city"), ("Country", "country")]:
            if info.get(keyname):
                v = info[keyname]
                extra.append(f"**{label}:** {v:,}" if isinstance(v, int) else f"**{label}:** {v}")
        if extra:
            st.markdown(" · ".join(extra))
        officers = info.get("companyOfficers") or []
        if officers:
            with st.expander("Key management"):
                for o in officers[:6]:
                    st.markdown(f"- **{o.get('name', '')}** – {o.get('title', '')}")

        if info:
            st.markdown("##### 📋 Key metrics")
            cards([{"label": k, "value": v} for k, v in insights.key_metrics(info, cur)],
                  min_width=175)

    # ---------------- Forecast
    with t_fc:
        st.markdown(f"Models are trained on **{period}** of cleaned daily data to predict the "
                    f"next {horizon} {'days' if crypto else 'trading sessions'}.")
        fc = None
        if len(df) < MIN_ROWS:
            st.warning(f"Only {len(df)} rows – choose a longer history period "
                       f"(need ≥ {MIN_ROWS}).")
        else:
            with st.spinner("Training ML models (Ridge, Random Forest, Gradient Boosting, "
                            f"Neural Net{', LSTM' if use_lstm else ''}) …"):
                try:
                    fc = run_forecast(ysym, period, horizon, use_lstm, crypto)
                except Exception as exc:
                    st.error(f"Forecast failed: {exc}")
        if fc is not None:
            ens = fc.metrics.loc["Ensemble"]
            cards([
                {"label": "Current price", "value": fmt_price(fc.history.iloc[-1], cur)},
                {"label": f"Forecast in {horizon} {'days' if crypto else 'sessions'}",
                 "value": fmt_price(fc.ensemble[-1], cur),
                 "delta": f"{fc.expected_change_pct:+.2f}%"},
                {"label": "95% range – low", "value": fmt_price(fc.lower[-1], cur)},
                {"label": "95% range – high", "value": fmt_price(fc.upper[-1], cur)},
                {"label": "P(next close higher)",
                 "value": "—" if fc.up_probability is None else f"{fc.up_probability:.0f}%",
                 "delta": None if fc.classifier_accuracy is None else
                 f"classifier accuracy {fc.classifier_accuracy:.0f}%", "tone": "off"},
                {"label": "Back-test error (MAPE, 1-day)", "value": f"{ens['MAPE %']:.2f}%",
                 "delta": f"direction hit-rate {ens['Direction Accuracy %']:.0f}%",
                 "tone": "off"},
            ], min_width=185)
            show_chart(charts.forecast_chart(fc, cur=cur), key=f"{key}_fc")
            st.info(insights.narrative(name, info, tech, perf, fc, cur))

            a, b = st.columns([3, 2])
            with a:
                show_chart(charts.backtest_chart(fc), key=f"{key}_bt")
            with b:
                st.markdown("**Model scoreboard (unseen test data)**")
                show_table(fc.metrics.round(2), key=f"{key}_metrics")
                beat = fc.metrics.loc["Ensemble", "RMSE"] < fc.naive_rmse
                st.caption(f"Naive 'tomorrow = today' RMSE: {fc.naive_rmse:,.2f}. The ensemble "
                           f"{'beats' if beat else 'does not beat'} this baseline – "
                           "short-term prices are close to a random walk, so treat forecasts "
                           "as a trend indication, not certainty.")
            fdf = pd.DataFrame({"Date": fc.future_dates.strftime("%d %b %Y"),
                                "Ensemble": fc.ensemble, "Lower 95%": fc.lower,
                                "Upper 95%": fc.upper,
                                **{k: v for k, v in fc.predictions.items()}})
            with st.expander("Forecast table"):
                show_table(fdf.round(2).set_index("Date"), key=f"{key}_fctable")
                st.download_button("⬇️ Download forecast CSV", fdf.to_csv(index=False),
                                   file_name=f"{ysym}_forecast.csv", mime="text/csv",
                                   key=f"{key}_dl_fc")
            for note in fc.notes:
                st.caption(f"ℹ️ {note}")

    # ---------------- Financials
    with t_fin:
        if crypto:
            st.info("Financial statements are not applicable to crypto assets.")
        else:
            fin = load_financials(ysym)
            scr = load_screener(dfetch.base_symbol(ysym)) if ysym.endswith((".NS", ".BO")) else {}
            if scr and isinstance(scr.get("quarters"), pd.DataFrame) and not scr["quarters"].empty:
                st.markdown("##### Quarterly results (Screener.in, ₹ Cr)")
                show_table(scr["quarters"], key=f"{key}_scrq")
            if scr and isinstance(scr.get("profit_loss"), pd.DataFrame) and \
                    not scr["profit_loss"].empty:
                st.markdown("##### Profit & Loss (Screener.in, ₹ Cr)")
                show_table(scr["profit_loss"], key=f"{key}_scrpl")
            if fin:
                for i, (title, table) in enumerate(fin.items()):
                    with st.expander(f"{title} (Yahoo Finance)", expanded=(i == 0)):
                        show_table(table.map(lambda v: insights.fmt_big(v, cur))
                                   if hasattr(table, "map") else table, key=f"{key}_fin{i}")
                inc = fin.get("Income Statement (Annual)")
                if inc is not None:
                    rows = [r for r in ("Total Revenue", "Net Income") if r in inc.index]
                    if rows:
                        plot_df = inc.loc[rows].T.iloc[::-1].apply(pd.to_numeric, errors="coerce")
                        import plotly.graph_objects as go
                        fig = go.Figure([go.Bar(x=plot_df.index, y=plot_df[r], name=r)
                                         for r in rows])
                        fig.update_layout(barmode="group", height=360, template="plotly_white",
                                          title="Revenue vs Net Income (annual)",
                                          margin=dict(l=10, r=10, t=50, b=10))
                        show_chart(fig, key=f"{key}_revni")
            if not fin and not scr:
                st.warning("Financial statements unavailable for this symbol right now.")

    # ---------------- News
    with t_news:
        query = f"{name} share price" if not crypto else f"{display_name} crypto"
        with st.spinner("Collecting headlines (Yahoo Finance + Google News RSS) …"):
            news = load_news(ysym, query)
        if not news:
            st.info("No recent headlines found.")
        else:
            scores = [n["sentiment"] for n in news]
            avg = float(np.mean(scores))
            mood = "Positive 🟢" if avg > 0.1 else "Negative 🔴" if avg < -0.1 else "Neutral ⚪"
            cards([{"label": "Headline sentiment", "value": mood,
                    "delta": f"score {avg:+.2f}", "tone": "off"},
                   {"label": "Positive headlines", "value": sum(s > 0 for s in scores)},
                   {"label": "Negative headlines", "value": sum(s < 0 for s in scores)}],
                  min_width=180)
            for n in news[:20]:
                dot = "🟢" if n["sentiment"] > 0 else "🔴" if n["sentiment"] < 0 else "⚪"
                meta = " · ".join(x for x in [n.get("publisher"), n.get("published")] if x)
                title = n["title"].replace("[", "(").replace("]", ")")
                link = f"[{title}]({n['link']})" if n.get("link") else title
                st.markdown(f"{dot} {link}  \n<span class='small-note'>{meta}</span>",
                            unsafe_allow_html=True)

    # ---------------- Raw data
    with t_data:
        show_table(ind.iloc[::-1].round(2), key=f"{key}_raw", height=420)
        st.download_button("⬇️ Download cleaned data + indicators (CSV)", ind.to_csv(),
                           file_name=f"{ysym}_data.csv", mime="text/csv", key=f"{key}_dl_raw")


# --------------------------------------------------------------------------- #
# Header
# --------------------------------------------------------------------------- #
st.title("📈 " + APP_TITLE)
st.caption("Live NSE · BSE · global stocks · crypto — cleaned, analysed and forecast "
           "with machine learning. Data: Yahoo Finance, CoinGecko, NSE India, "
           "Screener.in, Google Finance & Google News (scraped with BeautifulSoup).")

tab_mkt, tab_stock, tab_crypto, tab_search, tab_about = st.tabs(
    ["📊 Market Dashboard", "📈 Stock Analysis & Forecast", "₿ Crypto Tracker",
     "🔍 Search Any Stock", "ℹ️ About"])


# --------------------------------------------------------------------------- #
# TAB 1 – Market dashboard
# --------------------------------------------------------------------------- #
def market_board():
    status = load_market_status()
    if status:
        chips = " · ".join(f"**{s['market']}**: {s['status']}" for s in status[:4] if s["market"])
        st.markdown(f"🏛️ NSE market status — {chips}")

    idx = load_batch(tuple(INDICES.values()))
    if idx.empty:
        st.warning("Live index quotes are unavailable right now. Check your internet "
                   "connection and press *Refresh*.")
    else:
        rev = {v: k for k, v in INDICES.items()}
        cards([{"label": rev.get(row["Symbol"], row["Symbol"]),
                "value": f"{row['Price']:,.2f}",
                "delta": f"{row['Change']:+,.2f} ({row['Change %']:+.2f}%)"}
               for _, row in idx.iterrows()], min_width=200)
    st.caption(f"Updated {datetime.now(IST):%I:%M:%S %p} IST")


with tab_mkt:
    if auto_refresh and hasattr(st, "fragment"):
        st.fragment(run_every=60)(market_board)()
    else:
        market_board()

    left, right = st.columns([2, 1])
    with left:
        idx_name = st.selectbox("Index chart", list(INDICES.keys()), key="mkt_idx")
        view = st.radio("Range", ["Intraday (5-min)", "1 Month", "6 Months", "1 Year", "5 Years"],
                        horizontal=True, index=3, key="mkt_range")
        per, itv = {"Intraday (5-min)": ("5d", "5m"), "1 Month": ("1mo", "1d"),
                    "6 Months": ("6mo", "1d"), "1 Year": ("1y", "1d"),
                    "5 Years": ("5y", "1wk")}[view]
        idf, _ = load_history(INDICES[idx_name], per, itv)
        if itv == "5m" and not idf.empty:
            idf = idf[idf.index.date == idf.index[-1].date()]
        if idf.empty:
            st.info("Index history unavailable right now.")
        else:
            show_chart(charts.price_chart(add_indicators(idf), f"{idx_name} ({view})",
                                          show_sma=itv != "5m", show_bb=False,
                                          chart_type="Line" if itv == "5m" else chart_type),
                       key="mkt_idx_chart")
    with right:
        st.markdown("##### Indian vs global markets")
        comp = {}
        for nm in ("NIFTY 50", "SENSEX", "NIFTY BANK", "S&P 500"):
            h, _ = load_history(INDICES[nm], "1y")
            if not h.empty:
                comp[nm] = h["Close"]
        if comp:
            show_chart(charts.normalized_compare(comp, "1-year performance (rebased)"),
                       key="mkt_compare")

    st.markdown("### 🔥 NIFTY 50 heat-map, top gainers & losers")
    wl = load_batch(tuple(f"{s}.NS" for s in NSE_WATCHLIST.values()))
    if wl.empty:
        st.info("Watch-list quotes unavailable right now.")
    else:
        rev = {f"{s}.NS": n for n, s in NSE_WATCHLIST.items()}
        wl["Company"] = wl["Symbol"].map(rev).fillna(wl["Symbol"])
        wl["Ticker"] = wl["Symbol"].str.replace(".NS", "", regex=False)
        show_chart(charts.heatmap_treemap(wl, "Ticker", "Change %", "Price",
                                          "Daily % change (tile size ~ price)"),
                   key="mkt_heat")
        g, l_ = st.columns(2)
        with g:
            show_chart(charts.movers_bar(wl.nlargest(10, "Change %"), "Ticker", "Change %",
                                         "Top 10 gainers"), key="mkt_gainers")
        with l_:
            show_chart(charts.movers_bar(wl.nsmallest(10, "Change %"), "Ticker", "Change %",
                                         "Top 10 losers"), key="mkt_losers")
        adv, dec = int((wl["Change %"] > 0).sum()), int((wl["Change %"] < 0).sum())
        st.caption(f"Breadth: {adv} advancing · {dec} declining · "
                   f"{len(wl) - adv - dec} unchanged")
        with st.expander("Full watch-list table"):
            show_table(wl[["Company", "Ticker", "Price", "Change", "Change %"]]
                       .sort_values("Change %", ascending=False).round(2).set_index("Company"),
                       key="mkt_wl_table")

    with st.expander("📡 Live NSE indices board (scraped from nseindia.com)"):
        nse = load_nse_indices()
        if nse.empty:
            st.caption("NSE blocks some automated requests; the board will appear when "
                       "nseindia.com responds. Index cards above use Yahoo Finance.")
        else:
            show_table(nse, key="mkt_nse_board", hide_index=True)


# --------------------------------------------------------------------------- #
# TAB 2 – Stock analysis from the watch-list
# --------------------------------------------------------------------------- #
with tab_stock:
    c1, c2 = st.columns([3, 1])
    with c1:
        company = st.selectbox("Choose a company (NIFTY 50 watch-list)",
                               list(NSE_WATCHLIST.keys()), key="wl_company")
    with c2:
        exch = st.radio("Exchange", ["NSE", "BSE"], horizontal=True, key="wl_exch")
    ysym = dfetch.to_yahoo_symbol(NSE_WATCHLIST[company], "NSE")
    if exch == "BSE":
        ysym = ysym.replace(".NS", ".BO")
    render_stock_analysis(ysym, company, key="wl")


# --------------------------------------------------------------------------- #
# TAB 3 – Crypto
# --------------------------------------------------------------------------- #
with tab_crypto:
    vs = st.radio("Quote currency", ["INR", "USD"], horizontal=True, key="cr_vs")
    vs_sym = "₹" if vs == "INR" else "$"
    board, source = load_crypto_board(vs)
    if board.empty:
        st.warning("Live crypto board unavailable right now (CoinGecko and Yahoo "
                   "unreachable). Try *Refresh* in a minute.")
    else:
        top = board.head(4)
        cols = st.columns(len(top))
        for col, (_, r) in zip(cols, top.iterrows()):
            ch = float(r.get("price_change_percentage_24h_in_currency") or 0)
            with col:
                cards([{"label": f"{r['name']} ({str(r['symbol']).upper()})",
                        "value": fmt_price(r["current_price"], vs_sym),
                        "delta": f"{ch:+.2f}% in 24h"}], min_width=120)
            spark = r.get("sparkline")
            if isinstance(spark, list) and len(spark) > 2:
                with col:
                    show_chart(charts.sparkline(spark, spark[-1] >= spark[0]),
                               key=f"cr_spark_{r['symbol']}")
        table = board.copy()
        rename = {"name": "Coin", "symbol": "Symbol", "current_price": f"Price ({vs})",
                  "price_change_percentage_1h_in_currency": "1h %",
                  "price_change_percentage_24h_in_currency": "24h %",
                  "price_change_percentage_7d_in_currency": "7d %",
                  "market_cap": f"Market Cap ({vs})", "total_volume": f"Volume 24h ({vs})",
                  "sparkline": "Last 7 days", "ath_change_percentage": "From ATH %"}
        table = table[[c for c in rename if c in table.columns]].rename(columns=rename)
        if "Symbol" in table:
            table["Symbol"] = table["Symbol"].astype(str).str.upper()
        cfg = {}
        if "Last 7 days" in table and hasattr(st, "column_config"):
            cfg["Last 7 days"] = st.column_config.LineChartColumn("Last 7 days")
        for col in ("1h %", "24h %", "7d %", "From ATH %"):
            if col in table and hasattr(st, "column_config"):
                cfg[col] = st.column_config.NumberColumn(col, format="%.2f%%")
        show_table(table, key="cr_board", hide_index=True, column_config=cfg)
        st.caption(f"Source: {source} · refreshed every 2 minutes")
        if "24h %" in table:
            show_chart(charts.movers_bar(table.dropna(subset=["24h %"]), "Coin", "24h %",
                                         "24-hour change"), key="cr_movers")

    st.divider()
    coin = st.selectbox("Analyse & forecast a coin", list(CRYPTO_LIST.keys()), key="cr_coin")
    render_stock_analysis(f"{CRYPTO_LIST[coin][1]}-{vs}", coin, key="crypto", crypto=True)


# --------------------------------------------------------------------------- #
# TAB 4 – Search any stock
# --------------------------------------------------------------------------- #
with tab_search:
    st.markdown("### 🔍 Search any stock by **company name** or **script code**")
    st.caption("Examples: `Reliance`, `Tata Consultancy`, `IRCTC`, `HDFCBANK`, `500325` "
               "(BSE code), `Apple`, `TSLA`. Indian listings (NSE `.NS`, BSE `.BO`) "
               "are shown first.")
    q = st.text_input("Company name or script code", key="search_q",
                      placeholder="Type a name and press Enter …")
    if q.strip():
        with st.spinner("Searching …"):
            results = search(q.strip())
        if not results:
            st.warning("No matching symbols found. Try the exact NSE code (e.g. `TATAPOWER`) "
                       "or BSE code (e.g. `500400`).")
        else:
            labels = [f"{r['symbol']} — {r['name']} ({r['exchange'] or r['type']})"
                      for r in results]
            choice = st.selectbox(f"{len(results)} matches – pick one", range(len(results)),
                                  format_func=lambda i: labels[i], key="search_pick")
            sel = results[choice]
            is_crypto = sel["symbol"].endswith(("-USD", "-INR")) or \
                str(sel.get("type", "")).upper() == "CRYPTOCURRENCY"
            render_stock_analysis(sel["symbol"], sel["name"], key="search", crypto=is_crypto)
    else:
        st.info("👆 Enter a company name or script code to fetch live details, insights, "
                "pros & cons and an ML forecast.")


# --------------------------------------------------------------------------- #
# TAB 5 – About
# --------------------------------------------------------------------------- #
with tab_about:
    st.markdown(f"""
### How it works
**1. Live data** – prices from **Yahoo Finance** (`yfinance`) for NSE (`.NS`), BSE (`.BO`),
global stocks, indices and crypto; the crypto board from **CoinGecko**; the live indices board
and market status from **NSE India**.

**2. Web scraping (BeautifulSoup)** – **Screener.in** (company profile, key ratios, pros & cons,
quarterly results, P&L, shareholding), **Google Finance** (quote summary & about) and
**Google News RSS** (headlines for sentiment).

**3. Cleaning** – duplicate dates removed, time-zones normalised, missing values filled,
invalid prices dropped, High/Low repaired and extreme moves flagged.

**4. Features** – lagged returns, distance from 5/10/20/50-day averages, momentum, volatility,
RSI, MACD and 20-day range position.

**5. Models** – Ridge Regression, Random Forest, Gradient Boosting and an MLP neural network
(scikit-learn) plus an optional **LSTM** (TensorFlow). Each is back-tested on the most recent
20 % of history it never saw, then blended with weights ∝ 1/RMSE. A Random-Forest classifier
estimates the probability that the next session closes higher.

**6. Insights** – technical verdict, risk (volatility, drawdown, Sharpe, VaR), rule-based
pros & cons from fundamentals, plus Screener.in's own pros & cons for Indian stocks.

**TensorFlow detected:** {"✅ yes – LSTM available" if tf_ok() else "❌ no – LSTM disabled (MLP used)"}

---
⚠️ **Disclaimer:** This application is for education and research. Market forecasts are
uncertain; nothing here is investment advice. Always do your own research or consult a
SEBI-registered adviser before investing.
""")

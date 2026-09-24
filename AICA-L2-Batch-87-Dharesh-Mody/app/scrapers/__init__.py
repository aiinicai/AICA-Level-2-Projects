from . import (
    nse, bse, moneycontrol, chittorgarh, ipoji, investorgain,
    investorgain_subscription, ipowatch, ipo_index, ipo_markets, ipo_premium,
)

# key -> (module, display name, is_official_exchange, needs_browser)
# Order matters: Chittorgarh is fetched first and is the primary GMP source;
# IPOJI is fetched right after it and only overrides GMP when the most recent
# Chittorgarh attempt failed (see source_ok_recently()/merge_incoming() in
# app/db.py). InvestorGain remains a further fallback after that.
# investorgain_subscription runs after those: subscription figures use a
# freshness (last-fetched-wins) rule rather than an official/unofficial one,
# so placing it after NSE/BSE means it reflects whichever number is
# genuinely most recent within this refresh pass.
# IPOWatch/IPO Index/IPO Markets/IPO Premium never feed the merged
# gmp_amount at all — they exist purely to populate the per-IPO "GMP" tab's
# source-by-source diagnostics table (see GMP_DIAGNOSTIC_SOURCES below and
# db.sync_gmp_quotes()).
REGISTRY = {
    "nse": (nse, nse.NAME, True, False),
    "bse": (bse, bse.NAME, True, False),
    "moneycontrol": (moneycontrol, moneycontrol.NAME, False, False),
    "chittorgarh": (chittorgarh, chittorgarh.NAME, False, True),
    "ipoji": (ipoji, ipoji.NAME, False, True),
    "investorgain": (investorgain, investorgain.NAME, False, True),
    "investorgain_subscription": (investorgain_subscription, investorgain_subscription.NAME, False, True),
    "ipowatch": (ipowatch, ipowatch.NAME, False, True),
    "ipo_index": (ipo_index, ipo_index.NAME, False, True),
    "ipo_markets": (ipo_markets, ipo_markets.NAME, False, True),
    "ipo_premium": (ipo_premium, ipo_premium.NAME, False, True),
}

SOURCE_URLS = {
    "nse": nse.API_URL,
    "bse": bse.URL,
    "moneycontrol": moneycontrol.URL,
    "chittorgarh": chittorgarh.URL,
    "ipoji": ipoji.URL,
    "investorgain": investorgain.URL,
    "investorgain_subscription": investorgain_subscription.URL,
    "ipowatch": ipowatch.URL,
    "ipo_index": ipo_index.URL,
    "ipo_markets": ipo_markets.URL,
    "ipo_premium": ipo_premium.URL,
}

# Sources shown in the per-IPO "GMP" tab's "All checked GMP sources" table,
# in the order they're displayed. This list is deliberately separate from
# REGISTRY's merge behaviour: every source here gets its own independent
# row (see db.sync_gmp_quotes()) regardless of whether it's allowed to win
# the single merged gmp_amount used elsewhere in the app.
GMP_DIAGNOSTIC_SOURCES = [
    "ipowatch", "ipoji", "investorgain", "ipo_index", "ipo_markets",
    "ipo_premium", "chittorgarh",
]

# Chittorgarh's own GMP report is, in practice, the same InvestorGain
# publisher/feed under Chittorgarh's branding — so counting it as a second,
# independent quote alongside InvestorGain would overstate how many sources
# actually agree. It's still fetched and still used as the app's primary
# GMP source for the merged gmp_amount (see REGISTRY/merge_incoming above),
# just not shown as an independent number in the diagnostics table.
GMP_REDIRECTS = {
    "chittorgarh": "Directory links to InvestorGain; same publisher/feed, so it is not counted twice",
}

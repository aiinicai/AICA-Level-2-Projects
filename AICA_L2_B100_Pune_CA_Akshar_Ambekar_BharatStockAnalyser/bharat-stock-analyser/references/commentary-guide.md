# Analyst commentary guide

The engine produces numbers and rule-based bullets. Claude adds the analyst layer: context
from results, filings and news. The commentary is merged into the report and labelled
"Analyst view" so that a reader can always tell model output from analyst judgement.

## Schema

All fields are optional. Unknown fields are rejected.

```json
{
  "headline": "string, one line, at most about 14 words",
  "summary": "string, 3 to 5 sentences",
  "highlights": ["string", "..."],
  "catalysts": ["string", "..."],
  "risks": ["string", "..."],
  "business": "string, replaces the source company profile (optional)",
  "sources": [{"title": "string", "url": "https://...", "date": "DD-Mon-YYYY"}],
  "newer_results": {"quarter": "Q2FY27", "date": "DD-Mon-YYYY", "source": "https://..."},
  "data_conflicts": ["string", "..."]
}
```

| Field | What to write |
|---|---|
| `headline` | The investment call in one line, in the style of a broker note title. Example: "Volume recovery priced in; balance sheet caps upside". Must be consistent with the model rating. |
| `summary` | What the company is, what happened recently, why the model rating makes sense (or where you disagree and why), and what to watch. |
| `highlights` | 3 to 6 bullets from the latest results and filings: volumes, margins, guidance, order book, capex, asset quality. Each with a number and its period. |
| `catalysts` | 2 to 4 dated or measurable events: results dates, capacity commissioning, policy decisions. |
| `risks` | 3 to 5 risks not already covered by the model concerns: regulatory, commodity, governance, concentration, pledge. |
| `sources` | Every source used, with URL and date. |
| `newer_results` | Only when results for a quarter newer than the digest's latest quarter are published. `quarter` is required. Setting it makes the rating provisional (never BUY). When the digest says "Results freshness: confirmed with NSE", the filings were already checked and this field is normally not needed. |
| `data_conflicts` | Each material contradiction between a digest figure and a reliable source, in one sentence with both figures and the source. Setting it makes the rating provisional. Do not list rounding differences or differences that the digest already explains (for example one-off adjustments). |

## Writing rules

1. **Numbers.** Every number must appear in the digest or in a cited source. Quote the period
   (Q1FY27, FY26) with every figure.
2. **No overrides.** Do not restate a different target price or rating. If you disagree, say so
   in `summary` or `risks`, for example "Analyst view: the consensus forward EPS assumes a
   steel price recovery that is not visible in the latest quarter." The only fields that
   affect the rating are `newer_results` and `data_conflicts`, and they can only make it more
   cautious.
3. **Separate fact from inference.** "EBITDA per tonne fell 12% QoQ (company release)" is a
   fact. "Margins may recover as coking coal eases" is an inference; label it with "may" or
   "we expect".
4. **Style.** Plain, precise English. No hype ("rocket", "multibagger"), no emojis, no
   exclamation marks. Indian units: Rs, crore, lakh. Fiscal years as FY26, quarters as Q1FY27.
5. **Freshness.** Figures marked "NSE filing" in the digest's quarterly table come from the
   company's own XBRL filing; prefer them over press reports, and use them to reconcile press
   figures (for example profit to owners against profit including minority interest).
   If you find results for a quarter newer than the latest one in the digest,
   set `newer_results`, give the key figures in `highlights` with the source, and say in
   `summary` that the model figures and target do not yet include that quarter. If you
   searched and found nothing, say so in `summary` ("Q2FY27 results not found as of
   01-Nov-2026"). Never write that results are "due" without checking the exchange filing.
6. **No personal advice.** Do not tell the reader how much to buy, at what price to enter, or
   what fits their portfolio.

## Example (Tata Steel, figures from the digest only)

```json
{
  "headline": "BUY on valuation with low conviction; Q2FY27 results are the test",
  "summary": "Tata Steel makes flat and long steel products in India and overseas. Q1FY27 revenue rose 14.3% YoY to Rs 60,794 crore and profit excluding one-offs rose 17.5% YoY. The model's blended target of Rs 217.1 implies 29.5% upside, in line with the consensus mean of Rs 217.0; the composite score of 50 sits exactly at the quality gate, and conviction is Low because the DCF value of Rs 51.17 points the other way. Analyst view: the upside depends on consensus EPS of 1.9x trailing; with net debt to equity of 0.82x and a price below the 200-day average, this is a low-conviction call until the margin recovery shows in reported profit.",
  "highlights": [
    "Q1FY27 revenue of Rs 60,794 crore, up 14.3% YoY and down 3.9% QoQ.",
    "Q1FY27 EBITDA excluding other income of Rs 9,264 crore, up 24.7% from Rs 7,428 crore in Q1FY26.",
    "FY26 net profit of Rs 10,794 crore after a loss of Rs 4,437 crore in FY24, when one-off charges were Rs 6,639 crore before tax.",
    "35 analysts have a mean target of Rs 217.0, with a range of Rs 175 to Rs 260."
  ],
  "catalysts": [
    "Q2FY27 results, which will show whether the margin recovery holds.",
    "Any change in safeguard duty on steel imports."
  ],
  "risks": [
    "Analyst view: consensus forward EPS of Rs 17.90 is 1.9x trailing EPS of Rs 9.53; a weaker steel cycle would remove most of the upside.",
    "Revenue declined at a 1.6% CAGR over FY23 to FY26, so earnings growth depends on margins rather than revenue growth."
  ],
  "sources": []
}
```

When web search is available, `sources` must list the filings and articles behind each new
fact. The example above uses only digest figures, so it has no external sources. The full
researched versions are in `examples/TATASTEEL_commentary.json` and
`examples/DIXON_commentary.json`; the Dixon file reconciles two press figures for Q2FY27 profit
with the NSE filing.

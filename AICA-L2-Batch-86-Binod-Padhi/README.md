# India Property Rent & Valuation Analyzer

A modular PyQt6 desktop application that estimates whether a residential
property in India is **overpriced, fairly priced, or underpriced**, based
on comparable listings, rental yield, and price-to-rent analysis.

## Status: Working core (Phase 1)

This is a complete, runnable implementation of the core engine described
in the design brief:

- ✅ SQLite schema: states/cities/localities, listings, properties, valuations
- ✅ Locality-first comparable selection with progressive fallback to city level (never city-average-only)
- ✅ Three valuation methods (comparable, rental capitalization, adjusted) combined into a Fair Value Range
- ✅ Gross/net rental yield, price-to-rent ratio, overpriced/underpriced verdict with configurable thresholds
- ✅ Data confidence score + combined investment score (0–100), both with configurable weights
- ✅ CSV/Excel/JSON import pipeline with header normalization, validation, dedup, and IQR outlier flagging (flags, doesn't silently drop)
- ✅ PyQt6 GUI: Home, Property Valuation form, Valuation Result (with charts), City Comparison, Market Data/import
- ✅ Word, Excel, and PDF report export
- ✅ Prominent, non-skippable disclaimer text throughout (see `config.DISCLAIMER`)
- ✅ First-run demo data (360 synthetic records across 10 localities) so every screen has something to show — clearly flagged `is_sample_data=1` in the database and labeled "DEMO SOURCE — SAMPLE DATA", never presented as real market data

## Not yet implemented (roadmap, not started to keep this build honest)

- Locality Market Dashboard screen (drill-down UI) — the underlying query
  layer (`database.query_listings`, `valuation.comparable`) already supports
  it; only the dedicated screen is missing.
- Historical price/rent trend charts — `gui/charts.py::trend_chart` exists
  but nothing feeds it yet, since trend data requires multiple dated
  snapshots the demo dataset doesn't simulate.
- Settings screen for editing thresholds/weights in `config.py` live from the GUI.
- Automated API connectors (NHB RESIDEX report parser, Numbeo paid API) —
  stubbed in `data/data_sources.py` with an explanation of why scraping
  MagicBricks/Housing.com/99acres is intentionally not implemented.

## Running it

### Windows (recommended): double-click the batch files

- **`run_app.bat`** — first-time setup: creates a `venv` virtual environment,
  installs all dependencies from `requirements.txt`, and launches the app.
  Safe to double-click again later too (it reuses the existing `venv` and
  just re-checks dependencies).
- **`launch.bat`** — fast subsequent launches once `run_app.bat` has been
  run at least once (skips the dependency check for a quicker start).

Requires Python 3.10+ installed and available as `python` or `py` on your
`PATH` (check "Add Python to PATH" during Python installation). If Python
isn't found, `run_app.bat` will tell you and exit instead of failing silently.

### Manual / other platforms

```bash
pip install -r requirements.txt
python main.py
```

On first launch the app creates `property_analyzer.db` (SQLite) next to
`main.py`, seeds Indian states/cities/localities from
`resources/india_locations.json`, and loads the demo dataset.

## Getting real data in

Automated scraping of listing portals that restrict bot access is
intentionally out of scope. Use:

1. **Market Data tab → Import CSV/Excel/JSON** — the importer accepts
   flexible headers (see `data/normalizer.py::HEADER_ALIASES`) and a
   downloadable template.
2. Any officially published report (e.g. NHB RESIDEX) — extract the table
   into the template format and import it the same way.

## Project layout

See the module docstrings — every file explains its own responsibility.
Business logic (`valuation/`) has no PyQt or sqlite3 dependency and is
independently testable.

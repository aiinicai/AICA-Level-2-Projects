"""
Risk engine package — populated in Stage 12.

A single centralized scorer (Blueprint Section H) consumed by all four
rule packs — not four separate risk formulas. Operates on INTEGER paise
values directly (percentile/ratio math is scale-invariant); only display
formatting converts to rupees, via app/utils/currency.py.
"""

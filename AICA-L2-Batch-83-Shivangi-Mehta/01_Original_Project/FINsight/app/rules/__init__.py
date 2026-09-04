"""
Rule engines package.

Four independent, pluggable sub-packages: accounting/, audit/, tax/,
sebi/. base_rule.py (the shared BaseRule interface + auto-discovery
registry — Blueprint Section A.2, item 4) is added in Stage 3/8 once
there are model classes for rule metadata to register against.

Module-boundary reminder (Blueprint Section 1.1): accounting rules test
framework-treatment questions only; audit rules test assertion-tagged
risk indicators only. Shared detection logic (e.g. related-party
matching) lives in one place and is called by both, not duplicated.
"""

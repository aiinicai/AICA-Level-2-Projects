"""
SEBI/LODR rule pack — DEFERRED, not populated in V1.

FinSight V1 scope decision (approved, post-Stage-10): SEBI / Listed
Entity compliance review is out of scope for V1 — see
documentation/finsight_v1_scope.md and architecture.md's "Stage 11
Scope Change" addendum. This package remains an empty stub,
intentionally preserved (not removed) so a future FinSight V2 can
populate it without any registration/wiring changes elsewhere.

Same gating requirement as tax/ would apply if/when this pack is ever
populated (Blueprint Section 1.2 / Section 6): every rule would need to
reach VERIFIED status against primary LODR Regulations text before it
could execute. The 5-row SEBI Rule Verification Register carried in
architecture.md Section 6 is historical/reference content only — none
of those rows are implemented, and none are currently planned to be.
"""

"""Human Review page - Module 13, Level 3.

The only place in this application where a HumanReview object is ever
created. Every AI-generated claim (business/management/governance
interpretations, and the investment thesis if generated) is listed here
with an explicit Accept/Reject action - nothing gets marked reviewed by
any other code path, which is what makes the report's Human Validation
Checklist an honest record rather than a formality.
"""

from __future__ import annotations

from datetime import datetime, timezone

import streamlit as st

from app.core.models import HumanReview


def upsert_human_review(
    reviews: list[HumanReview], target_id: str, reviewer_name: str,
    accepted: bool, notes: str | None = None,
) -> list[HumanReview]:
    """Pure function: return a new reviews list with any existing review
    for target_id replaced (re-reviewing updates the record rather than
    creating a duplicate), or the new review appended if none existed.
    Testable without Streamlit."""
    filtered = [r for r in reviews if r.target_id != target_id]
    new_review = HumanReview(
        target_id=target_id, reviewer_name=reviewer_name, accepted=accepted,
        reviewer_notes=notes, reviewed_at=datetime.now(timezone.utc),
    )
    filtered.append(new_review)
    return filtered


def _review_lookup(reviews: list[HumanReview]) -> dict[str, HumanReview]:
    return {r.target_id: r for r in reviews}


def render() -> None:
    st.header("Human Review")
    st.caption(
        "Every AI-generated claim below is Level 2 (AI Interpretation) until "
        "explicitly reviewed here. Nothing is ever auto-marked as reviewed - "
        "this page is the only place that happens."
    )

    company = st.session_state.get("company")
    if company is None:
        st.info("Load a company on the Company Input page first.")
        return

    reviewer_name = st.text_input(
        "Your Name (used for every review recorded below)",
        value=st.session_state.get("reviewer_name", ""),
    )
    st.session_state["reviewer_name"] = reviewer_name

    all_interps = (
        st.session_state.get("business_interpretations", [])
        + st.session_state.get("management_interpretations", [])
        + st.session_state.get("governance_interpretations", [])
    )
    thesis = st.session_state.get("thesis")
    human_reviews = st.session_state.get("human_reviews", [])
    reviewed = _review_lookup(human_reviews)

    if not all_interps and thesis is None:
        st.info(
            "No AI-generated content to review yet. Run document/risk analysis "
            "(Risk Dashboard) or generate a thesis (Final Thesis & Report) first."
        )
        return

    if all_interps:
        st.subheader(f"AI Interpretations ({len(all_interps)})")
        for interp in all_interps:
            existing = reviewed.get(interp.interpretation_id)
            status = (
                f"Accepted by {existing.reviewer_name}" if existing and existing.accepted
                else f"Rejected by {existing.reviewer_name}" if existing
                else "Not yet reviewed"
            )
            with st.expander(f"[{interp.confidence.value.upper()}] {interp.claim[:80]} - {status}"):
                st.write(interp.claim)
                st.caption(f"Confidence: {interp.confidence.value} | Model: {interp.model_name}")
                if existing and existing.reviewer_notes:
                    st.caption(f"Previous note: {existing.reviewer_notes}")

                notes = st.text_area("Notes (optional)", key=f"notes_{interp.interpretation_id}")
                col1, col2 = st.columns(2)
                with col1:
                    if st.button("Accept", key=f"accept_{interp.interpretation_id}"):
                        if not reviewer_name:
                            st.error("Enter your name above before recording a review.")
                        else:
                            st.session_state["human_reviews"] = upsert_human_review(
                                human_reviews, interp.interpretation_id, reviewer_name, True, notes or None,
                            )
                            st.rerun()
                with col2:
                    if st.button("Reject", key=f"reject_{interp.interpretation_id}"):
                        if not reviewer_name:
                            st.error("Enter your name above before recording a review.")
                        else:
                            st.session_state["human_reviews"] = upsert_human_review(
                                human_reviews, interp.interpretation_id, reviewer_name, False, notes or None,
                            )
                            st.rerun()

    if thesis is not None:
        st.subheader("Investment Thesis")
        existing = reviewed.get("thesis")
        status = (
            f"Accepted by {existing.reviewer_name}" if existing and existing.accepted
            else f"Rejected by {existing.reviewer_name}" if existing
            else "Not yet reviewed"
        )
        with st.expander(f"Recommendation: {thesis.recommendation.value.upper()} - {status}"):
            st.write(thesis.core_thesis)
            notes = st.text_area("Notes (optional)", key="notes_thesis")
            col1, col2 = st.columns(2)
            with col1:
                if st.button("Accept Thesis"):
                    if not reviewer_name:
                        st.error("Enter your name above before recording a review.")
                    else:
                        st.session_state["human_reviews"] = upsert_human_review(
                            human_reviews, "thesis", reviewer_name, True, notes or None,
                        )
                        st.rerun()
            with col2:
                if st.button("Reject Thesis"):
                    if not reviewer_name:
                        st.error("Enter your name above before recording a review.")
                    else:
                        st.session_state["human_reviews"] = upsert_human_review(
                            human_reviews, "thesis", reviewer_name, False, notes or None,
                        )
                        st.rerun()

    st.markdown("---")
    total_targets = len(all_interps) + (1 if thesis is not None else 0)
    total_reviewed = len(reviewed)
    st.metric("Review Progress", f"{total_reviewed} / {total_targets}")

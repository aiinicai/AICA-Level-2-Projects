"""
legal.py
--------
Single source of truth for the usage-restriction notice. Every export
and the web UI footer pull the text from here, so it only needs to be
right in one place.
"""

PROJECT_NOTICE = (
    "This tool was developed by Shrey Chopra solely as a submission for the "
    "ICAI AICA (AI for Chartered Accountants) Level 2 capstone project. It is "
    "provided for evaluation purposes only and is not licensed for commercial, "
    "production, or client-facing use. No part of this application, its source "
    "code, or its output templates may be copied, redistributed, or reused "
    "without the prior written permission of the project owner."
)

SHORT_NOTICE = "ICAI AICA Level 2 capstone submission — Shrey Chopra. Not for reuse without permission."

DRAFT_WATERMARK = "DRAFT — SYSTEM-GENERATED, PENDING CONTROLLER SIGN-OFF"
FINAL_WATERMARK = "FINAL — CONTROLLER-APPROVED"

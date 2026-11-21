#!/usr/bin/env python3
"""
GIA_Arthwise Loan Facilitator & Debt Syndication Platform
Entry point script to start the unified production-oriented application.
"""
import os
import sys
import uvicorn

if __name__ == "__main__":
    # Ensure current workspace is on sys.path
    workspace_dir = os.path.dirname(os.path.abspath(__file__))
    if workspace_dir not in sys.path:
        sys.path.insert(0, workspace_dir)

    print("=" * 80)
    print("   GIA_ARTHWISE LOAN PROPOSAL EVALUATION & DEBT SYNDICATION PLATFORM")
    print("   Production Platform for Indian Financial Intermediaries & Syndicators")
    print("=" * 80)
    print("Regulatory Notice:")
    print("  All eligibility results are preliminary estimates for professional review.")
    print("  Never represent them as a loan sanction, credit approval, or guarantee.")
    print("-" * 80)
    print("Access URLs:")
    print("  • Web Application & PWA:  http://127.0.0.1:8000")
    print("  • REST API Documentation: http://127.0.0.1:8000/docs")
    print("  • Alternative Redoc:      http://127.0.0.1:8000/redoc")
    print("-" * 80)
    print("Pre-seeded Test Roles & Credentials:")
    print("  • Administrator:  admin@giaarthwise.com    / Admin@123")
    print("  • Senior Analyst: analyst@giaarthwise.com  / Analyst@123")
    print("  • Credit Reviewer: reviewer@giaarthwise.com / Reviewer@123")
    print("  • Borrower Client: client@giaarthwise.com   / Client@123")
    print("=" * 80)

    uvicorn.run("backend.app.main:app", host="127.0.0.1", port=8000, reload=True)

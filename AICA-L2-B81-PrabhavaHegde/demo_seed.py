"""
Builds the fictitious sample assessment: Meridian Textiles Private Limited.

Every entity, person and document here is invented. No real client data is used,
which is itself a DPDP requirement the tool must not breach while demonstrating
DPDP readiness work.

The sample is written only through Project methods, exactly as the screens write,
and is chosen to show the evidence gate at work: some heavyweight controls are
claimed as Present with nothing attached, and score nil.

The app calls seed() on first start when its folder holds no assessment. It can
also be run by hand:

    python demo_seed.py                      # into demo/clients
    python demo_seed.py --clients-dir PATH   # into another folder
"""

from __future__ import annotations

import argparse
import tempfile
from pathlib import Path

import role
from catalogue import applicable, load_catalogue
from models import Client, Project

SLUG = "Meridian_Textiles_Pvt_Ltd"

# The entity runs its own business and decides the purpose of processing.
ROLE_ANSWERS = {"Q1": True, "Q2": True, "Q3": True, "Q4": True, "Q5": False}

# control id -> (status, assessor note, management response, owner, target date)
TABLE = {
    "R6.2": ("Present", "TLS 1.3 enforced on portal and mail gateway.", "", "", ""),
    "R6.4": ("Present", "MFA extended to all users on 10 September 2026.", "", "", ""),
    "S4.4": ("Present", "Employee notice cites section 7(i); other processing without consent is "
                        "mapped to named clauses.", "", "", ""),
    # Claimed, but nothing produced: the evidence gate strikes these.
    "R6.1": ("Present", "Management states the server is encrypted. Configuration not produced.",
             "Encryption configuration report to be produced.", "IT Head", "2026-10-15"),
    "R6.3": ("Present", "Access matrix stated to exist. Not made available during fieldwork.",
             "Access matrix to be shared after the quarterly review.", "IT Head", "2026-10-15"),
    "R7.1": ("Present", "Breach detection and escalation procedure referred to but not shared.",
             "Escalation procedure to be shared.", "IT Head", "2026-10-31"),
    "R6.5": ("Partial", "Application logs retained 90 days against the one-year minimum.",
             "Retention to be extended subject to storage approval.", "IT Head", "2026-11-30"),
    "R6.6": ("Partial", "Backups taken nightly; restore never tested.",
             "Quarterly restore test to be scheduled.", "IT Head", "2026-12-31"),
    "S4.2": ("Partial", "Consent is captured by an unticked box on the dealer portal; records hold "
                        "date and purpose but not the notice version.",
             "Notice version to be recorded against each consent from the next portal release.",
             "Head of Sales", "2026-11-30"),
    "R7.4": ("Absent", "", "Accepted. A breach response pack will be prepared with external support.",
             "CFO", "2027-01-31"),
    "S4.1": ("Absent", "Customers whose consent predates the Act have not been sent a section 5(2) notice.",
             "A section 5(2) notice will be sent to existing dealers and customers.",
             "Company Secretary", "2026-12-31"),
    "S4.3": ("Absent", "Withdrawal needs a signed letter, while consent is given by a tick box.",
             "An email withdrawal route will be added and processors instructed on each withdrawal.",
             "Head of Customer Service", "2026-11-30"),
}

EVIDENCE = {
    "R6.2": ("TLS_configuration_report.txt", "TLS configuration report for portal and mail gateway"),
    "R6.4": ("MFA_rollout_report.txt", "MFA rollout report"),
    "S4.2": ("Consent_form_and_sample_records.txt", "Consent form and sample consent records"),
    "S4.4": ("Employee_notice_s7i.txt", "Employee notice citing section 7(i)"),
}


def seed(target: Path, catalogue: list) -> str:
    """Write the sample into target/<SLUG>. Returns the slug. Refuses to overwrite."""
    folder = Path(target) / SLUG
    if (folder / "assessment.db").exists():
        raise SystemExit(f"The sample already exists: {folder}")
    p = Project(folder)
    try:
        p.save_client(Client(
            name="Meridian Textiles Private Limited (sample)",
            entity_type="Private Limited Company",
            sector="Manufacturing",
            contact_person="Head of Finance",
            role="fiduciary",
            assessed_by="Kaveri & Rao, Chartered Accountants (fictitious)",
            assessment_date="2026-09-15",
        ))
        finding = role.determine(ROLE_ANSWERS)
        p.set_role(finding.role, finding.reasoning)
        in_scope = {c.id for c in applicable(catalogue, finding.role, set())}

        for cid, (status, note, response, owner, target_date) in TABLE.items():
            if cid in in_scope:
                p.set_response(cid, status, note, response, owner, target_date)

        with tempfile.TemporaryDirectory() as tmp:
            for cid, (name, description) in EVIDENCE.items():
                if cid not in in_scope:
                    continue
                f = Path(tmp) / name
                f.write_text("Fictitious artefact created for the DPDP Readiness Assessor sample. "
                             "It names no real organisation or person.\n"
                             f"Supports control {cid}: {description}.\n", encoding="utf-8")
                p.add_evidence(cid, f, description)
    finally:
        p.close()
    return SLUG


def main() -> None:
    base = Path(__file__).resolve().parent
    parser = argparse.ArgumentParser(description="Build the fictitious sample assessment.")
    parser.add_argument("--clients-dir", default=str(base / "demo" / "clients"))
    args = parser.parse_args()
    target = Path(args.clients_dir).resolve()
    target.mkdir(parents=True, exist_ok=True)
    slug = seed(target, load_catalogue(base / "rules"))
    print(f"Sample written to {target / slug}")


if __name__ == "__main__":
    main()

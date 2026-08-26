"""
Application Configuration & DPDP Security Flags.
"""

import os

APP_TITLE = "Enterprise Forensic Audit & Benford's Law Suite (Indian DPDP Act, 2023 Compliant)"
APP_VERSION = "2.4.0-DPDP-PRO"
API_PREFIX = "/api"

# Security & Compliance Flags
ENFORCE_AIR_GAP_DEFAULT = True
MANDATORY_DISCLAIMER_CONSENT = True
MAX_UPLOAD_SIZE_MB = 250
DEFAULT_SESSION_SALT = os.getenv("DPDP_SESSION_SALT", "DPDP_2023_ENTERPRISE_AUDIT_SALT")

HOST = "127.0.0.1"
PORT = 8000

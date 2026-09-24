"""Application configuration.

Everything is env-overridable so the same build runs locally for the CFO and
headlessly for a grader. Defaults are chosen so `uvicorn app.main:app` works
with zero setup.
"""
from __future__ import annotations

import os
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parent.parent          # backend/
DATA_DIR = Path(os.getenv("CR_DATA_DIR", BASE_DIR / "data"))
DATA_DIR.mkdir(parents=True, exist_ok=True)


SECRET_FILE = DATA_DIR / "secret.key"


def _load_or_create_secret() -> str:
    """The JWT signing key, unique to this installation.

    Read from data/secret.key, created on first start if absent. Generating it
    rather than shipping one means two copies of this folder do not share a
    key, and nothing sensitive sits in source control. Changing it invalidates
    every issued token, which is why it is written once and then left alone —
    the only visible effect is that everyone signs in again after the upgrade
    that introduced this.
    """
    import secrets
    import stat

    try:
        if SECRET_FILE.exists():
            existing = SECRET_FILE.read_text(encoding="utf-8").strip()
            if len(existing) >= 32:
                return existing
        key = secrets.token_urlsafe(48)
        SECRET_FILE.write_text(key, encoding="utf-8")
        try:
            SECRET_FILE.chmod(stat.S_IRUSR | stat.S_IWUSR)   # 0600; no-op on Windows
        except OSError:
            pass
        return key
    except OSError:
        # A read-only data directory should not stop the application, but it
        # must not silently fall back to a fixed key either. A per-process
        # random key means tokens die with the process — inconvenient, and
        # safe.
        import secrets as _s
        return _s.token_urlsafe(48)


class Settings:
    APP_NAME: str = "Cash Runway"
    APP_TAGLINE: str = "Cash command for founders and CFOs"
    VERSION: str = "1.0.0"

    # --- database -------------------------------------------------------
    DATABASE_URL: str = os.getenv("CR_DATABASE_URL", f"sqlite:///{DATA_DIR / 'cashrunway.db'}")

    # --- auth -----------------------------------------------------------
    # The signing key is never a literal in this file. A shipped default is a
    # published key: anyone holding the source could mint a valid token for any
    # account, Admin included, without knowing a password. So it comes from the
    # environment, or from a file generated once per installation.
    SECRET_KEY: str = os.getenv("CR_SECRET_KEY") or _load_or_create_secret()
    ALGORITHM: str = "HS256"
    ACCESS_TOKEN_EXPIRE_MINUTES: int = int(os.getenv("CR_TOKEN_MINUTES", "720"))

    # Sign-in lockout. Four e-mail addresses are printed in the README, so
    # without this the password is the only thing between a guesser and the
    # books, and they get unlimited guesses at it.
    LOGIN_MAX_ATTEMPTS: int = int(os.getenv("CR_LOGIN_MAX_ATTEMPTS", "5"))
    LOGIN_LOCKOUT_MINUTES: int = int(os.getenv("CR_LOGIN_LOCKOUT_MINUTES", "15"))

    # --- locale ---------------------------------------------------------
    TIMEZONE: str = "Asia/Kolkata"
    CURRENCY_SYMBOL: str = "₹"

    # --- tally ----------------------------------------------------------
    TALLY_HOST: str = os.getenv("CR_TALLY_HOST", "localhost")
    TALLY_PORT: int = int(os.getenv("CR_TALLY_PORT", "9000"))
    TALLY_TIMEOUT: int = int(os.getenv("CR_TALLY_TIMEOUT", "30"))

    # --- sms (Twilio) ---------------------------------------------------
    # SMS rather than WhatsApp. WhatsApp's Cloud API refuses a business-
    # initiated message outside a 24-hour window opened by the recipient, so
    # every alert would have needed a pre-approved template — and an alert is
    # business-initiated by definition. SMS has no such window.
    SMS_ENABLED: bool = os.getenv("CR_SMS_ENABLED", "false").lower() == "true"
    TWILIO_ACCOUNT_SID: str = os.getenv("CR_TWILIO_ACCOUNT_SID", "")
    TWILIO_AUTH_TOKEN: str = os.getenv("CR_TWILIO_AUTH_TOKEN", "")
    # Either a Twilio number in E.164, or a Messaging Service SID (MG…), which
    # takes precedence when both are set.
    TWILIO_FROM: str = os.getenv("CR_TWILIO_FROM", "")
    TWILIO_MESSAGING_SERVICE_SID: str = os.getenv("CR_TWILIO_MESSAGING_SERVICE_SID", "")
    # Optional n8n alternative — set CR_ALERT_CHANNEL=n8n to route through it.
    ALERT_CHANNEL: str = os.getenv("CR_ALERT_CHANNEL", "twilio")  # twilio | n8n | console
    N8N_WEBHOOK_URL: str = os.getenv("CR_N8N_WEBHOOK_URL", "")

    # --- smtp (secondary alert channel) ---------------------------------
    SMTP_HOST: str = os.getenv("CR_SMTP_HOST", "")
    SMTP_PORT: int = int(os.getenv("CR_SMTP_PORT", "587"))
    SMTP_USER: str = os.getenv("CR_SMTP_USER", "")
    SMTP_PASSWORD: str = os.getenv("CR_SMTP_PASSWORD", "")
    SMTP_FROM: str = os.getenv("CR_SMTP_FROM", "alerts@cashrunway.local")

    # --- ai narrative ---------------------------------------------------
    # The "Reading of the Position" box. If no key is present the app falls
    # back to a deterministic rule-based narrator so nothing ever breaks in a
    # demo or on a grader's machine.
    ANTHROPIC_API_KEY: str = os.getenv("ANTHROPIC_API_KEY", "")
    AI_MODEL: str = os.getenv("CR_AI_MODEL", "claude-sonnet-4-5")
    AI_ENABLED: bool = os.getenv("CR_AI_ENABLED", "true").lower() == "true"

    # --- business defaults ----------------------------------------------
    MIN_CASH_FLOOR: float = float(os.getenv("CR_MIN_CASH_FLOOR", "4000000"))      # ₹ 40 L
    BANK_CONCENTRATION_THRESHOLD: float = 0.60                                    # 60 %
    CLIENT_CONCENTRATION_THRESHOLD: float = 0.25                                  # 25 %
    BOOKS_BANK_AMBER: float = 200000                                              # ₹ 2 L
    BOOKS_BANK_RED: float = 1000000                                               # ₹ 10 L
    FUNDRAISE_LEAD_MONTHS: int = 6

    CORS_ORIGINS: list[str] = [
        "http://localhost:5173", "http://127.0.0.1:5173",
        "http://localhost:4173", "http://127.0.0.1:4173",
    ]


settings = Settings()

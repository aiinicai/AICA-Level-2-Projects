"""
Application logging setup (distinct from the in-app `audit_log` business
table defined in the Blueprint — this is infrastructure/error logging,
not the review-workflow audit trail).

Stage 2 scope: a plain rotating file handler. No log-parsing, alerting,
or business logic here.
"""
import logging
from logging.handlers import RotatingFileHandler


def setup_logging(app):
    log_dir = app.config["LOG_DIR"]
    log_dir.mkdir(parents=True, exist_ok=True)

    handler = RotatingFileHandler(
        log_dir / "finsight.log", maxBytes=1_000_000, backupCount=5
    )
    handler.setLevel(app.config.get("LOG_LEVEL", "INFO"))
    formatter = logging.Formatter(
        "%(asctime)s %(levelname)s [%(name)s] %(message)s"
    )
    handler.setFormatter(formatter)

    app.logger.addHandler(handler)
    app.logger.setLevel(app.config.get("LOG_LEVEL", "INFO"))
    return app.logger

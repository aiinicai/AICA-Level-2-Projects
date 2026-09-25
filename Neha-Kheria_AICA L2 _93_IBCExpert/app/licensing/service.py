"""Centralized licence/feature decision service."""
from __future__ import annotations

import hashlib
import json
import sqlite3
from dataclasses import asdict
from datetime import datetime

from app.core.errors import LicenceError, LicenceRestrictedError
from app.core.time import Clock, SystemClock, to_utc_iso
from app.db.connection import transaction
from app.licensing.entitlement import Entitlement, verify_credentials
from app.licensing.trial import TrialService, TrialStatus

TRIAL_FEATURES = {
    "client_management", "legal_database", "ocr", "advanced_search",
    "recommendation_engine", "form_generation", "dashboard_analytics", "plugins",
}


class LicenseService:
    def __init__(
        self,
        connection: sqlite3.Connection,
        trial: TrialService,
        public_key: bytes,
        *,
        clock: Clock | None = None,
    ):
        if len(public_key) != 32:
            raise LicenceError("Owner public verification key is not configured correctly.")
        self.connection = connection
        self.trial = trial
        self.public_key = public_key
        self.clock = clock or SystemClock()

    def _active_row(self):
        return self.connection.execute(
            "SELECT * FROM licences WHERE status='ACTIVE' ORDER BY installed_at DESC LIMIT 1"
        ).fetchone()

    def _entitlement_from_row(self, row) -> Entitlement:
        return Entitlement.from_payload(row["signed_payload"].encode("utf-8"))

    def status(self) -> TrialStatus:
        row = self._active_row()
        if row:
            try:
                entitlement = verify_credentials(
                    row["activation_id"], row["signature"], self.public_key,
                    self.trial.check(False).request_code, self.clock.now(),
                )
                return self.trial.check(licensed=True)
            except LicenceError:
                self.connection.execute(
                    "UPDATE licences SET status='INVALID' WHERE id=?", (row["id"],)
                )
        return self.trial.check(licensed=False)

    def activate(self, activation_id: str, activation_code: str) -> Entitlement:
        trial_status = self.trial.check(False)
        entitlement = verify_credentials(
            activation_id, activation_code, self.public_key,
            trial_status.request_code, self.clock.now(),
        )
        payload_text = entitlement.payload().decode("utf-8")
        with transaction(self.connection):
            self.connection.execute("UPDATE licences SET status='REPLACED' WHERE status='ACTIVE'")
            cursor = self.connection.execute(
                """
                INSERT INTO licences(
                    licence_id,licence_type,customer_name,organisation,issued_at,starts_at,
                    expires_at,device_request_code,device_allowance,signed_payload,signature,
                    activation_id,status,installed_at,last_validated_at
                ) VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?,?,?)
                """,
                (
                    entitlement.licence_id, entitlement.licence_type,
                    entitlement.customer_name, entitlement.organisation,
                    entitlement.issued_at, entitlement.starts_at, entitlement.expires_at,
                    entitlement.device_request_code, entitlement.device_allowance,
                    payload_text, activation_code, activation_id, "ACTIVE",
                    to_utc_iso(self.clock.now()), to_utc_iso(self.clock.now()),
                ),
            )
            licence_db_id = int(cursor.lastrowid)
            self.connection.executemany(
                "INSERT INTO licence_features(licence_id,feature_key,enabled) VALUES(?,?,1)",
                [(licence_db_id, feature) for feature in entitlement.features],
            )
            self.connection.execute(
                """INSERT INTO licence_events(occurred_at,event_type,licence_id,summary,details_json)
                   VALUES(?,?,?,?,?)""",
                (to_utc_iso(self.clock.now()), "LICENCE_INSTALLED", entitlement.licence_id,
                 "Signed offline licence installed.", "{}"),
            )
        self.trial.check(licensed=True)
        return entitlement

    def has_feature(self, feature: str) -> bool:
        status = self.status()
        if not status.normal_use_allowed:
            return False
        row = self._active_row()
        if row:
            return self.connection.execute(
                """SELECT 1 FROM licence_features f
                   WHERE f.licence_id=? AND f.feature_key=? AND f.enabled=1""",
                (row["id"], feature),
            ).fetchone() is not None
        return feature in TRIAL_FEATURES

    def require_feature(self, feature: str) -> None:
        if not self.has_feature(feature):
            raise LicenceRestrictedError(
                f"The '{feature}' feature is unavailable under the current trial or licence."
            )

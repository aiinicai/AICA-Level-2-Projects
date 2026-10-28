"""Project state: everything needed to resume work. Saved as a gzip-compressed JSON file (.ctproj).
Source files are never modified; only their extracted content and file names are stored."""
from __future__ import annotations

import gzip
import json
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Optional

from .fx import FXSettings
from .models import GeneralLedger, TrialBalance, tb_from_dict, gl_from_dict, to_dict

PROJECT_VERSION = 1


@dataclass
class Settings:
    preparer: str = ""
    reviewer: str = ""
    include_dta: bool = False
    thresholds: dict = field(default_factory=dict)       # overrides for risk thresholds
    template_path: str = ""
    letterhead_path: str = ""
    output_dir: str = ""
    status: str = "DRAFT"


@dataclass
class Project:
    name: str = "New project"
    created: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    saved: str = ""
    fx: FXSettings = field(default_factory=FXSettings)
    fx_confirmed: bool = False
    tb: Optional[TrialBalance] = None
    gl: Optional[GeneralLedger] = None
    prior_tb: Optional[TrialBalance] = None
    tb_confirmed: bool = False
    answers: dict = field(default_factory=dict)
    mapping_overrides: dict = field(default_factory=dict)
    decisions: dict = field(default_factory=dict)        # adjustment id -> decision dict
    flag_responses: dict = field(default_factory=dict)   # risk flag id -> {"mgmt_response","reviewer_conclusion"}
    approvals: dict = field(default_factory=dict)        # e.g. {"translation_diff": True}
    supporting_files: list = field(default_factory=list)
    settings: Settings = field(default_factory=Settings)
    audit_log: list = field(default_factory=list)        # [{"time","action","detail"}]

    def log(self, action: str, detail: str = ""):
        self.audit_log.append({"time": datetime.now().isoformat(timespec="seconds"), "action": action, "detail": detail[:500]})

    def to_dict(self) -> dict:
        d = {
            "version": PROJECT_VERSION, "name": self.name, "created": self.created, "saved": datetime.now().isoformat(timespec="seconds"),
            "fx": asdict(self.fx), "fx_confirmed": self.fx_confirmed,
            "tb": to_dict(self.tb) if self.tb else None, "gl": to_dict(self.gl) if self.gl else None,
            "prior_tb": to_dict(self.prior_tb) if self.prior_tb else None, "tb_confirmed": self.tb_confirmed,
            "answers": self.answers, "mapping_overrides": self.mapping_overrides, "decisions": self.decisions,
            "flag_responses": self.flag_responses, "approvals": self.approvals, "supporting_files": self.supporting_files,
            "settings": asdict(self.settings), "audit_log": self.audit_log,
        }
        return d

    def save(self, path: str):
        with gzip.open(path, "wt", encoding="utf-8") as fh:
            json.dump(self.to_dict(), fh, default=str)

    @staticmethod
    def load(path: str) -> "Project":
        with gzip.open(path, "rt", encoding="utf-8") as fh:
            d = json.load(fh)
        p = Project(name=d.get("name", ""), created=d.get("created", ""), saved=d.get("saved", ""))
        p.fx = FXSettings(**d["fx"]) if d.get("fx") else FXSettings()
        p.fx_confirmed = d.get("fx_confirmed", False)
        p.tb = tb_from_dict(d["tb"]) if d.get("tb") else None
        p.gl = gl_from_dict(d["gl"]) if d.get("gl") else None
        p.prior_tb = tb_from_dict(d["prior_tb"]) if d.get("prior_tb") else None
        p.tb_confirmed = d.get("tb_confirmed", False)
        for k in ("answers", "mapping_overrides", "decisions", "flag_responses", "approvals", "supporting_files", "audit_log"):
            setattr(p, k, d.get(k, type(getattr(p, k))()))
        s = d.get("settings") or {}
        p.settings = Settings(**{k: v for k, v in s.items() if k in Settings.__dataclass_fields__})
        return p

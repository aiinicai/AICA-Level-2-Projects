from __future__ import annotations
from dataclasses import dataclass, field, asdict
from pathlib import Path
import yaml

SEV_ORDER = {"High": 0, "Medium": 1, "Low": 2, "Info": 3}


@dataclass
class Finding:
    check_id: str
    title: str
    severity: str            # High | Medium | Low | Info
    detail: str
    location: str = ""       # page / paragraph / table / cell reference = the evidence trail
    expected: str = ""
    found: str = ""

    def to_dict(self):
        return asdict(self)


@dataclass
class Result:
    check_id: str
    status: str              # PASS | EXC | NOTRUN
    findings: list = field(default_factory=list)
    note: str = ""           # reason for NOTRUN or context for PASS


def load_yaml(path):
    with open(path, "r", encoding="utf-8") as fh:
        return yaml.safe_load(fh)


ROOT = Path(__file__).resolve().parent.parent


def load_params():
    return load_yaml(ROOT / "rules" / "params.yaml")


def load_catalogue():
    return load_yaml(ROOT / "rules" / "catalogue.yaml")["checks"]

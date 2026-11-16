from dataclasses import asdict, dataclass, field
import hashlib
import json

KINDS = ("Economic", "Corporate", "Regulatory")
STATUSES = ("Scheduled", "Tentative", "Published", "Updated", "Postponed", "Cancelled")
IMPORTANCE = ("Unknown", "Low", "Medium", "High")
DATE_FIELDS = ("scheduled_at", "published_at", "effective_at", "deadline_at", "record_date", "ex_date", "source_updated_at")


@dataclass
class Event:
    source_id: str
    external_id: str
    kind: str
    title: str
    category: str
    country: str = ""
    authority: str = ""
    source_url: str = ""
    source_reference_kind: str = "document"
    status: str = "Published"
    importance: str = "Unknown"
    scheduled_at: str | None = None
    published_at: str | None = None
    effective_at: str | None = None
    deadline_at: str | None = None
    record_date: str | None = None
    ex_date: str | None = None
    source_updated_at: str | None = None
    source_timezone: str = ""
    date_confirmed: bool = True
    reporting_period: str = ""
    indicator: str = ""
    series_key: str = ""
    unit: str = ""
    previous: str | None = None
    forecast: str | None = None
    actual: str | None = None
    revised: str | None = None
    provider_forecast: str | None = None
    company: str = ""
    symbol: str = ""
    isin: str = ""
    exchange: str = ""
    summary: str = ""
    notice_number: str = ""
    supersedes_external_id: str = ""
    document_url: str = ""
    document_hash: str = ""
    sample: bool = False
    verification: str = "Source supplied"
    original_times: dict = field(default_factory=dict)

    def payload(self) -> dict:
        return asdict(self)

    def fingerprint(self) -> str:
        # Retrieval/update metadata changes alone do not constitute a material revision.
        data = self.payload()
        data.pop("source_updated_at", None)
        data["original_times"].pop("source_updated_at",None)
        return hashlib.sha256(json.dumps(data, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


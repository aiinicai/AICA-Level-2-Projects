from dataclasses import dataclass, field
from typing import List


@dataclass
class ReadResult:
    lines: list = field(default_factory=list)
    sheets: list = field(default_factory=list)          # every sheet read: {sheet, columns, header_row, mapping}
    needs_mapping: list = field(default_factory=list)   # [{"sheet":..., "columns":[...], "header_row":int}]
    messages: list = field(default_factory=list)
    kind: str = ""
    review_count: int = 0
    tables: dict = field(default_factory=dict)          # summary reports: rows in Master-Template form
    docs: list = field(default_factory=list)            # summary reports: document series (Table 13)

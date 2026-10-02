"""Regenerates the blank templates, filled samples and sample Tally XML.

    python -m scripts.generate_samples

Outputs:
    templates/<kind>_template.xlsx     blank templates (no ledger dropdowns; the app adds
                                       dropdowns from your synced masters when you download)
    samples/sample_<kind>.xlsx         filled examples matching the demo masters
    samples/sample_<kind>.xml          the Tally import XML those samples produce
"""
from __future__ import annotations

from pathlib import Path

from app.accounting.models import VoucherKind
from app.accounting.services import VoucherAssembler
from app.config.settings import PROJECT_ROOT, AppConfig
from app.excel.generator import TemplateLists, build_template
from app.excel.reader import read_workbook
from app.excel.samples import SAMPLE_ROWS
from app.excel.template_spec import SPECS
from app.excel.validator import parse_rows
from app.tally.client import DEMO_COMPANY, DEMO_MASTERS
from app.tally.masters import CachedMasters
from app.tally.xml_generator import TallyXmlGenerator

NAMES = {VoucherKind.SALES: "sales", VoucherKind.PURCHASE: "purchase", VoucherKind.JOURNAL: "journal",
         VoucherKind.RECEIPT: "receipt", VoucherKind.PAYMENT: "payment"}


def main() -> None:
    templates = PROJECT_ROOT / "templates"
    samples = PROJECT_ROOT / "samples"
    templates.mkdir(exist_ok=True)
    samples.mkdir(exist_ok=True)
    config = AppConfig(company_name=DEMO_COMPANY, company_state="Maharashtra", tally_company_name=DEMO_COMPANY,
                       financial_year="2026-27", demo_mode=True)
    masters = CachedMasters.from_records(DEMO_MASTERS)

    for kind, spec in SPECS.items():
        name = NAMES[kind]
        (templates / f"{name}_template.xlsx").write_bytes(build_template(spec, TemplateLists()))
        filled = build_template(spec, TemplateLists(), company_name=DEMO_COMPANY, financial_year="2026-27",
                                sample_rows=SAMPLE_ROWS[kind])
        (samples / f"sample_{name}.xlsx").write_bytes(filled)

        read = read_workbook(filled, spec, "sample.xlsx")
        parsed, issues = parse_rows(spec, read.rows)
        vouchers, asm_issues = VoucherAssembler(spec, config, masters).assemble(parsed)
        problems = [i for i in read.issues + issues + asm_issues if i.severity == "error"]
        if problems:
            raise SystemExit(f"Sample {name} has errors: {problems}")
        xml = TallyXmlGenerator(config).import_envelope(vouchers)
        (samples / f"sample_{name}.xml").write_bytes(xml)
        print(f"{name}: {len(vouchers)} voucher(s)")
    print(f"Written to {templates} and {samples}")


if __name__ == "__main__":
    main()

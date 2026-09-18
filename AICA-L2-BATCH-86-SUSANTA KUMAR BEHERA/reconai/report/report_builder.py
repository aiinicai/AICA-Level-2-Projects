from pathlib import Path
from typing import Optional, Union

from reconai.models.session import ReconciliationSession
from reconai.report.excel_exporter import ExcelReportExporter
from reconai.report.pdf_exporter import PDFReportExporter


class ReportBuilder:
    """Unified report exporter coordinating Excel and PDF generation."""

    def __init__(self):
        self.excel_exporter = ExcelReportExporter()
        self.pdf_exporter = PDFReportExporter()

    def export_excel(self, session: ReconciliationSession, output_path: Union[str, Path]) -> str:
        return self.excel_exporter.export(session, output_path)

    def export_pdf(self, session: ReconciliationSession, output_path: Union[str, Path]) -> str:
        return self.pdf_exporter.export(session, output_path)

    def export_all(
        self,
        session: ReconciliationSession,
        base_path: Union[str, Path],
    ) -> dict:
        base = Path(base_path)
        excel_path = base.with_suffix(".xlsx")
        pdf_path = base.with_suffix(".pdf")

        res_excel = self.export_excel(session, excel_path)
        res_pdf = self.export_pdf(session, pdf_path)
        return {"excel": res_excel, "pdf": res_pdf}

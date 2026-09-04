"""Background workers using QThread to keep UI completely responsive."""
from typing import Dict, Optional, Any
from PySide6.QtCore import QThread, Signal

from src.core.excel_parser import parse_workbook, WorkbookParseResult
from src.core.components import map_workbook_components, MappingDecision
from src.core.derivations import extract_period_financials, PeriodFinancials
from src.core.assumptions import resolve_principal_repayment, build_assumptions_registry, AssumptionItem
from src.core.calculator import compute_ratios, CalculationResultSet
from src.core.variance_engine import populate_reasons_for_results
from src.core.integrity import run_integrity_checks, IntegrityCheckResult
from src.core.audit import AuditLogger


class AnalysisWorker(QThread):
    """Background worker for parsing workbooks and computing ratio analysis."""
    progress = Signal(str)
    finished_success = Signal(object)  # dict with all computed objects
    finished_error = Signal(str)

    def __init__(
        self,
        cy_file_path: str,
        py_file_path: Optional[str],
        user_overrides: Optional[Dict[str, Any]] = None,
        threshold_pct: float = 25.0
    ):
        super().__init__()
        self.cy_file_path = cy_file_path
        self.py_file_path = py_file_path
        self.user_overrides = user_overrides or {}
        self.threshold_pct = threshold_pct

    def run(self):
        try:
            audit_logger = AuditLogger()
            
            # Step 1: Parse CY Workbook
            self.progress.emit("Parsing Current Year financial workbook...")
            cy_parse = parse_workbook(self.cy_file_path)
            audit_logger.log("FILE_UPLOAD", f"CY file loaded: {cy_parse.file_name} (SHA-256: {cy_parse.file_hash[:12]}...)")
            
            # Step 2: Parse PY Workbook if provided
            py_parse = None
            if self.py_file_path:
                self.progress.emit("Parsing Previous Year financial workbook...")
                py_parse = parse_workbook(self.py_file_path)
                audit_logger.log("FILE_UPLOAD", f"PY file loaded: {py_parse.file_name} (SHA-256: {py_parse.file_hash[:12]}...)")

            # Step 3: Map components and apply Rules 1-6
            self.progress.emit("Mapping line items to Schedule III components...")
            cy_map, cy_events = map_workbook_components(cy_parse, "CY")
            for ev in cy_events:
                audit_logger.log("RULE_APPLIED", ev)
                
            py_map = None
            if py_parse:
                py_map, py_events = map_workbook_components(py_parse, "PY")
                for ev in py_events:
                    audit_logger.log("RULE_APPLIED", ev)

            # Step 4: Extract period financials
            self.progress.emit("Computing derived sub-totals and opening/closing balances...")
            cy_closing = extract_period_financials(cy_map, "reporting", f"FY {cy_parse.reporting_year}")
            cy_opening = extract_period_financials(cy_map, "comparative", f"FY {cy_parse.comparative_year}" if cy_parse.comparative_year else "")
            
            if py_parse and py_map:
                py_closing = extract_period_financials(py_map, "reporting", f"FY {py_parse.reporting_year}")
                py_opening = extract_period_financials(py_map, "comparative", f"FY {py_parse.comparative_year}" if py_parse.comparative_year else "")
            else:
                # Fallback: single year CY comparative used as PY
                py_closing = cy_opening
                py_opening = cy_opening

            # Step 5: Resolve assumptions and principal repayment waterfall
            self.progress.emit("Resolving standard accounting assumptions and debt waterfall...")
            pr_result = resolve_principal_repayment(
                cy_closing, cy_opening, py_closing, py_opening,
                tolerance=self.user_overrides.get("materiality_tolerance", 0.05)
            )
            audit_logger.log("ASSUMPTION_APPLIED", f"CY Principal repayment: {pr_result.principal_repayment_cy:.2f} ({pr_result.basis_cy})")
            audit_logger.log("ASSUMPTION_APPLIED", f"PY Principal repayment: {pr_result.principal_repayment_py:.2f} ({pr_result.basis_py})")

            assumptions = build_assumptions_registry(
                user_overrides=self.user_overrides,
                pr_result=pr_result,
                closing_cy=cy_closing,
                closing_py=py_closing
            )

            # Step 6: Compute Ratios
            self.progress.emit("Computing 11 Schedule III ratios and variances...")
            result_set = compute_ratios(
                cy_closing, cy_opening, py_closing, py_opening,
                assumptions=assumptions,
                threshold_pct=self.threshold_pct
            )

            # Step 7: Driver decomposition reason generation
            self.progress.emit("Generating driver-decomposed variance explanations...")
            populate_reasons_for_results(
                result_set.schedule_iii_ratios,
                cy_closing, cy_opening, py_closing, py_opening,
                units=cy_parse.units
            )

            # Step 8: Automated Integrity Checks
            self.progress.emit("Running automated integrity and articulation checks...")
            integrity_results = run_integrity_checks(
                cy_parse=cy_parse,
                py_parse=py_parse,
                cy_map=cy_map,
                py_map=py_map,
                cy_closing=cy_closing,
                cy_opening=cy_opening,
                py_closing=py_closing,
                py_opening=py_opening,
                tolerance=assumptions["materiality_tolerance"].value_cy
            )
            for ic in integrity_results:
                if ic.status == "Fail":
                    audit_logger.log("INTEGRITY_CHECK", f"Check {ic.check_id} FAILED: {ic.comment}")

            payload = {
                "cy_parse": cy_parse,
                "py_parse": py_parse,
                "cy_map": cy_map,
                "py_map": py_map,
                "cy_closing": cy_closing,
                "cy_opening": cy_opening,
                "py_closing": py_closing,
                "py_opening": py_opening,
                "assumptions": assumptions,
                "pr_result": pr_result,
                "result_set": result_set,
                "integrity_results": integrity_results,
                "audit_logger": audit_logger,
                "is_single_year": (py_parse is None)
            }
            self.finished_success.emit(payload)

        except Exception as e:
            self.finished_error.emit(str(e))

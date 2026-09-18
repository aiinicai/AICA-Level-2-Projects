"""
AI Auditor V8 - Comprehensive Automated Test Suite
Tests extraction, mapping, ratios, variance, risks, Excel generation, and Word generation.
"""

import os
import unittest
from extraction.excel_extractor import ExcelExtractor
from extraction.pdf_extractor import PDFExtractor
from analysis.mapper import TaxonomyMapper
from analysis.ratio_engine import RatioEngine
from analysis.trend_engine import TrendEngine
from analysis.variance_engine import VarianceEngine
from analysis.risk_engine import RiskEngine
from reports.excel_generator import ExcelReportGenerator
from reports.word_generator import WordReportGenerator
from reports.chart_generator import ChartGenerator

class TestAIAuditorV8(unittest.TestCase):

    @classmethod
    def setUpClass(cls):
        cls.samples_dir = os.path.join(os.path.dirname(__file__), "..", "samples")
        cls.excel_path = os.path.join(cls.samples_dir, "sample_manufacturing_financial_statements.xlsx")
        cls.pdf_path = os.path.join(cls.samples_dir, "sample_trading_financial_statements.pdf")
        cls.out_dir = os.path.join(os.path.dirname(__file__), "..", "test_output")
        os.makedirs(cls.out_dir, exist_ok=True)

    def test_01_excel_extraction_and_mapping(self):
        self.assertTrue(os.path.exists(self.excel_path), "Excel sample file missing")
        extractor = ExcelExtractor(self.excel_path)
        model = extractor.extract()
        
        self.assertGreater(len(model.balance_sheet.line_items), 5, "Balance sheet line items should be > 5")
        self.assertGreater(len(model.profit_loss.line_items), 5, "P&L line items should be > 5")
        self.assertGreater(len(model.cash_flow.line_items), 2, "Cash flow line items should be > 2")
        
        # Apply Taxonomy Mapping
        TaxonomyMapper.map_model(model)
        rev_item = model.profit_loss.get_item_by_standard_key("revenue_operations")
        self.assertIsNotNone(rev_item, "Revenue from operations should be mapped")
        self.assertEqual(rev_item.get_value("FY 2023-24"), 14500.00)

    def test_02_pdf_extraction(self):
        self.assertTrue(os.path.exists(self.pdf_path), "PDF sample file missing")
        extractor = PDFExtractor(self.pdf_path)
        model = extractor.extract()
        TaxonomyMapper.map_model(model)
        self.assertGreater(len(model.balance_sheet.line_items) + len(model.profit_loss.line_items), 5, "Extracted PDF items should be > 5")

    def test_03_ratio_calculations(self):
        extractor = ExcelExtractor(self.excel_path)
        model = extractor.extract()
        TaxonomyMapper.map_model(model)
        
        ratios = RatioEngine.calculate_all_ratios(model)
        self.assertIn("Liquidity Ratios", ratios)
        self.assertIn("Profitability Ratios", ratios)
        self.assertIn("Solvency & Leverage Ratios", ratios)
        self.assertIn("Activity & Efficiency Ratios", ratios)
        
        # Check Current Ratio
        cr_item = next((r for r in ratios["Liquidity Ratios"] if r["name"] == "Current Ratio"), None)
        self.assertIsNotNone(cr_item)
        self.assertGreater(cr_item["current_value"], 1.0, "Current ratio should be > 1.0")

    def test_04_variance_and_reasons(self):
        extractor = ExcelExtractor(self.excel_path)
        model = extractor.extract()
        TaxonomyMapper.map_model(model)
        RatioEngine.calculate_all_ratios(model)
        
        variations = VarianceEngine.analyze_variations(model, threshold_pct=5.0)
        self.assertGreater(len(variations), 0, "Should detect variations >= 5%")
        for v in variations:
            self.assertIn("possible_reasons", v)
            self.assertIn("audit_verification", v)
            self.assertGreater(len(v["possible_reasons"]), 0)

    def test_05_risk_engine(self):
        extractor = ExcelExtractor(self.excel_path)
        model = extractor.extract()
        TaxonomyMapper.map_model(model)
        RatioEngine.calculate_all_ratios(model)
        
        risks = RiskEngine.evaluate_risks(model)
        self.assertIsInstance(risks, list)

    def test_06_report_generation(self):
        extractor = ExcelExtractor(self.excel_path)
        model = extractor.extract()
        TaxonomyMapper.map_model(model)
        RatioEngine.calculate_all_ratios(model)
        VarianceEngine.analyze_variations(model, threshold_pct=5.0)
        RiskEngine.evaluate_risks(model)
        
        # Excel
        excel_out = os.path.join(self.out_dir, "test_audit_report.xlsx")
        gen_xl = ExcelReportGenerator(model)
        gen_xl.generate(excel_out)
        self.assertTrue(os.path.exists(excel_out), "Excel report should be generated")
        self.assertGreater(os.path.getsize(excel_out), 5000, "Excel file size should be > 5KB")
        
        # Word
        word_out = os.path.join(self.out_dir, "test_audit_report.docx")
        gen_wd = WordReportGenerator(model)
        gen_wd.generate(word_out)
        self.assertTrue(os.path.exists(word_out), "Word report should be generated")
        self.assertGreater(os.path.getsize(word_out), 5000, "Word file size should be > 5KB")

if __name__ == "__main__":
    unittest.main()

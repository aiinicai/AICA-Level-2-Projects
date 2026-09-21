#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Automated Test Suite for MF X-Ray V1.0
ICAI AI Level 2 Capstone Project
"""
import sys
import os
import unittest
from datetime import date, timedelta
import pandas as pd
import numpy as np

if hasattr(sys.stdout, "reconfigure"):
    sys.stdout.reconfigure(encoding="utf-8")

import MF_XRay_V1 as app


class TestMFXRayV1(unittest.TestCase):

    def setUp(self):
        self.portfolio = app.demo_portfolio()
        self.metrics = app.compute_all_metrics(self.portfolio, 6.0)

    def test_app_metadata(self):
        self.assertEqual(app.APP_VERSION, "V1.0")
        self.assertEqual(app.APP_NAME, "MF X-Ray")
        self.assertIn("MF X-RAY", app.APP_FULL_TITLE)
        self.assertIn("NOT LIVE MARKET DATA", app.DEMO_DATA_LABEL)
        print("PASS: App metadata and version verified (V1.0)")

    def test_demo_portfolio_basics(self):
        self.assertEqual(len(self.portfolio.entries), 4)
        self.assertEqual(self.portfolio.total_investment(), 900000.0)
        self.assertEqual(self.metrics["total_investment"], 900000.0)
        alloc = self.metrics["allocation_df"]
        self.assertAlmostEqual(alloc["Allocation %"].sum(), 100.0, places=2)
        print(f"PASS: Demo portfolio total = {self.metrics['total_investment']} (4 funds, sum=100%)")

    def test_worked_example_math(self):
        meta_a = {"category": "Large Cap", "nav": 10.0, "aum_cr": 1000, "expense_ratio_pct": 1.0,
                  "return_1y_pct": 10, "cagr_3y_pct": 12, "cagr_5y_pct": 10, "risk_level": "Moderate",
                  "equity_pct": 100, "debt_pct": 0, "cash_pct": 0, "benchmark": "Nifty 50", "portfolio_date": date.today()}
        meta_b = meta_a.copy()
        holdings_a = {"Company Alpha": 10.0, "Company Beta": 90.0}
        holdings_b = {"Company Alpha": 8.0, "Company Gamma": 92.0}
        
        fund_a = app.Fund("Test Fund A", meta_a, holdings_a)
        fund_b = app.Fund("Test Fund B", meta_b, holdings_b)
        
        app.FUNDS["Test Fund A"] = fund_a
        app.FUNDS["Test Fund B"] = fund_b
        
        custom_p = app.Portfolio()
        custom_p.add("Test Fund A", 500000.0)
        custom_p.add("Test Fund B", 500000.0)
        
        m = app.compute_all_metrics(custom_p, 6.0)
        exp_df = m["exposure_df"]
        alpha_row = exp_df[exp_df["Company"] == "Company Alpha"].iloc[0]
        
        self.assertAlmostEqual(alpha_row["Exposure Amount"], 90000.0, places=2)
        self.assertAlmostEqual(alpha_row["Effective Exposure %"], 9.0, places=2)
        self.assertEqual(alpha_row["Number of Funds"], 2)
        print("PASS: Section 35 Worked Example Math Verified: 50k + 40k = 90k (9.0% on 10,00,000 portfolio)")
        
        del app.FUNDS["Test Fund A"]
        del app.FUNDS["Test Fund B"]

    def test_effective_exposure(self):
        exp = self.metrics["exposure_df"]
        self.assertFalse(exp.empty)
        pcts = exp["Effective Exposure %"].tolist()
        self.assertEqual(pcts, sorted(pcts, reverse=True))
        top = exp.iloc[0]
        self.assertTrue(top["Effective Exposure %"] > 0)
        print(f"PASS: Effective exposure verified. Top holding: {top['Company']} at {top['Effective Exposure %']:.2f}%")

    def test_overlap_matrix(self):
        matrix = self.metrics["overlap_matrix"]
        self.assertEqual(matrix.shape[0], matrix.shape[1])
        for fund in matrix.index:
            self.assertAlmostEqual(matrix.loc[fund, fund], 100.0, places=1)
        for f1 in matrix.index:
            for f2 in matrix.columns:
                self.assertAlmostEqual(matrix.loc[f1, f2], matrix.loc[f2, f1], places=2)
        print("PASS: Overlap Matrix verified (symmetric, 100% diagonal)")

    def test_sector_exposure(self):
        sec = self.metrics["sector_df"]
        self.assertFalse(sec.empty)
        sec_pcts = sec["Effective Exposure %"].tolist()
        self.assertEqual(sec_pcts, sorted(sec_pcts, reverse=True))
        print(f"PASS: Sector exposure verified. Top sector: {sec.iloc[0]['Sector']} at {sec.iloc[0]['Effective Exposure %']:.2f}%")

    def test_risk_metrics(self):
        risk = self.metrics["risk"]
        self.assertIn("volatility_pct", risk)
        self.assertIn("sharpe_ratio", risk)
        self.assertIn("max_drawdown_pct", risk)
        self.assertTrue(risk["volatility_pct"] > 0)
        self.assertTrue(risk["max_drawdown_pct"] <= 0)
        print(f"PASS: Risk metrics verified: Volatility={risk['volatility_pct']:.2f}%, Sharpe={risk['sharpe_ratio']:.2f}, MaxDD={risk['max_drawdown_pct']:.2f}%")

    def test_health_score_breakdown(self):
        h = self.metrics["health"]
        self.assertTrue(0 <= h["total"] <= 100)
        comp_sum = round(sum(h["components"].values()))
        self.assertEqual(h["total"], comp_sum)
        expected_keys = {"diversification", "overlap", "stock_concentration", "sector_concentration", "volatility", "drawdown"}
        self.assertEqual(set(h["components"].keys()), expected_keys)
        print(f"PASS: Health score verified ({h['total']}/100 with 6 transparent components summing to total)")

    def test_ai_insights_narrative(self):
        narrative = app.generate_ai_narrative(self.metrics)
        self.assertIn("Your portfolio contains", narrative)
        self.assertIn("Portfolio Health Score", narrative)
        for forbidden in ["BUY", "SELL", "HOLD", "switch to"]:
            self.assertNotIn(forbidden, narrative.lower())
        print("PASS: AI Insight narrative generated without unsolicited advice")

    def test_ask_mf_xray_qa(self):
        ans1 = app.answer_question("Which companies have the highest exposure?", self.metrics)
        self.assertIn("The highest effective exposures are", ans1)

        ans2 = app.answer_question("Which funds overlap the most?", self.metrics)
        self.assertIn("overlap the most", ans2)

        ans3 = app.answer_question("Which sector has the highest exposure?", self.metrics)
        self.assertIn("highest effective exposure", ans3)

        ans4 = app.answer_question("Which funds contain Northbridge Bank?", self.metrics)
        self.assertIn("Northbridge Bank", ans4)
        self.assertIn("held by", ans4)

        ans5 = app.answer_question("Why is my portfolio concentrated?", self.metrics)
        self.assertIn("concentrated primarily", ans5)

        ans6 = app.answer_question("Explain my portfolio like a CA.", self.metrics)
        self.assertIn("CA Portfolio Intelligence Summary", ans6)

        ans7 = app.answer_question("What is the weather today?", self.metrics)
        self.assertIn("Insufficient data available", ans7)
        print("PASS: Ask MF X-Ray natural language Q&A engine passed all query tests")

    def test_whatif_simulator(self):
        fund_to_remove = self.portfolio.entries[0].fund_name
        sim = app.simulate_remove_fund(self.portfolio, fund_to_remove, 6.0)
        self.assertEqual(sim["removed_fund"], fund_to_remove)
        self.assertLess(sim["after"]["total_investment"], sim["before"]["total_investment"])
        row_b = app.whatif_summary_row("Before", sim["before"])
        row_a = app.whatif_summary_row("After", sim["after"])
        self.assertIn("Health Score", row_b)
        self.assertIn("Health Score", row_a)
        print(f"PASS: What-If simulation verified for removing {fund_to_remove}")

    def test_sip_xirr(self):
        fund_name = list(app.FUNDS.keys())[0]
        start_date = (date.today().replace(day=1) - timedelta(days=730)).strftime("%d-%m-%Y")
        res = app.simulate_sip(fund_name, 10000, start_date, 24)
        self.assertEqual(res["invested_total"], 240000)
        self.assertTrue(res["units"] > 0)
        self.assertTrue(res["current_value"] > 0)
        self.assertIsNotNone(res["xirr_pct"])
        print(f"PASS: SIP simulation verified: Invested=2.4L, Units={res['units']:.2f}, XIRR={res['xirr_pct']:.2f}%")

    def test_excel_export(self):
        out_path = "test_export_mf_xray.xlsx"
        try:
            app.export_to_excel(out_path, self.portfolio, self.metrics)
            self.assertTrue(os.path.exists(out_path))
            import openpyxl
            wb = openpyxl.load_workbook(out_path)
            expected_sheets = [
                "Portfolio Summary", "Fund Allocation", "Fund Analysis", "Underlying Holdings",
                "Stock Exposure (X-Ray)", "Overlap Analysis", "Sector Analysis", "Risk Analysis",
                "Alerts", "AI Insights", "Methodology"
            ]
            for s in expected_sheets:
                self.assertIn(s, wb.sheetnames)
            wb.close()
            print(f"PASS: Excel export verified ({len(expected_sheets)} sheets match specifications)")
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)

    def test_word_export(self):
        out_path = "test_export_mf_xray.docx"
        try:
            app.export_to_word(out_path, self.portfolio, self.metrics)
            self.assertTrue(os.path.exists(out_path))
            from docx import Document
            doc = Document(out_path)
            headings = [p.text for p in doc.paragraphs if p.text]
            self.assertIn("Executive Summary", headings)
            self.assertIn("Portfolio Overview", headings)
            self.assertIn("Overlap Analysis", headings)
            self.assertIn("Methodology", headings)
            self.assertIn("Disclaimer", headings)
            print("PASS: Word report export verified (.docx with complete sections)")
        finally:
            if os.path.exists(out_path):
                os.remove(out_path)


if __name__ == "__main__":
    unittest.main(verbosity=2)

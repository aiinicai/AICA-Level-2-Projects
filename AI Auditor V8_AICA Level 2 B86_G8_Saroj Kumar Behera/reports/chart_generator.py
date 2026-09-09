"""
AI Auditor V8 - Chart Visualizer & Asset Generator
Generates clean, professional charts using Matplotlib for GUI display and Report integration.
"""

import os
import matplotlib
matplotlib.use('Agg')  # Non-interactive background renderer
import matplotlib.pyplot as plt
import numpy as np
from typing import Dict, List, Any, Optional
from core.models import FinancialModel

class ChartGenerator:

    @classmethod
    def generate_all_charts(cls, model: FinancialModel, output_dir: str = "temp_charts") -> Dict[str, str]:
        """Generates a suite of financial summary charts and saves them as PNG files."""
        os.makedirs(output_dir, exist_ok=True)
        chart_paths = {}

        # Style configuration
        plt.style.use('seaborn-v0_8-whitegrid' if 'seaborn-v0_8-whitegrid' in plt.style.available else 'default')
        plt.rcParams['font.sans-serif'] = 'Segoe UI, Arial, sans-serif'
        plt.rcParams['axes.edgecolor'] = '#CCCCCC'
        plt.rcParams['axes.linewidth'] = 0.8

        periods = model.periods
        if not periods:
            return chart_paths

        curr_p = periods[0]
        prev_p = periods[1] if len(periods) > 1 else None

        # 1. Performance Overview (Revenue, EBITDA, PAT)
        p1 = cls._generate_performance_chart(model, curr_p, prev_p, os.path.join(output_dir, "performance_summary.png"))
        if p1: chart_paths["performance"] = p1

        # 2. Key Ratios Radar / Bar Chart
        p2 = cls._generate_ratios_chart(model, os.path.join(output_dir, "ratios_summary.png"))
        if p2: chart_paths["ratios"] = p2

        # 3. Capital Structure / Assets vs Debt
        p3 = cls._generate_capital_structure_chart(model, curr_p, prev_p, os.path.join(output_dir, "capital_structure.png"))
        if p3: chart_paths["capital"] = p3

        return chart_paths

    @classmethod
    def _generate_performance_chart(cls, model: FinancialModel, curr_p: str, prev_p: Optional[str], save_path: str) -> Optional[str]:
        try:
            fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
            
            categories = ['Revenue', 'EBITDA', 'Profit After Tax']
            
            def get_val(key, p):
                if not p: return 0.0
                if key == "EBITDA":
                    pbt = model.profit_loss.get_value_by_key("profit_before_tax", p, 0.0)
                    fin = model.profit_loss.get_value_by_key("finance_costs", p, 0.0)
                    dep = model.profit_loss.get_value_by_key("depreciation_amortisation", p, 0.0)
                    return pbt + fin + dep
                return model.profit_loss.get_value_by_key(key, p, 0.0)

            cy_vals = [
                get_val("revenue_operations", curr_p),
                get_val("EBITDA", curr_p),
                get_val("profit_after_tax", curr_p)
            ]

            x = np.arange(len(categories))
            width = 0.35

            if prev_p:
                py_vals = [
                    get_val("revenue_operations", prev_p),
                    get_val("EBITDA", prev_p),
                    get_val("profit_after_tax", prev_p)
                ]
                ax.bar(x - width/2, py_vals, width, label=prev_p, color='#718096', alpha=0.9, edgecolor='none', zorder=3)
                ax.bar(x + width/2, cy_vals, width, label=curr_p, color='#1A365D', alpha=0.95, edgecolor='none', zorder=3)
            else:
                ax.bar(x, cy_vals, width, label=curr_p, color='#1A365D', alpha=0.95, edgecolor='none', zorder=3)

            ax.set_title(f"Financial Performance Summary ({model.company_info.unit_label})", fontsize=11, fontweight='bold', color='#1A202C', pad=12)
            ax.set_xticks(x)
            ax.set_xticklabels(categories, fontsize=9, fontweight='semibold')
            ax.legend(frameon=True, facecolor='white', edgecolor='#E2E8F0', fontsize=8)
            ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

            # Value labels on top of bars
            for p in ax.patches:
                val = p.get_height()
                if val != 0:
                    ax.annotate(f"{val:,.1f}",
                                (p.get_x() + p.get_width() / 2., val),
                                ha='center', va='bottom' if val >= 0 else 'top',
                                fontsize=8, color='#2D3748',
                                xytext=(0, 3 if val >= 0 else -8),
                                textcoords='offset points')

            fig.tight_layout()
            fig.savefig(save_path, bbox_inches='tight')
            plt.close(fig)
            return save_path
        except Exception as e:
            print(f"Error generating performance chart: {e}")
            return None

    @classmethod
    def _generate_ratios_chart(cls, model: FinancialModel, save_path: str) -> Optional[str]:
        try:
            if not model.ratios:
                return None

            fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
            
            selected_names = ["Current Ratio", "Debt-Equity Ratio", "Interest Coverage Ratio", "Net Profit (PAT) Margin", "Return on Capital Employed (ROCE)"]
            labels = []
            cy_vals = []
            py_vals = []

            for cat, r_list in model.ratios.items():
                for r in r_list:
                    if r["name"] in selected_names:
                        short_name = r["name"].replace("Ratio", "").replace("Margin", "Margin").replace("(PAT)", "").strip()
                        labels.append(short_name)
                        cy_vals.append(r["current_value"] or 0.0)
                        py_vals.append(r["previous_value"] or 0.0)

            if not labels:
                return None

            y = np.arange(len(labels))
            height = 0.35

            ax.barh(y - height/2, py_vals, height, label=model.periods[1] if len(model.periods)>1 else "Prior", color='#A0AEC0', alpha=0.9, zorder=3)
            ax.barh(y + height/2, cy_vals, height, label=model.periods[0], color='#2B6CB0', alpha=0.95, zorder=3)

            ax.set_title("Key Financial Ratios Comparison", fontsize=11, fontweight='bold', color='#1A202C', pad=12)
            ax.set_yticks(y)
            ax.set_yticklabels(labels, fontsize=9, fontweight='semibold')
            ax.legend(frameon=True, facecolor='white', edgecolor='#E2E8F0', fontsize=8)
            ax.grid(axis='x', linestyle='--', alpha=0.5, zorder=0)

            fig.tight_layout()
            fig.savefig(save_path, bbox_inches='tight')
            plt.close(fig)
            return save_path
        except Exception as e:
            print(f"Error generating ratios chart: {e}")
            return None

    @classmethod
    def _generate_capital_structure_chart(cls, model: FinancialModel, curr_p: str, prev_p: Optional[str], save_path: str) -> Optional[str]:
        try:
            fig, ax = plt.subplots(figsize=(7, 4.2), dpi=150)
            
            def bs_val(k, p):
                return model.balance_sheet.get_value_by_key(k, p, 0.0) if p else 0.0

            eq_cy = bs_val("share_capital", curr_p) + bs_val("reserves_surplus", curr_p)
            debt_cy = bs_val("long_term_borrowings", curr_p) + bs_val("short_term_borrowings", curr_p)
            ca_cy = bs_val("inventories", curr_p) + bs_val("trade_receivables", curr_p) + bs_val("cash_and_bank", curr_p)
            nca_cy = bs_val("property_plant_equipment", curr_p) + bs_val("non_current_investments", curr_p)

            items = ['Net Worth', 'Total Debt', 'Fixed/Non-Current Assets', 'Current Assets']
            vals = [eq_cy, debt_cy, nca_cy, ca_cy]
            colors = ['#2B6CB0', '#C53030', '#2F855A', '#D69E2E']

            x = np.arange(len(items))
            ax.bar(x, vals, color=colors, width=0.5, alpha=0.9, zorder=3)

            ax.set_title(f"Balance Sheet Capital & Asset Profile - {curr_p}", fontsize=11, fontweight='bold', color='#1A202C', pad=12)
            ax.set_xticks(x)
            ax.set_xticklabels(items, fontsize=8.5, fontweight='semibold', rotation=10)
            ax.grid(axis='y', linestyle='--', alpha=0.5, zorder=0)

            for p in ax.patches:
                val = p.get_height()
                if val != 0:
                    ax.annotate(f"{val:,.1f}",
                                (p.get_x() + p.get_width() / 2., val),
                                ha='center', va='bottom',
                                fontsize=8, color='#2D3748',
                                xytext=(0, 3), textcoords='offset points')

            fig.tight_layout()
            fig.savefig(save_path, bbox_inches='tight')
            plt.close(fig)
            return save_path
        except Exception as e:
            print(f"Error generating capital structure chart: {e}")
            return None

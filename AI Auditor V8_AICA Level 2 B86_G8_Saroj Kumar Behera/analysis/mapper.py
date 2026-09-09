"""
AI Auditor V8 - Financial Statement Taxonomy Mapper
Maps raw extracted line items to standard Schedule III / Ind AS / IFRS taxonomy keys using RapidFuzz heuristics.
"""

from typing import Dict, List, Tuple, Optional, Any
from rapidfuzz import process, fuzz
from config.constants import (
    BS_TAXONOMY, PL_TAXONOMY, CF_TAXONOMY,
    STATEMENT_BALANCE_SHEET, STATEMENT_PROFIT_LOSS, STATEMENT_CASH_FLOW
)
from core.models import FinancialModel, LineItem, FinancialStatement

class TaxonomyMapper:
    
    @classmethod
    def map_model(cls, model: FinancialModel) -> FinancialModel:
        """Applies heuristic taxonomy mapping across all statements in the model."""
        cls.map_statement(model.balance_sheet, BS_TAXONOMY)
        cls.map_statement(model.profit_loss, PL_TAXONOMY)
        cls.map_statement(model.cash_flow, CF_TAXONOMY)
        return model

    @classmethod
    def map_statement(cls, stmt: FinancialStatement, taxonomy: Dict[str, Any]):
        """Maps line items within a statement to taxonomy keys."""
        # Build lookup list of (standard_key, synonym, category)
        choices = []
        synonym_to_key = {}
        for key, details in taxonomy.items():
            for syn in details["synonyms"]:
                choices.append(syn)
                synonym_to_key[syn] = (key, details["category"])

        for item in stmt.line_items:
            if item.user_overridden:
                continue  # Preserve user manual selection
                
            clean_name = item.original_name.lower().strip()
            # Direct exact match check
            matched_key = None
            category = "General"
            best_score = 0.0
            
            for syn, (k, cat) in synonym_to_key.items():
                if syn == clean_name:
                    matched_key = k
                    category = cat
                    best_score = 1.0
                    break
                    
            if not matched_key and choices:
                # RapidFuzz fuzzy match
                match_result = process.extractOne(
                    clean_name, choices, scorer=fuzz.token_sort_ratio
                )
                if match_result:
                    match_syn, score, _ = match_result
                    if score >= 70.0:  # 70% match threshold
                        matched_key, category = synonym_to_key[match_syn]
                        best_score = score / 100.0

            if matched_key:
                item.standard_key = matched_key
                item.category = category
                item.confidence_score = best_score
            else:
                item.category = "Unclassified / Other"
                item.confidence_score = 0.0

    @classmethod
    def get_taxonomy_labels_for_statement(cls, statement_type: str) -> List[Tuple[str, str]]:
        """Returns list of (standard_key, user_friendly_label) for dropdowns in GUI."""
        if "balance" in statement_type.lower():
            tax = BS_TAXONOMY
        elif "profit" in statement_type.lower() or "loss" in statement_type.lower():
            tax = PL_TAXONOMY
        elif "cash" in statement_type.lower():
            tax = CF_TAXONOMY
        else:
            return [("unclassified", "Unclassified / Custom Line Item")]

        options = [("unclassified", "-- Unclassified / Other --")]
        for k, v in tax.items():
            options.append((k, f"{v['label']} ({v['category']})"))
        return options

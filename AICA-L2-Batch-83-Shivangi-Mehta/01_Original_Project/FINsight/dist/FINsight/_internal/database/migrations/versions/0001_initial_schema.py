"""initial schema

Revision ID: 0001
Revises:
Create Date: 2026-08-22

Hand-authored (see database/migrations/versions/README.md for why this
wasn't produced by --autogenerate: Alembic/SQLAlchemy could not be
installed in the delivery sandbox). Mirrors app/models/*.py field-for-
field as of the Stage 3 review-round-2 corrections:
  - exceptions.supporting_file_id REMOVED (see documentation/
    db_constraints.md, "Document <-> Exception/Query relationship").
  - NOT NULL / UNIQUE / indexes added per documentation/db_constraints.md.

Table creation order is a genuine dependency-respecting topological sort
(not just declaration order) — in particular exceptions -> queries ->
documents, since documents references both of the other two and, before
the supporting_file_id removal, that relationship was circular.

No accounting/audit/tax/SEBI rule CONTENT is inserted here — this
migration only creates the empty rule tables (schema), per Stage 3
condition #5.
"""
from typing import Sequence, Union

from alembic import op
import sqlalchemy as sa

# revision identifiers, used by Alembic.
revision: str = "0001"
down_revision: Union[str, None] = None
branch_labels: Union[str, Sequence[str], None] = None
depends_on: Union[str, Sequence[str], None] = None


def upgrade() -> None:
    op.create_table(
        "engagements",
        sa.Column("engagement_id", sa.Integer, primary_key=True),
        sa.Column("entity_name", sa.String, nullable=False),
        sa.Column("financial_year", sa.String, nullable=False),
        sa.Column("status", sa.String, nullable=False, server_default="DRAFT"),
        sa.Column("created_at", sa.String, nullable=False),
        sa.Column("updated_at", sa.String, nullable=False),
        sa.Column("created_by", sa.String, nullable=True),
    )

    op.create_table(
        "entity_profiles",
        sa.Column("profile_id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("entity_type", sa.String, nullable=False),
        sa.Column("industry", sa.String, nullable=True),
        sa.Column("is_listed", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("accounting_framework", sa.String, nullable=False),
        sa.Column("turnover", sa.Integer, nullable=True),
        sa.Column("is_gst_registered", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("statutory_audit_applicable", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("tax_audit_status", sa.String, nullable=False, server_default="REQUIRES_REVIEW"),
        sa.Column("consolidated_fs_applicable", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("prior_year_data_available", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("overall_materiality", sa.Integer, nullable=True),
        sa.Column("performance_materiality", sa.Integer, nullable=True),
        sa.Column("clearly_trivial_threshold", sa.Integer, nullable=True),
        sa.UniqueConstraint("engagement_id", name="uq_entity_profiles_engagement_id"),
    )

    op.create_table(
        "applicability",
        sa.Column("applicability_id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("area", sa.String, nullable=False),
        sa.Column("system_suggested_status", sa.String, nullable=False),
        sa.Column("system_suggested_reason", sa.String, nullable=True),
        sa.Column("user_confirmed_status", sa.String, nullable=True),
        sa.Column("user_confirmation_note", sa.String, nullable=True),
        sa.Column("confirmed_by", sa.String, nullable=True),
        sa.Column("confirmed_at", sa.String, nullable=True),
        sa.UniqueConstraint("engagement_id", "area", name="uq_applicability_engagement_area"),
    )

    op.create_table(
        "uploaded_files",
        sa.Column("file_id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("file_type", sa.String, nullable=False),
        sa.Column("original_filename", sa.String, nullable=False),
        sa.Column("stored_path", sa.String, nullable=False),
        sa.Column("row_count", sa.Integer, nullable=True),
        sa.Column("upload_status", sa.String, nullable=False, server_default="UPLOADED"),
        sa.Column("uploaded_at", sa.String, nullable=False),
        sa.Column("checksum", sa.String, nullable=True),
        sa.UniqueConstraint("engagement_id", "checksum", name="uq_uploaded_files_engagement_checksum"),
    )
    op.create_index("ix_uploaded_files_engagement", "uploaded_files", ["engagement_id"])

    op.create_table(
        "data_mappings",
        sa.Column("mapping_id", sa.Integer, primary_key=True),
        sa.Column("file_id", sa.Integer, sa.ForeignKey("uploaded_files.file_id"), nullable=False),
        sa.Column("source_column", sa.String, nullable=False),
        sa.Column("target_field", sa.String, nullable=False),
        sa.Column("confidence_score", sa.Float, nullable=True),
        sa.Column("is_user_confirmed", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("confirmed_at", sa.String, nullable=True),
        sa.UniqueConstraint("file_id", "source_column", name="uq_data_mappings_file_source_column"),
    )

    op.create_table(
        "standards",
        sa.Column("standard_id", sa.Integer, primary_key=True),
        sa.Column("framework", sa.String, nullable=False),
        sa.Column("code", sa.String, nullable=False, unique=True),
        sa.Column("title", sa.String, nullable=False),
        sa.Column("source_reference", sa.String, nullable=True),
        sa.Column("effective_date", sa.String, nullable=True),
    )

    op.create_table(
        "accounting_rules",
        sa.Column("rule_id", sa.String, primary_key=True),
        sa.Column("standard_id", sa.Integer, sa.ForeignKey("standards.standard_id"), nullable=True),
        sa.Column("framework", sa.String, nullable=False),
        sa.Column("topic", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("data_required", sa.String, nullable=True),
        sa.Column("logic_summary", sa.String, nullable=True),
        sa.Column("risk_level_default", sa.String, nullable=False, server_default="MEDIUM"),
        sa.Column("suggested_action", sa.String, nullable=True),
        sa.Column("suggested_query_template", sa.String, nullable=True),
        sa.Column("version", sa.String, nullable=True),
        sa.Column("effective_date", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("applicability_preconditions", sa.String, nullable=True),
        sa.Column("analytical_test", sa.String, nullable=True),
        sa.Column("expected_result", sa.String, nullable=True),
        sa.Column("knowledge_base_version", sa.String, nullable=True),
        sa.Column("verification_status", sa.String, nullable=False, server_default="VERIFIED"),
    )

    op.create_table(
        "audit_rules",
        sa.Column("rule_id", sa.String, primary_key=True),
        sa.Column("standard_id", sa.Integer, sa.ForeignKey("standards.standard_id"), nullable=True),
        sa.Column("topic", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("data_required", sa.String, nullable=True),
        sa.Column("logic_summary", sa.String, nullable=True),
        sa.Column("risk_level_default", sa.String, nullable=False, server_default="MEDIUM"),
        sa.Column("suggested_action", sa.String, nullable=True),
        sa.Column("suggested_query_template", sa.String, nullable=True),
        sa.Column("version", sa.String, nullable=True),
        sa.Column("effective_date", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("related_sa", sa.String, nullable=True),
        sa.Column("audit_area", sa.String, nullable=True),
        sa.Column("suggested_audit_procedure", sa.String, nullable=True),
        sa.Column("verification_status", sa.String, nullable=False, server_default="VERIFIED"),
    )

    op.create_table(
        "tax_rules",
        sa.Column("rule_id", sa.String, primary_key=True),
        sa.Column("standard_id", sa.Integer, sa.ForeignKey("standards.standard_id"), nullable=True),
        sa.Column("topic", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("data_required", sa.String, nullable=True),
        sa.Column("logic_summary", sa.String, nullable=True),
        sa.Column("risk_level_default", sa.String, nullable=False, server_default="MEDIUM"),
        sa.Column("suggested_action", sa.String, nullable=True),
        sa.Column("suggested_query_template", sa.String, nullable=True),
        sa.Column("version", sa.String, nullable=True),
        sa.Column("effective_date", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("legislative_act", sa.String, nullable=True),
        sa.Column("provision_reference", sa.String, nullable=True),
        sa.Column("applicable_from_ay", sa.String, nullable=True),
        sa.Column("applicable_to_ay", sa.String, nullable=True),
        sa.Column("verification_status", sa.String, nullable=False, server_default="SOURCE_VERIFICATION_REQUIRED"),
        sa.Column("verified_source", sa.String, nullable=True),
        sa.Column("verified_on", sa.String, nullable=True),
        sa.Column("verified_by", sa.String, nullable=True),
    )
    op.create_index("ix_tax_rules_verification_status", "tax_rules", ["verification_status"])

    op.create_table(
        "sebi_rules",
        sa.Column("rule_id", sa.String, primary_key=True),
        sa.Column("standard_id", sa.Integer, sa.ForeignKey("standards.standard_id"), nullable=True),
        sa.Column("topic", sa.String, nullable=False),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("data_required", sa.String, nullable=True),
        sa.Column("logic_summary", sa.String, nullable=True),
        sa.Column("risk_level_default", sa.String, nullable=False, server_default="MEDIUM"),
        sa.Column("suggested_action", sa.String, nullable=True),
        sa.Column("suggested_query_template", sa.String, nullable=True),
        sa.Column("version", sa.String, nullable=True),
        sa.Column("effective_date", sa.String, nullable=True),
        sa.Column("is_active", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("lodr_regulation_ref", sa.String, nullable=True),
        sa.Column("limitation", sa.String, nullable=True),
        sa.Column("verification_status", sa.String, nullable=False, server_default="SOURCE_VERIFICATION_REQUIRED"),
        sa.Column("verified_source", sa.String, nullable=True),
        sa.Column("verified_on", sa.String, nullable=True),
        sa.Column("verified_by", sa.String, nullable=True),
    )
    op.create_index("ix_sebi_rules_verification_status", "sebi_rules", ["verification_status"])

    op.create_table(
        "audit_assertions",
        sa.Column("assertion_id", sa.Integer, primary_key=True),
        sa.Column("code", sa.String, nullable=False, unique=True),
        sa.Column("label", sa.String, nullable=False),
    )

    op.create_table(
        "audit_rule_assertions",
        sa.Column("rule_id", sa.String, sa.ForeignKey("audit_rules.rule_id"), primary_key=True),
        sa.Column("assertion_id", sa.Integer, sa.ForeignKey("audit_assertions.assertion_id"), primary_key=True),
    )

    op.create_table(
        "transactions",
        sa.Column("transaction_id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("file_id", sa.Integer, sa.ForeignKey("uploaded_files.file_id"), nullable=True),
        sa.Column("dataset_type", sa.String, nullable=False),
        sa.Column("transaction_date", sa.String, nullable=True),
        sa.Column("account_name", sa.String, nullable=True),
        sa.Column("party_name", sa.String, nullable=True),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("debit_amount", sa.Integer, nullable=True),
        sa.Column("credit_amount", sa.Integer, nullable=True),
        sa.Column("reference_number", sa.String, nullable=True),
        sa.Column("is_manual_entry", sa.Boolean, nullable=True),
        sa.Column("payment_mode", sa.String, nullable=True),
        sa.Column("extra_json", sa.String, nullable=True),
        sa.Column("created_at", sa.String, nullable=False),
    )
    op.create_index("ix_transactions_engagement_dataset", "transactions", ["engagement_id", "dataset_type"])

    op.create_table(
        "fixed_assets",
        sa.Column("asset_id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("file_id", sa.Integer, sa.ForeignKey("uploaded_files.file_id"), nullable=True),
        sa.Column("asset_description", sa.String, nullable=True),
        sa.Column("asset_class", sa.String, nullable=True),
        sa.Column("date_put_to_use", sa.String, nullable=True),
        sa.Column("original_cost_paise", sa.Integer, nullable=True),
        sa.Column("opening_wdv_paise", sa.Integer, nullable=True),
        sa.Column("additions_paise", sa.Integer, nullable=True),
        sa.Column("deletions_paise", sa.Integer, nullable=True),
        sa.Column("book_depreciation_rate", sa.Float, nullable=True),
        sa.Column("book_depreciation_amount_paise", sa.Integer, nullable=True),
        sa.Column("tax_block_of_asset", sa.String, nullable=True),
        sa.Column("tax_depreciation_rate", sa.Float, nullable=True),
        sa.Column("closing_wdv_paise", sa.Integer, nullable=True),
    )
    op.create_index("ix_fixed_assets_engagement", "fixed_assets", ["engagement_id"])

    op.create_table(
        "gst_line_items",
        sa.Column("gst_line_id", sa.Integer, primary_key=True),
        sa.Column("transaction_id", sa.Integer, sa.ForeignKey("transactions.transaction_id"), nullable=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("gstin", sa.String, nullable=True),
        sa.Column("invoice_number", sa.String, nullable=True),
        sa.Column("invoice_date", sa.String, nullable=True),
        sa.Column("taxable_value_paise", sa.Integer, nullable=True),
        sa.Column("cgst_paise", sa.Integer, nullable=True),
        sa.Column("sgst_paise", sa.Integer, nullable=True),
        sa.Column("igst_paise", sa.Integer, nullable=True),
        sa.Column("tax_rate", sa.Float, nullable=True),
        sa.Column("source_dataset", sa.String, nullable=True),
    )
    op.create_index("ix_gst_line_items_engagement", "gst_line_items", ["engagement_id"])
    op.create_index("ix_gst_line_items_invoice", "gst_line_items", ["engagement_id", "invoice_number"])

    op.create_table(
        "tds_line_items",
        sa.Column("tds_line_id", sa.Integer, primary_key=True),
        sa.Column("transaction_id", sa.Integer, sa.ForeignKey("transactions.transaction_id"), nullable=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("section_code", sa.String, nullable=True),
        sa.Column("deductee_pan", sa.String, nullable=True),
        sa.Column("rate_applied", sa.Float, nullable=True),
        sa.Column("amount_deducted_paise", sa.Integer, nullable=True),
        sa.Column("challan_number", sa.String, nullable=True),
        sa.Column("deposit_date", sa.String, nullable=True),
    )
    op.create_index("ix_tds_line_items_engagement", "tds_line_items", ["engagement_id"])

    # exceptions BEFORE queries/documents — both reference it.
    op.create_table(
        "exceptions",
        sa.Column("exception_id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("module", sa.String, nullable=False),
        sa.Column("area", sa.String, nullable=True),
        sa.Column("rule_id", sa.String, nullable=True),  # see documentation/db_constraints.md
        sa.Column("standard_reference", sa.String, nullable=True),
        sa.Column("description", sa.String, nullable=True),
        sa.Column("related_transaction_id", sa.Integer, sa.ForeignKey("transactions.transaction_id"), nullable=True),
        sa.Column("amount", sa.Integer, nullable=True),
        sa.Column("risk_score", sa.Integer, nullable=True),
        sa.Column("risk_level", sa.String, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="OPEN"),
        sa.Column("assigned_to", sa.String, nullable=True),
        sa.Column("reviewer_notes", sa.String, nullable=True),
        sa.Column("created_at", sa.String, nullable=False),
        sa.Column("resolved_at", sa.String, nullable=True),
        sa.Column("trigger_condition", sa.String, nullable=True),
        sa.Column("threshold_used_json", sa.String, nullable=True),
        sa.Column("data_sources_json", sa.String, nullable=True),
        sa.Column("assertions_snapshot", sa.String, nullable=True),
        sa.Column("status_reason", sa.String, nullable=True),
        # NOTE: no supporting_file_id column — removed, see
        # documentation/db_constraints.md.
    )
    op.create_index("ix_exceptions_engagement_status", "exceptions", ["engagement_id", "status"])
    op.create_index("ix_exceptions_engagement_module", "exceptions", ["engagement_id", "module"])

    op.create_table(
        "risk_scores",
        sa.Column("risk_score_id", sa.Integer, primary_key=True),
        sa.Column("exception_id", sa.Integer, sa.ForeignKey("exceptions.exception_id"), nullable=False),
        sa.Column("total_score", sa.Integer, nullable=False),
        sa.Column("factor_breakdown_json", sa.String, nullable=True),
        sa.Column("calculated_at", sa.String, nullable=False),
    )

    op.create_table(
        "queries",
        sa.Column("query_id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("exception_id", sa.Integer, sa.ForeignKey("exceptions.exception_id"), nullable=True),
        sa.Column("category", sa.String, nullable=False),
        sa.Column("area", sa.String, nullable=True),
        sa.Column("observation", sa.String, nullable=True),
        sa.Column("question_text", sa.String, nullable=True),
        sa.Column("required_document", sa.String, nullable=True),
        sa.Column("reference", sa.String, nullable=True),
        sa.Column("risk_level", sa.String, nullable=True),
        sa.Column("status", sa.String, nullable=False, server_default="OPEN"),
        sa.Column("is_ai_drafted", sa.Boolean, nullable=False, server_default=sa.text("0")),
        sa.Column("created_at", sa.String, nullable=False),
    )
    op.create_index("ix_queries_engagement_status", "queries", ["engagement_id", "status"])

    op.create_table(
        "query_responses",
        sa.Column("response_id", sa.Integer, primary_key=True),
        sa.Column("query_id", sa.Integer, sa.ForeignKey("queries.query_id"), nullable=False),
        sa.Column("management_response", sa.String, nullable=True),
        sa.Column("reviewer_comments", sa.String, nullable=True),
        sa.Column("resolution", sa.String, nullable=True),
        sa.Column("responded_at", sa.String, nullable=True),
    )

    # documents LAST of the exception/query family — it is the sole
    # owner of the Document <-> Exception/Query relationship (Stage 3
    # review round 2, correction #3) and therefore depends on both.
    op.create_table(
        "documents",
        sa.Column("document_id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=False),
        sa.Column("related_exception_id", sa.Integer, sa.ForeignKey("exceptions.exception_id"), nullable=True),
        sa.Column("related_query_id", sa.Integer, sa.ForeignKey("queries.query_id"), nullable=True),
        sa.Column("file_name", sa.String, nullable=False),
        sa.Column("stored_path", sa.String, nullable=False),
        sa.Column("uploaded_at", sa.String, nullable=False),
    )
    op.create_index("ix_documents_related_exception", "documents", ["related_exception_id"])
    op.create_index("ix_documents_related_query", "documents", ["related_query_id"])

    op.create_table(
        "audit_log",
        sa.Column("log_id", sa.Integer, primary_key=True),
        sa.Column("engagement_id", sa.Integer, sa.ForeignKey("engagements.engagement_id"), nullable=True),
        sa.Column("action", sa.String, nullable=False),
        sa.Column("entity_affected", sa.String, nullable=True),
        sa.Column("performed_by", sa.String, nullable=True),
        sa.Column("timestamp", sa.String, nullable=False),
        sa.Column("detail_json", sa.String, nullable=True),
    )
    op.create_index("ix_audit_log_engagement", "audit_log", ["engagement_id"])

    op.create_table(
        "application_settings",
        sa.Column("setting_key", sa.String, primary_key=True),
        sa.Column("setting_value", sa.String, nullable=True),
        sa.Column("updated_at", sa.String, nullable=True),
    )

    op.create_table(
        "knowledge_base_versions",
        sa.Column("kb_version_id", sa.Integer, primary_key=True),
        sa.Column("version_label", sa.String, nullable=False, unique=True),
        sa.Column("released_at", sa.String, nullable=True),
        sa.Column("notes", sa.String, nullable=True),
        sa.Column("is_current", sa.Boolean, nullable=False, server_default=sa.text("0")),
    )


def downgrade() -> None:
    # Reverse dependency order.
    op.drop_table("knowledge_base_versions")
    op.drop_table("application_settings")
    op.drop_table("audit_log")
    op.drop_table("documents")
    op.drop_table("query_responses")
    op.drop_table("queries")
    op.drop_table("risk_scores")
    op.drop_table("exceptions")
    op.drop_table("tds_line_items")
    op.drop_table("gst_line_items")
    op.drop_table("fixed_assets")
    op.drop_table("transactions")
    op.drop_table("audit_rule_assertions")
    op.drop_table("audit_assertions")
    op.drop_table("sebi_rules")
    op.drop_table("tax_rules")
    op.drop_table("audit_rules")
    op.drop_table("accounting_rules")
    op.drop_table("standards")
    op.drop_table("data_mappings")
    op.drop_table("uploaded_files")
    op.drop_table("applicability")
    op.drop_table("entity_profiles")
    op.drop_table("engagements")

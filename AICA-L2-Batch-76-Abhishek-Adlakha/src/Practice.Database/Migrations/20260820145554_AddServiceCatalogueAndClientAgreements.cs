using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1861 // Generated migration uses inline column/key arrays.

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class AddServiceCatalogueAndClientAgreements : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "services");

            migrationBuilder.AddUniqueConstraint(
                name: "ak_gst_registrations_id_client",
                schema: "clients",
                table: "gst_registrations",
                columns: new[] { "id", "client_id" });

            migrationBuilder.CreateTable(
                name: "service_categories",
                schema: "services",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    name = table.Column<string>(type: "character varying(120)", maxLength: 120, nullable: false),
                    normalized_name = table.Column<string>(type: "character varying(120)", maxLength: 120, nullable: false),
                    display_order = table.Column<int>(type: "integer", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_service_categories", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "services",
                schema: "services",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    category_id = table.Column<Guid>(type: "uuid", nullable: false),
                    code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    name = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: false),
                    normalized_name = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: false),
                    description = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    default_billable = table.Column<bool>(type: "boolean", nullable: false),
                    supports_recurrence = table.Column<bool>(type: "boolean", nullable: false),
                    supports_gstin_scope = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_services", x => x.id);
                    table.ForeignKey(
                        name: "fk_services_category",
                        column: x => x.category_id,
                        principalSchema: "services",
                        principalTable: "service_categories",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "client_services",
                schema: "services",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_id = table.Column<Guid>(type: "uuid", nullable: false),
                    service_id = table.Column<Guid>(type: "uuid", nullable: false),
                    gst_registration_id = table.Column<Guid>(type: "uuid", nullable: true),
                    engagement_code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: true),
                    title_override = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    effective_from = table.Column<DateOnly>(type: "date", nullable: false),
                    effective_to = table.Column<DateOnly>(type: "date", nullable: true),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    default_priority = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    responsible_team_id = table.Column<Guid>(type: "uuid", nullable: true),
                    notes = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true),
                    deactivated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    deactivation_reason = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_client_services", x => x.id);
                    table.CheckConstraint("ck_client_services_dates", "effective_to IS NULL OR effective_to >= effective_from");
                    table.CheckConstraint("ck_client_services_deactivation", "(is_active AND deactivated_at_utc IS NULL AND deactivation_reason IS NULL) OR (NOT is_active AND deactivated_at_utc IS NOT NULL AND length(trim(deactivation_reason)) > 0)");
                    table.CheckConstraint("ck_client_services_priority", "default_priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')");
                    table.ForeignKey(
                        name: "fk_client_services_client",
                        column: x => x.client_id,
                        principalSchema: "clients",
                        principalTable: "clients",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_client_services_gstin_client",
                        columns: x => new { x.gst_registration_id, x.client_id },
                        principalSchema: "clients",
                        principalTable: "gst_registrations",
                        principalColumns: new[] { "id", "client_id" },
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_client_services_service",
                        column: x => x.service_id,
                        principalSchema: "services",
                        principalTable: "services",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_client_services_team",
                        column: x => x.responsible_team_id,
                        principalSchema: "employees",
                        principalTable: "teams",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "service_import_proposals",
                schema: "import",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    import_run_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_row_number = table.Column<int>(type: "integer", nullable: false),
                    source_client_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    proposed_client_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: true),
                    source_column = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    service_code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    proposed_gstin = table.Column<string>(type: "character varying(15)", maxLength: 15, nullable: true),
                    client_service_id = table.Column<Guid>(type: "uuid", nullable: true),
                    outcome = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    data_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_service_import_proposals", x => x.id);
                    table.CheckConstraint("ck_service_import_proposals_outcome", "outcome IN ('READY', 'EXCEPTION', 'IMPORTED', 'SKIPPED')");
                    table.ForeignKey(
                        name: "fk_service_import_proposals_client_service",
                        column: x => x.client_service_id,
                        principalSchema: "services",
                        principalTable: "client_services",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_service_import_proposals_run",
                        column: x => x.import_run_id,
                        principalSchema: "import",
                        principalTable: "import_runs",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.InsertData(
                schema: "system",
                table: "field_definitions",
                columns: new[] { "entity_type", "field_key", "description", "is_active", "is_administrator_required", "is_system_required", "label", "updated_at_utc", "updated_by_user_id" },
                values: new object[,]
                {
                    { "services.client_service", "clientId", "Client receiving the service.", true, true, true, "Client", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "services.client_service", "defaultPriority", "Priority copied to future generated work.", true, false, false, "Default priority", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "services.client_service", "effectiveFrom", "Date the service agreement begins.", true, true, true, "Effective from", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "services.client_service", "responsibleTeamId", "Team responsible for this client service.", true, false, false, "Responsible team", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "services.client_service", "serviceId", "Catalogue service being enrolled.", true, true, true, "Service", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null }
                });

            migrationBuilder.InsertData(
                schema: "identity",
                table: "permissions",
                columns: new[] { "id", "action", "code", "description", "module", "supports_scope" },
                values: new object[,]
                {
                    { new Guid("20000000-0000-0000-0000-000000000023"), "ViewCatalogue", "services.view", "View the service catalogue.", "Services", false },
                    { new Guid("20000000-0000-0000-0000-000000000024"), "ManageCatalogue", "services.catalogue.manage", "Create and safely deactivate service definitions.", "Services", false },
                    { new Guid("20000000-0000-0000-0000-000000000025"), "ViewEnrollments", "services.enrollments.view", "View permitted client service agreements.", "Services", true },
                    { new Guid("20000000-0000-0000-0000-000000000026"), "ManageEnrollments", "services.enrollments.manage", "Configure permitted client service agreements.", "Services", true }
                });

            migrationBuilder.InsertData(
                schema: "services",
                table: "service_categories",
                columns: new[] { "id", "code", "display_order", "is_active", "name", "normalized_name" },
                values: new object[,]
                {
                    { new Guid("40000000-0000-0000-0000-000000000001"), "ACCOUNTING", 10, true, "Accounting", "ACCOUNTING" },
                    { new Guid("40000000-0000-0000-0000-000000000002"), "INCOME_TAX", 20, true, "Income Tax", "INCOME TAX" },
                    { new Guid("40000000-0000-0000-0000-000000000003"), "GST", 30, true, "GST", "GST" },
                    { new Guid("40000000-0000-0000-0000-000000000004"), "ASSURANCE", 40, true, "Assurance and Advisory", "ASSURANCE AND ADVISORY" },
                    { new Guid("40000000-0000-0000-0000-000000000005"), "CORPORATE", 50, true, "Corporate and Regulatory", "CORPORATE AND REGULATORY" }
                });

            migrationBuilder.InsertData(
                schema: "identity",
                table: "role_permissions",
                columns: new[] { "permission_id", "role_id", "scope_ceiling" },
                values: new object[,]
                {
                    { new Guid("20000000-0000-0000-0000-000000000023"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000024"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000025"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" },
                    { new Guid("20000000-0000-0000-0000-000000000026"), new Guid("10000000-0000-0000-0000-000000000001"), "ALL" }
                });

            migrationBuilder.InsertData(
                schema: "services",
                table: "services",
                columns: new[] { "id", "category_id", "code", "created_at_utc", "default_billable", "description", "is_active", "name", "normalized_name", "supports_gstin_scope", "supports_recurrence", "updated_at_utc" },
                values: new object[,]
                {
                    { new Guid("41000000-0000-0000-0000-000000000001"), new Guid("40000000-0000-0000-0000-000000000001"), "ACCOUNTS", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Accounts", "ACCOUNTS", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000002"), new Guid("40000000-0000-0000-0000-000000000002"), "ITR", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Income Tax Return", "INCOME TAX RETURN", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000003"), new Guid("40000000-0000-0000-0000-000000000002"), "SFT", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Statement of Financial Transactions", "STATEMENT OF FINANCIAL TRANSACTIONS", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000004"), new Guid("40000000-0000-0000-0000-000000000002"), "TAX_AUDIT", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Tax Audit", "TAX AUDIT", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000005"), new Guid("40000000-0000-0000-0000-000000000002"), "TDS", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "TDS Compliance", "TDS COMPLIANCE", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000006"), new Guid("40000000-0000-0000-0000-000000000002"), "TDS_RECONCILIATION", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "TDS Reconciliation", "TDS RECONCILIATION", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000007"), new Guid("40000000-0000-0000-0000-000000000003"), "GST", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "GST Returns", "GST RETURNS", true, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000008"), new Guid("40000000-0000-0000-0000-000000000003"), "GST_REFUND", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "GST Refund", "GST REFUND", true, false, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000009"), new Guid("40000000-0000-0000-0000-000000000003"), "GSTR9", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "GSTR-9 Annual Return", "GSTR-9 ANNUAL RETURN", true, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000010"), new Guid("40000000-0000-0000-0000-000000000005"), "RODTEP", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "RoDTEP", "RODTEP", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000011"), new Guid("40000000-0000-0000-0000-000000000005"), "FLA_RETURN", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "FLA Return", "FLA RETURN", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000012"), new Guid("40000000-0000-0000-0000-000000000004"), "CFO_INTERNAL_AUDIT", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "CFO / Internal Audit", "CFO / INTERNAL AUDIT", false, false, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000013"), new Guid("40000000-0000-0000-0000-000000000003"), "LUT", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Letter of Undertaking", "LETTER OF UNDERTAKING", true, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000014"), new Guid("40000000-0000-0000-0000-000000000005"), "MSME", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "MSME Compliance", "MSME COMPLIANCE", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000015"), new Guid("40000000-0000-0000-0000-000000000005"), "IEC", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Import Export Code", "IMPORT EXPORT CODE", false, false, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000016"), new Guid("40000000-0000-0000-0000-000000000002"), "COMPANY_TAX", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Company Tax", "COMPANY TAX", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000017"), new Guid("40000000-0000-0000-0000-000000000005"), "PROFESSIONAL_TAX", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Professional Tax", "PROFESSIONAL TAX", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000018"), new Guid("40000000-0000-0000-0000-000000000004"), "AUDIT", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Audit", "AUDIT", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000019"), new Guid("40000000-0000-0000-0000-000000000005"), "ROC_RETURN", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "ROC Return", "ROC RETURN", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000020"), new Guid("40000000-0000-0000-0000-000000000005"), "ROC_REGISTER", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "ROC Register", "ROC REGISTER", false, false, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) },
                    { new Guid("41000000-0000-0000-0000-000000000021"), new Guid("40000000-0000-0000-0000-000000000002"), "TRANSFER_PRICING", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, null, true, "Transfer Pricing", "TRANSFER PRICING", false, true, new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)) }
                });

            migrationBuilder.CreateIndex(
                name: "ix_client_services_client_active",
                schema: "services",
                table: "client_services",
                columns: new[] { "client_id", "is_active" });

            migrationBuilder.CreateIndex(
                name: "IX_client_services_gst_registration_id_client_id",
                schema: "services",
                table: "client_services",
                columns: new[] { "gst_registration_id", "client_id" });

            migrationBuilder.CreateIndex(
                name: "ix_client_services_service_active",
                schema: "services",
                table: "client_services",
                columns: new[] { "service_id", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ix_client_services_team_active",
                schema: "services",
                table: "client_services",
                columns: new[] { "responsible_team_id", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ux_client_services_gstin_active",
                schema: "services",
                table: "client_services",
                columns: new[] { "client_id", "service_id", "gst_registration_id" },
                unique: true,
                filter: "is_active AND gst_registration_id IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "ux_client_services_unscoped_active",
                schema: "services",
                table: "client_services",
                columns: new[] { "client_id", "service_id" },
                unique: true,
                filter: "is_active AND gst_registration_id IS NULL");

            migrationBuilder.CreateIndex(
                name: "ux_service_categories_code",
                schema: "services",
                table: "service_categories",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_service_categories_name",
                schema: "services",
                table: "service_categories",
                column: "normalized_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_service_import_proposals_client_service_id",
                schema: "import",
                table: "service_import_proposals",
                column: "client_service_id");

            migrationBuilder.CreateIndex(
                name: "ix_service_import_proposals_outcome",
                schema: "import",
                table: "service_import_proposals",
                columns: new[] { "import_run_id", "outcome" });

            migrationBuilder.CreateIndex(
                name: "ux_service_import_proposals_run_row_service",
                schema: "import",
                table: "service_import_proposals",
                columns: new[] { "import_run_id", "source_row_number", "service_code" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_services_category_active",
                schema: "services",
                table: "services",
                columns: new[] { "category_id", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ux_services_code",
                schema: "services",
                table: "services",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_services_name",
                schema: "services",
                table: "services",
                column: "normalized_name",
                unique: true);

            migrationBuilder.Sql(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'practice_app') THEN
                        GRANT USAGE ON SCHEMA services TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA services TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON import.service_import_proposals TO practice_app;
                        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA services, import TO practice_app;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA services
                            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO practice_app;
                    END IF;
                END $$;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "service_import_proposals",
                schema: "import");

            migrationBuilder.DropTable(
                name: "client_services",
                schema: "services");

            migrationBuilder.DropTable(
                name: "services",
                schema: "services");

            migrationBuilder.DropTable(
                name: "service_categories",
                schema: "services");

            migrationBuilder.DropUniqueConstraint(
                name: "ak_gst_registrations_id_client",
                schema: "clients",
                table: "gst_registrations");

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "services.client_service", "clientId" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "services.client_service", "defaultPriority" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "services.client_service", "effectiveFrom" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "services.client_service", "responsibleTeamId" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "services.client_service", "serviceId" });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000023"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000024"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000025"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "role_permissions",
                keyColumns: new[] { "permission_id", "role_id" },
                keyValues: new object[] { new Guid("20000000-0000-0000-0000-000000000026"), new Guid("10000000-0000-0000-0000-000000000001") });

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000023"));

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000024"));

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000025"));

            migrationBuilder.DeleteData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000026"));
        }
    }
}

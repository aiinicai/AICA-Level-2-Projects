using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1861 // EF migration scaffolding emits constant metadata arrays.

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class AddBillingEntitiesAndEffectiveDatedTerms : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "billing");

            migrationBuilder.CreateTable(
                name: "billing_entities",
                schema: "billing",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    legal_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    trade_name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    pan = table.Column<string>(type: "character(10)", fixedLength: true, maxLength: 10, nullable: true),
                    gstin = table.Column<string>(type: "character(15)", fixedLength: true, maxLength: 15, nullable: true),
                    address = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    email = table.Column<string>(type: "character varying(320)", maxLength: 320, nullable: true),
                    phone = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: true),
                    currency_code = table.Column<string>(type: "character(3)", fixedLength: true, maxLength: 3, nullable: false),
                    effective_from = table.Column<DateOnly>(type: "date", nullable: false),
                    effective_to = table.Column<DateOnly>(type: "date", nullable: true),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    row_version = table.Column<long>(type: "bigint", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_billing_entities", x => x.id);
                    table.CheckConstraint("ck_billing_entities_currency", "currency_code ~ '^[A-Z]{3}$'");
                    table.CheckConstraint("ck_billing_entities_dates", "effective_to IS NULL OR effective_to >= effective_from");
                    table.CheckConstraint("ck_billing_entities_gstin", "gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z0-9]{13}$'");
                    table.CheckConstraint("ck_billing_entities_pan", "pan IS NULL OR pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'");
                });

            migrationBuilder.CreateTable(
                name: "billing_import_proposals",
                schema: "import",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    import_run_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_row_number = table.Column<int>(type: "integer", nullable: false),
                    source_client_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    source_service = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: true),
                    source_billing_entity = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: true),
                    source_amount = table.Column<decimal>(type: "numeric(19,2)", precision: 19, scale: 2, nullable: true),
                    source_frequency = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    client_service_id = table.Column<Guid>(type: "uuid", nullable: true),
                    billing_entity_id = table.Column<Guid>(type: "uuid", nullable: true),
                    outcome = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    issue_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    data_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_billing_import_proposals", x => x.id);
                    table.CheckConstraint("ck_billing_import_proposals_outcome", "outcome IN ('READY','EXCEPTION','IMPORTED','SKIPPED')");
                    table.ForeignKey(
                        name: "fk_billing_import_proposals_client_service",
                        column: x => x.client_service_id,
                        principalSchema: "services",
                        principalTable: "client_services",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_billing_import_proposals_entity",
                        column: x => x.billing_entity_id,
                        principalSchema: "billing",
                        principalTable: "billing_entities",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_billing_import_proposals_run",
                        column: x => x.import_run_id,
                        principalSchema: "import",
                        principalTable: "import_runs",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "billing_terms",
                schema: "billing",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_service_id = table.Column<Guid>(type: "uuid", nullable: false),
                    billing_entity_id = table.Column<Guid>(type: "uuid", nullable: true),
                    is_billable = table.Column<bool>(type: "boolean", nullable: false),
                    pricing_model = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    amount = table.Column<decimal>(type: "numeric(19,2)", precision: 19, scale: 2, nullable: true),
                    currency_code = table.Column<string>(type: "character(3)", fixedLength: true, maxLength: 3, nullable: false),
                    tax_inclusive = table.Column<bool>(type: "boolean", nullable: false),
                    effective_from = table.Column<DateOnly>(type: "date", nullable: false),
                    effective_to = table.Column<DateOnly>(type: "date", nullable: true),
                    version = table.Column<int>(type: "integer", nullable: false),
                    notes = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    created_by_user_id = table.Column<Guid>(type: "uuid", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_billing_terms", x => x.id);
                    table.CheckConstraint("ck_billing_terms_amount", "(is_billable AND billing_entity_id IS NOT NULL AND amount IS NOT NULL AND amount >= 0) OR (NOT is_billable AND billing_entity_id IS NULL AND amount IS NULL)");
                    table.CheckConstraint("ck_billing_terms_currency", "currency_code ~ '^[A-Z]{3}$'");
                    table.CheckConstraint("ck_billing_terms_dates", "effective_to IS NULL OR effective_to >= effective_from");
                    table.CheckConstraint("ck_billing_terms_pricing", "pricing_model = 'FIXED'");
                    table.CheckConstraint("ck_billing_terms_version", "version > 0");
                    table.ForeignKey(
                        name: "fk_billing_terms_client_service",
                        column: x => x.client_service_id,
                        principalSchema: "services",
                        principalTable: "client_services",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_billing_terms_creator",
                        column: x => x.created_by_user_id,
                        principalSchema: "identity",
                        principalTable: "users",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_billing_terms_entity",
                        column: x => x.billing_entity_id,
                        principalSchema: "billing",
                        principalTable: "billing_entities",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "billing_schedules",
                schema: "billing",
                columns: table => new
                {
                    billing_term_id = table.Column<Guid>(type: "uuid", nullable: false),
                    frequency_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    interval_months = table.Column<int>(type: "integer", nullable: true),
                    anchor_date = table.Column<DateOnly>(type: "date", nullable: true),
                    billing_day = table.Column<int>(type: "integer", nullable: true),
                    business_day_adjustment = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    projection_timing = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    one_time_date = table.Column<DateOnly>(type: "date", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_billing_schedules", x => x.billing_term_id);
                    table.CheckConstraint("ck_billing_schedules_adjustment", "business_day_adjustment IN ('NONE','PREVIOUS','NEXT')");
                    table.CheckConstraint("ck_billing_schedules_day", "billing_day IS NULL OR billing_day BETWEEN 1 AND 31");
                    table.CheckConstraint("ck_billing_schedules_frequency", "frequency_code IN ('MONTHLY','QUARTERLY','HALF_YEARLY','ANNUALLY','SPECIFIC_MONTH','ONE_TIME','CUSTOM_MONTHS')");
                    table.CheckConstraint("ck_billing_schedules_interval", "interval_months IS NULL OR interval_months IN (1,3,6,12)");
                    table.CheckConstraint("ck_billing_schedules_projection", "projection_timing = 'PER_BILLING_EVENT'");
                    table.CheckConstraint("ck_billing_schedules_shape", "(frequency_code = 'ONE_TIME' AND one_time_date IS NOT NULL AND anchor_date IS NULL AND billing_day IS NULL AND interval_months IS NULL) OR (frequency_code <> 'ONE_TIME' AND one_time_date IS NULL AND anchor_date IS NOT NULL AND billing_day IS NOT NULL AND interval_months IS NOT NULL)");
                    table.ForeignKey(
                        name: "fk_billing_schedules_term",
                        column: x => x.billing_term_id,
                        principalSchema: "billing",
                        principalTable: "billing_terms",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "billing_schedule_months",
                schema: "billing",
                columns: table => new
                {
                    billing_term_id = table.Column<Guid>(type: "uuid", nullable: false),
                    month = table.Column<int>(type: "integer", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_billing_schedule_months", x => new { x.billing_term_id, x.month });
                    table.CheckConstraint("ck_billing_schedule_months_month", "month BETWEEN 1 AND 12");
                    table.ForeignKey(
                        name: "fk_billing_schedule_months_schedule",
                        column: x => x.billing_term_id,
                        principalSchema: "billing",
                        principalTable: "billing_schedules",
                        principalColumn: "billing_term_id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.InsertData(
                schema: "system",
                table: "field_definitions",
                columns: new[] { "entity_type", "field_key", "description", "is_active", "is_administrator_required", "is_system_required", "label", "updated_at_utc", "updated_by_user_id" },
                values: new object[,]
                {
                    { "billing.billing_entity", "address", "Registered or invoicing address.", true, false, false, "Address", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_entity", "code", "Stable code for the legal invoicing entity.", true, true, true, "Billing entity code", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_entity", "currencyCode", "Three-letter currency code for this billing entity.", true, true, true, "Currency", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_entity", "effectiveFrom", "Date from which the legal billing entity may be used.", true, true, true, "Effective from", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_entity", "email", "Billing contact email.", true, false, false, "Email", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_entity", "gstin", "GST registration used by the billing entity.", true, false, false, "GSTIN", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_entity", "legalName", "Registered legal name of the billing entity.", true, true, true, "Legal name", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_entity", "pan", "Permanent Account Number of the billing entity.", true, false, false, "PAN", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_entity", "phone", "Billing contact phone number.", true, false, false, "Phone", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_entity", "tradeName", "Public or trading name, where different.", true, false, false, "Trade name", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_term", "clientServiceId", "Agreement receiving the commercial term.", true, true, true, "Client service agreement", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_term", "effectiveFrom", "Date from which the commercial term applies.", true, true, true, "Effective from", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_term", "isBillable", "Whether the agreement is charged or explicitly non-billable.", true, true, true, "Billable status", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "billing.billing_term", "notes", "Commercial notes explaining the agreed fee.", true, false, false, "Fee notes", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null }
                });

            migrationBuilder.UpdateData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000020"),
                columns: new[] { "description", "supports_scope" },
                values: new object[] { "Configure billing entities and permitted client-service fee terms.", true });

            migrationBuilder.CreateIndex(
                name: "ix_billing_entities_active_name",
                schema: "billing",
                table: "billing_entities",
                columns: new[] { "is_active", "legal_name" });

            migrationBuilder.CreateIndex(
                name: "ux_billing_entities_code",
                schema: "billing",
                table: "billing_entities",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_billing_entities_gstin",
                schema: "billing",
                table: "billing_entities",
                column: "gstin",
                unique: true,
                filter: "gstin IS NOT NULL");

            migrationBuilder.CreateIndex(
                name: "IX_billing_import_proposals_billing_entity_id",
                schema: "import",
                table: "billing_import_proposals",
                column: "billing_entity_id");

            migrationBuilder.CreateIndex(
                name: "IX_billing_import_proposals_client_service_id",
                schema: "import",
                table: "billing_import_proposals",
                column: "client_service_id");

            migrationBuilder.CreateIndex(
                name: "ix_billing_import_proposals_outcome",
                schema: "import",
                table: "billing_import_proposals",
                columns: new[] { "import_run_id", "outcome" });

            migrationBuilder.CreateIndex(
                name: "ix_billing_import_proposals_run_row",
                schema: "import",
                table: "billing_import_proposals",
                columns: new[] { "import_run_id", "source_row_number" });

            migrationBuilder.CreateIndex(
                name: "ix_billing_terms_agreement_dates",
                schema: "billing",
                table: "billing_terms",
                columns: new[] { "client_service_id", "effective_from", "effective_to" });

            migrationBuilder.CreateIndex(
                name: "IX_billing_terms_created_by_user_id",
                schema: "billing",
                table: "billing_terms",
                column: "created_by_user_id");

            migrationBuilder.CreateIndex(
                name: "ix_billing_terms_entity_dates",
                schema: "billing",
                table: "billing_terms",
                columns: new[] { "billing_entity_id", "effective_from" });

            migrationBuilder.CreateIndex(
                name: "ux_billing_terms_agreement_version",
                schema: "billing",
                table: "billing_terms",
                columns: new[] { "client_service_id", "version" },
                unique: true);

            migrationBuilder.Sql("""
                CREATE EXTENSION IF NOT EXISTS btree_gist;
                ALTER TABLE billing.billing_terms
                    ADD CONSTRAINT ex_billing_terms_no_overlap
                    EXCLUDE USING gist
                    (client_service_id WITH =, daterange(effective_from, COALESCE(effective_to, 'infinity'::date), '[]') WITH &&);

                DO $phase7$
                BEGIN
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'practice_app') THEN
                        GRANT USAGE ON SCHEMA billing TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA billing TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON import.billing_import_proposals TO practice_app;
                        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA billing, import TO practice_app;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA billing
                            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO practice_app;
                    END IF;
                END $phase7$;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "billing_import_proposals",
                schema: "import");

            migrationBuilder.DropTable(
                name: "billing_schedule_months",
                schema: "billing");

            migrationBuilder.DropTable(
                name: "billing_schedules",
                schema: "billing");

            migrationBuilder.DropTable(
                name: "billing_terms",
                schema: "billing");

            migrationBuilder.DropTable(
                name: "billing_entities",
                schema: "billing");

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "address" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "code" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "currencyCode" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "effectiveFrom" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "email" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "gstin" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "legalName" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "pan" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "phone" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_entity", "tradeName" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_term", "clientServiceId" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_term", "effectiveFrom" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_term", "isBillable" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "billing.billing_term", "notes" });

            migrationBuilder.UpdateData(
                schema: "identity",
                table: "permissions",
                keyColumn: "id",
                keyValue: new Guid("20000000-0000-0000-0000-000000000020"),
                columns: new[] { "description", "supports_scope" },
                values: new object[] { "Configure billing.", false });
        }
    }
}

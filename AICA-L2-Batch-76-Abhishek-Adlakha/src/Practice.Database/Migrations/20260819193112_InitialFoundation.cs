using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1861 // EF-generated migration arguments are applied once

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class InitialFoundation : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "system");

            migrationBuilder.EnsureSchema(
                name: "audit");

            migrationBuilder.EnsureSchema(
                name: "import");

            migrationBuilder.EnsureSchema(
                name: "reference");

            migrationBuilder.CreateTable(
                name: "app_settings",
                schema: "system",
                columns: table => new
                {
                    key = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    value_json = table.Column<string>(type: "jsonb", nullable: false),
                    description = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_app_settings", x => x.key);
                });

            migrationBuilder.CreateTable(
                name: "audit_events",
                schema: "audit",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    occurred_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    actor_user_id = table.Column<Guid>(type: "uuid", nullable: true),
                    action = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    entity_type = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: false),
                    entity_id = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    reason = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    correlation_id = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    data_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_audit_events", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "holiday_calendars",
                schema: "system",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    name = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: false),
                    time_zone_id = table.Column<string>(type: "character varying(80)", maxLength: 80, nullable: false),
                    region_code = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_holiday_calendars", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "import_runs",
                schema: "import",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_file_name = table.Column<string>(type: "character varying(260)", maxLength: 260, nullable: false),
                    source_sha256 = table.Column<string>(type: "character varying(64)", maxLength: 64, nullable: false),
                    mode = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    started_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    completed_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    source_size_bytes = table.Column<long>(type: "bigint", nullable: false),
                    report_json = table.Column<string>(type: "jsonb", nullable: true),
                    error_summary = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_import_runs", x => x.id);
                    table.CheckConstraint("ck_import_runs_mode", "mode IN ('Profile', 'DryRun', 'Import')");
                    table.CheckConstraint("ck_import_runs_size", "source_size_bytes >= 0");
                    table.CheckConstraint("ck_import_runs_status", "status IN ('Running', 'Completed', 'Failed')");
                });

            migrationBuilder.CreateTable(
                name: "india_states",
                schema: "reference",
                columns: table => new
                {
                    gst_code = table.Column<string>(type: "character varying(2)", maxLength: 2, nullable: false),
                    name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    is_union_territory = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_india_states", x => x.gst_code);
                });

            migrationBuilder.CreateTable(
                name: "outbox_messages",
                schema: "system",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    occurred_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    message_type = table.Column<string>(type: "character varying(300)", maxLength: 300, nullable: false),
                    payload_json = table.Column<string>(type: "jsonb", nullable: false),
                    processed_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    next_attempt_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: true),
                    attempt_count = table.Column<int>(type: "integer", nullable: false),
                    last_error = table.Column<string>(type: "character varying(2000)", maxLength: 2000, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_outbox_messages", x => x.id);
                    table.CheckConstraint("ck_outbox_attempt_count", "attempt_count >= 0");
                });

            migrationBuilder.CreateTable(
                name: "holidays",
                schema: "system",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    holiday_calendar_id = table.Column<Guid>(type: "uuid", nullable: false),
                    holiday_date = table.Column<DateOnly>(type: "date", nullable: false),
                    name = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: false),
                    holiday_type = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    is_working_day_override = table.Column<bool>(type: "boolean", nullable: false),
                    notes = table.Column<string>(type: "character varying(500)", maxLength: 500, nullable: true),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_holidays", x => x.id);
                    table.CheckConstraint("ck_holidays_type", "holiday_type IN ('Public', 'Firm', 'Optional')");
                    table.ForeignKey(
                        name: "fk_holidays_calendar",
                        column: x => x.holiday_calendar_id,
                        principalSchema: "system",
                        principalTable: "holiday_calendars",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "import_issues",
                schema: "import",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    import_run_id = table.Column<Guid>(type: "uuid", nullable: false),
                    severity = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    issue_code = table.Column<string>(type: "character varying(80)", maxLength: 80, nullable: false),
                    sheet_name = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    row_number = table.Column<int>(type: "integer", nullable: true),
                    column_name = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: true),
                    raw_value = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    normalized_value = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    message = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_import_issues", x => x.id);
                    table.CheckConstraint("ck_import_issues_severity", "severity IN ('Info', 'Warning', 'Error')");
                    table.ForeignKey(
                        name: "fk_import_issues_run",
                        column: x => x.import_run_id,
                        principalSchema: "import",
                        principalTable: "import_runs",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.InsertData(
                schema: "system",
                table: "app_settings",
                columns: new[] { "key", "description", "updated_at_utc", "value_json" },
                values: new object[,]
                {
                    { "organization.time_zone", "IANA time zone used for firm-local dates and scheduling.", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), "\"Asia/Kolkata\"" },
                    { "reporting.financial_year_start", "Start of the Indian financial reporting year.", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), "{\"month\":4,\"day\":1}" }
                });

            migrationBuilder.InsertData(
                schema: "system",
                table: "holiday_calendars",
                columns: new[] { "id", "code", "created_at_utc", "is_active", "name", "region_code", "time_zone_id" },
                values: new object[] { new Guid("70a45f7b-dfde-4af0-a634-876797f19501"), "IN-DEFAULT", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), true, "India firm default", "IN", "Asia/Kolkata" });

            migrationBuilder.InsertData(
                schema: "reference",
                table: "india_states",
                columns: new[] { "gst_code", "is_active", "is_union_territory", "name" },
                values: new object[,]
                {
                    { "01", true, true, "Jammu and Kashmir" },
                    { "02", true, false, "Himachal Pradesh" },
                    { "03", true, false, "Punjab" },
                    { "04", true, true, "Chandigarh" },
                    { "05", true, false, "Uttarakhand" },
                    { "06", true, false, "Haryana" },
                    { "07", true, true, "Delhi" },
                    { "08", true, false, "Rajasthan" },
                    { "09", true, false, "Uttar Pradesh" },
                    { "10", true, false, "Bihar" },
                    { "11", true, false, "Sikkim" },
                    { "12", true, false, "Arunachal Pradesh" },
                    { "13", true, false, "Nagaland" },
                    { "14", true, false, "Manipur" },
                    { "15", true, false, "Mizoram" },
                    { "16", true, false, "Tripura" },
                    { "17", true, false, "Meghalaya" },
                    { "18", true, false, "Assam" },
                    { "19", true, false, "West Bengal" },
                    { "20", true, false, "Jharkhand" },
                    { "21", true, false, "Odisha" },
                    { "22", true, false, "Chhattisgarh" },
                    { "23", true, false, "Madhya Pradesh" },
                    { "24", true, false, "Gujarat" },
                    { "26", true, true, "Dadra and Nagar Haveli and Daman and Diu" },
                    { "27", true, false, "Maharashtra" },
                    { "29", true, false, "Karnataka" },
                    { "30", true, false, "Goa" },
                    { "31", true, true, "Lakshadweep" },
                    { "32", true, false, "Kerala" },
                    { "33", true, false, "Tamil Nadu" },
                    { "34", true, true, "Puducherry" },
                    { "35", true, true, "Andaman and Nicobar Islands" },
                    { "36", true, false, "Telangana" },
                    { "37", true, false, "Andhra Pradesh" },
                    { "38", true, true, "Ladakh" }
                });

            migrationBuilder.CreateIndex(
                name: "ix_audit_events_entity",
                schema: "audit",
                table: "audit_events",
                columns: new[] { "entity_type", "entity_id", "occurred_at_utc" });

            migrationBuilder.CreateIndex(
                name: "ix_audit_events_occurred",
                schema: "audit",
                table: "audit_events",
                column: "occurred_at_utc");

            migrationBuilder.CreateIndex(
                name: "ux_holiday_calendars_code",
                schema: "system",
                table: "holiday_calendars",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_holidays_calendar_date",
                schema: "system",
                table: "holidays",
                columns: new[] { "holiday_calendar_id", "holiday_date" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_import_issues_run_severity_code",
                schema: "import",
                table: "import_issues",
                columns: new[] { "import_run_id", "severity", "issue_code" });

            migrationBuilder.CreateIndex(
                name: "ix_import_runs_source_sha256",
                schema: "import",
                table: "import_runs",
                column: "source_sha256");

            migrationBuilder.CreateIndex(
                name: "ix_import_runs_started",
                schema: "import",
                table: "import_runs",
                column: "started_at_utc");

            migrationBuilder.CreateIndex(
                name: "ux_india_states_name",
                schema: "reference",
                table: "india_states",
                column: "name",
                unique: true);

            migrationBuilder.Sql("""
                DO $permissions$
                BEGIN
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'practice_app') THEN
                        GRANT USAGE ON SCHEMA reference, system, audit, import TO practice_app;
                        GRANT SELECT ON ALL TABLES IN SCHEMA reference TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA system TO practice_app;
                        REVOKE INSERT, UPDATE, DELETE ON system.ef_migrations_history FROM practice_app;
                        GRANT SELECT, INSERT ON ALL TABLES IN SCHEMA audit TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA import TO practice_app;
                        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA import TO practice_app;
                    END IF;
                END
                $permissions$;
                """);

            migrationBuilder.CreateIndex(
                name: "ix_outbox_pending",
                schema: "system",
                table: "outbox_messages",
                columns: new[] { "processed_at_utc", "next_attempt_at_utc" });
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "app_settings",
                schema: "system");

            migrationBuilder.DropTable(
                name: "audit_events",
                schema: "audit");

            migrationBuilder.DropTable(
                name: "holidays",
                schema: "system");

            migrationBuilder.DropTable(
                name: "import_issues",
                schema: "import");

            migrationBuilder.DropTable(
                name: "india_states",
                schema: "reference");

            migrationBuilder.DropTable(
                name: "outbox_messages",
                schema: "system");

            migrationBuilder.DropTable(
                name: "holiday_calendars",
                schema: "system");

            migrationBuilder.DropTable(
                name: "import_runs",
                schema: "import");
        }
    }
}

using System;
using Microsoft.EntityFrameworkCore.Migrations;
using Npgsql.EntityFrameworkCore.PostgreSQL.Metadata;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1861 // Generated migration uses inline column/key arrays.

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class AddClientRegistryAndImportStaging : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.EnsureSchema(
                name: "clients");

            migrationBuilder.CreateTable(
                name: "client_categories",
                schema: "clients",
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
                    table.PrimaryKey("pk_client_categories", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "client_groups",
                schema: "clients",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    code = table.Column<string>(type: "character varying(50)", maxLength: 50, nullable: false),
                    name = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: false),
                    normalized_name = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: false),
                    description = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_client_groups", x => x.id);
                });

            migrationBuilder.CreateTable(
                name: "client_import_mappings",
                schema: "import",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_field = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: false),
                    source_value = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: false),
                    normalized_source_value = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: false),
                    target_type = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    target_id = table.Column<Guid>(type: "uuid", nullable: true),
                    is_approved = table.Column<bool>(type: "boolean", nullable: false),
                    notes = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_by_user_id = table.Column<Guid>(type: "uuid", nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_client_import_mappings", x => x.id);
                    table.CheckConstraint("ck_client_import_mappings_target", "target_type IN ('CATEGORY', 'GROUP')");
                });

            migrationBuilder.CreateTable(
                name: "clients",
                schema: "clients",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    normalized_client_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    legacy_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: true),
                    display_name = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: false),
                    normalized_display_name = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: false),
                    legal_name = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: true),
                    category_id = table.Column<Guid>(type: "uuid", nullable: true),
                    pan = table.Column<string>(type: "character(10)", fixedLength: true, maxLength: 10, nullable: true),
                    tan = table.Column<string>(type: "character(10)", fixedLength: true, maxLength: 10, nullable: true),
                    onboarded_on = table.Column<DateOnly>(type: "date", nullable: true),
                    status = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    deactivated_on = table.Column<DateOnly>(type: "date", nullable: true),
                    deactivation_reason = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    notes = table.Column<string>(type: "character varying(4000)", maxLength: 4000, nullable: true),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_clients", x => x.id);
                    table.CheckConstraint("ck_clients_deactivation", "(status = 'ACTIVE' AND deactivated_on IS NULL AND deactivation_reason IS NULL) OR (status = 'INACTIVE' AND deactivated_on IS NOT NULL AND length(trim(deactivation_reason)) > 0)");
                    table.CheckConstraint("ck_clients_pan", "pan IS NULL OR pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'");
                    table.CheckConstraint("ck_clients_status", "status IN ('ACTIVE', 'INACTIVE')");
                    table.CheckConstraint("ck_clients_tan", "tan IS NULL OR tan ~ '^[A-Z]{4}[0-9]{5}[A-Z]$'");
                    table.ForeignKey(
                        name: "fk_clients_category",
                        column: x => x.category_id,
                        principalSchema: "clients",
                        principalTable: "client_categories",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "client_addresses",
                schema: "clients",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_id = table.Column<Guid>(type: "uuid", nullable: false),
                    address_type = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    line1 = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: false),
                    line2 = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: true),
                    city = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    district = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    state_code = table.Column<string>(type: "character(2)", fixedLength: true, maxLength: 2, nullable: true),
                    postal_code = table.Column<string>(type: "character varying(12)", maxLength: 12, nullable: true),
                    country_code = table.Column<string>(type: "character(2)", fixedLength: true, maxLength: 2, nullable: false),
                    is_primary = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    valid_from = table.Column<DateOnly>(type: "date", nullable: false),
                    valid_to = table.Column<DateOnly>(type: "date", nullable: true),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_client_addresses", x => x.id);
                    table.CheckConstraint("ck_client_addresses_country", "country_code ~ '^[A-Z]{2}$'");
                    table.CheckConstraint("ck_client_addresses_dates", "valid_to IS NULL OR valid_to >= valid_from");
                    table.CheckConstraint("ck_client_addresses_postal", "postal_code IS NULL OR country_code <> 'IN' OR postal_code ~ '^[1-9][0-9]{5}$'");
                    table.ForeignKey(
                        name: "fk_client_addresses_client",
                        column: x => x.client_id,
                        principalSchema: "clients",
                        principalTable: "clients",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_client_addresses_state",
                        column: x => x.state_code,
                        principalSchema: "reference",
                        principalTable: "india_states",
                        principalColumn: "gst_code",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "client_contacts",
                schema: "clients",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_id = table.Column<Guid>(type: "uuid", nullable: false),
                    contact_type = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    name = table.Column<string>(type: "character varying(200)", maxLength: 200, nullable: false),
                    designation = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    phone = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: true),
                    email = table.Column<string>(type: "character varying(320)", maxLength: 320, nullable: true),
                    is_primary = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    notes = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_client_contacts", x => x.id);
                    table.CheckConstraint("ck_client_contacts_type", "contact_type IN ('GENERAL', 'AUTHORIZED_PERSON', 'ACCOUNTS', 'TAX', 'OTHER')");
                    table.ForeignKey(
                        name: "fk_client_contacts_client",
                        column: x => x.client_id,
                        principalSchema: "clients",
                        principalTable: "clients",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "client_group_memberships",
                schema: "clients",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_id = table.Column<Guid>(type: "uuid", nullable: false),
                    group_id = table.Column<Guid>(type: "uuid", nullable: false),
                    membership_type = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    effective_from = table.Column<DateOnly>(type: "date", nullable: false),
                    valid_to = table.Column<DateOnly>(type: "date", nullable: true),
                    notes = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_client_group_memberships", x => x.id);
                    table.CheckConstraint("ck_client_group_memberships_dates", "valid_to IS NULL OR valid_to >= effective_from");
                    table.CheckConstraint("ck_client_group_memberships_type", "membership_type IN ('PRIMARY', 'SECONDARY')");
                    table.ForeignKey(
                        name: "fk_client_group_memberships_client",
                        column: x => x.client_id,
                        principalSchema: "clients",
                        principalTable: "clients",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_client_group_memberships_group",
                        column: x => x.group_id,
                        principalSchema: "clients",
                        principalTable: "client_groups",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.CreateTable(
                name: "client_import_results",
                schema: "import",
                columns: table => new
                {
                    id = table.Column<long>(type: "bigint", nullable: false)
                        .Annotation("Npgsql:ValueGenerationStrategy", NpgsqlValueGenerationStrategy.IdentityByDefaultColumn),
                    import_run_id = table.Column<Guid>(type: "uuid", nullable: false),
                    source_row_number = table.Column<int>(type: "integer", nullable: false),
                    source_client_code = table.Column<string>(type: "character varying(100)", maxLength: 100, nullable: true),
                    proposed_client_code = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: true),
                    client_id = table.Column<Guid>(type: "uuid", nullable: true),
                    outcome = table.Column<string>(type: "character varying(20)", maxLength: 20, nullable: false),
                    data_json = table.Column<string>(type: "jsonb", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_client_import_results", x => x.id);
                    table.CheckConstraint("ck_client_import_results_outcome", "outcome IN ('READY', 'EXCEPTION', 'IMPORTED', 'SKIPPED')");
                    table.ForeignKey(
                        name: "fk_client_import_results_client",
                        column: x => x.client_id,
                        principalSchema: "clients",
                        principalTable: "clients",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Restrict);
                    table.ForeignKey(
                        name: "fk_client_import_results_run",
                        column: x => x.import_run_id,
                        principalSchema: "import",
                        principalTable: "import_runs",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateTable(
                name: "gst_registrations",
                schema: "clients",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_id = table.Column<Guid>(type: "uuid", nullable: false),
                    gstin = table.Column<string>(type: "character(15)", fixedLength: true, maxLength: 15, nullable: false),
                    state_code = table.Column<string>(type: "character(2)", fixedLength: true, maxLength: 2, nullable: false),
                    trade_name = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: true),
                    registration_status = table.Column<string>(type: "character varying(30)", maxLength: 30, nullable: false),
                    effective_from = table.Column<DateOnly>(type: "date", nullable: true),
                    effective_to = table.Column<DateOnly>(type: "date", nullable: true),
                    is_primary = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    cancellation_reason = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_gst_registrations", x => x.id);
                    table.CheckConstraint("ck_gst_registrations_dates", "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from");
                    table.CheckConstraint("ck_gst_registrations_shape", "gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$'");
                    table.CheckConstraint("ck_gst_registrations_state", "substring(gstin from 1 for 2) = state_code");
                    table.CheckConstraint("ck_gst_registrations_status", "registration_status IN ('ACTIVE', 'INACTIVE', 'CANCELLED', 'SUSPENDED')");
                    table.ForeignKey(
                        name: "fk_gst_registrations_client",
                        column: x => x.client_id,
                        principalSchema: "clients",
                        principalTable: "clients",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                    table.ForeignKey(
                        name: "fk_gst_registrations_state",
                        column: x => x.state_code,
                        principalSchema: "reference",
                        principalTable: "india_states",
                        principalColumn: "gst_code",
                        onDelete: ReferentialAction.Restrict);
                });

            migrationBuilder.InsertData(
                schema: "clients",
                table: "client_categories",
                columns: new[] { "id", "code", "display_order", "is_active", "name", "normalized_name" },
                values: new object[,]
                {
                    { new Guid("30000000-0000-0000-0000-000000000001"), "INDIVIDUAL", 10, true, "Individual", "INDIVIDUAL" },
                    { new Guid("30000000-0000-0000-0000-000000000002"), "HUF", 20, true, "HUF", "HUF" },
                    { new Guid("30000000-0000-0000-0000-000000000003"), "PARTNERSHIP", 30, true, "Partnership", "PARTNERSHIP" },
                    { new Guid("30000000-0000-0000-0000-000000000004"), "LLP", 40, true, "LLP", "LLP" },
                    { new Guid("30000000-0000-0000-0000-000000000005"), "PRIVATE_LIMITED", 50, true, "Private Limited Company", "PRIVATE LIMITED COMPANY" },
                    { new Guid("30000000-0000-0000-0000-000000000006"), "PUBLIC_LIMITED", 60, true, "Public Limited Company", "PUBLIC LIMITED COMPANY" },
                    { new Guid("30000000-0000-0000-0000-000000000007"), "TRUST", 70, true, "Trust", "TRUST" },
                    { new Guid("30000000-0000-0000-0000-000000000008"), "SOCIETY", 80, true, "Society", "SOCIETY" },
                    { new Guid("30000000-0000-0000-0000-000000000009"), "PROPRIETORSHIP", 90, true, "Proprietorship", "PROPRIETORSHIP" },
                    { new Guid("30000000-0000-0000-0000-000000000010"), "OPC", 100, true, "One Person Company", "ONE PERSON COMPANY" },
                    { new Guid("30000000-0000-0000-0000-000000000011"), "OTHER", 110, true, "Other", "OTHER" }
                });

            migrationBuilder.InsertData(
                schema: "system",
                table: "field_definitions",
                columns: new[] { "entity_type", "field_key", "description", "is_active", "is_administrator_required", "is_system_required", "label", "updated_at_utc", "updated_by_user_id" },
                values: new object[,]
                {
                    { "clients.client", "categoryId", "Legal constitution such as Individual, LLP or Company.", true, true, false, "Client category", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "clients.client", "clientCode", "Stable firm client code.", true, true, true, "Client code", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "clients.client", "displayName", "Name used in lists and work allocation.", true, true, true, "Client name", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "clients.client", "legalName", "Registered legal name, where different.", true, false, false, "Legal name", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "clients.client", "onboardedOn", "Date the client engagement began.", true, false, false, "Onboarding date", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "clients.client", "pan", "Permanent Account Number.", true, false, false, "PAN", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "clients.client", "primaryAddress", "At least one primary address.", true, false, false, "Primary address", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "clients.client", "primaryContact", "At least one primary contact.", true, false, false, "Primary contact", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null },
                    { "clients.client", "tan", "Tax Deduction and Collection Account Number.", true, false, false, "TAN", new DateTimeOffset(new DateTime(2026, 8, 20, 0, 0, 0, 0, DateTimeKind.Unspecified), new TimeSpan(0, 0, 0, 0, 0)), null }
                });

            migrationBuilder.CreateIndex(
                name: "ix_client_addresses_active",
                schema: "clients",
                table: "client_addresses",
                columns: new[] { "client_id", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ix_client_addresses_postal",
                schema: "clients",
                table: "client_addresses",
                column: "postal_code");

            migrationBuilder.CreateIndex(
                name: "IX_client_addresses_state_code",
                schema: "clients",
                table: "client_addresses",
                column: "state_code");

            migrationBuilder.CreateIndex(
                name: "ux_client_addresses_primary",
                schema: "clients",
                table: "client_addresses",
                columns: new[] { "client_id", "address_type" },
                unique: true,
                filter: "is_primary AND is_active");

            migrationBuilder.CreateIndex(
                name: "ux_client_categories_code",
                schema: "clients",
                table: "client_categories",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_client_categories_name",
                schema: "clients",
                table: "client_categories",
                column: "normalized_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_client_contacts_active",
                schema: "clients",
                table: "client_contacts",
                columns: new[] { "client_id", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ix_client_contacts_email",
                schema: "clients",
                table: "client_contacts",
                column: "email");

            migrationBuilder.CreateIndex(
                name: "ix_client_contacts_phone",
                schema: "clients",
                table: "client_contacts",
                column: "phone");

            migrationBuilder.CreateIndex(
                name: "ux_client_contacts_primary",
                schema: "clients",
                table: "client_contacts",
                columns: new[] { "client_id", "contact_type" },
                unique: true,
                filter: "is_primary AND is_active");

            migrationBuilder.CreateIndex(
                name: "ix_client_group_memberships_group_current",
                schema: "clients",
                table: "client_group_memberships",
                columns: new[] { "group_id", "valid_to", "client_id" });

            migrationBuilder.CreateIndex(
                name: "ux_client_group_memberships_period",
                schema: "clients",
                table: "client_group_memberships",
                columns: new[] { "client_id", "group_id", "effective_from" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_client_group_memberships_primary",
                schema: "clients",
                table: "client_group_memberships",
                column: "client_id",
                unique: true,
                filter: "membership_type = 'PRIMARY' AND valid_to IS NULL");

            migrationBuilder.CreateIndex(
                name: "ux_client_groups_code",
                schema: "clients",
                table: "client_groups",
                column: "code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_client_groups_name",
                schema: "clients",
                table: "client_groups",
                column: "normalized_name",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_client_import_mappings_source",
                schema: "import",
                table: "client_import_mappings",
                columns: new[] { "source_field", "normalized_source_value" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "IX_client_import_results_client_id",
                schema: "import",
                table: "client_import_results",
                column: "client_id");

            migrationBuilder.CreateIndex(
                name: "ix_client_import_results_outcome",
                schema: "import",
                table: "client_import_results",
                columns: new[] { "import_run_id", "outcome" });

            migrationBuilder.CreateIndex(
                name: "ux_client_import_results_run_row",
                schema: "import",
                table: "client_import_results",
                columns: new[] { "import_run_id", "source_row_number" },
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_clients_category_status",
                schema: "clients",
                table: "clients",
                columns: new[] { "category_id", "status" });

            migrationBuilder.CreateIndex(
                name: "ix_clients_legacy_code",
                schema: "clients",
                table: "clients",
                column: "legacy_code");

            migrationBuilder.CreateIndex(
                name: "ix_clients_pan",
                schema: "clients",
                table: "clients",
                column: "pan");

            migrationBuilder.CreateIndex(
                name: "ix_clients_status_name",
                schema: "clients",
                table: "clients",
                columns: new[] { "status", "normalized_display_name" });

            migrationBuilder.CreateIndex(
                name: "ix_clients_tan",
                schema: "clients",
                table: "clients",
                column: "tan");

            migrationBuilder.CreateIndex(
                name: "ux_clients_code",
                schema: "clients",
                table: "clients",
                column: "normalized_client_code",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ix_gst_registrations_client_active",
                schema: "clients",
                table: "gst_registrations",
                columns: new[] { "client_id", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ix_gst_registrations_state_active",
                schema: "clients",
                table: "gst_registrations",
                columns: new[] { "state_code", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ux_gst_registrations_gstin",
                schema: "clients",
                table: "gst_registrations",
                column: "gstin",
                unique: true);

            migrationBuilder.CreateIndex(
                name: "ux_gst_registrations_primary",
                schema: "clients",
                table: "gst_registrations",
                column: "client_id",
                unique: true,
                filter: "is_primary AND is_active");

            migrationBuilder.Sql(
                """
                DO $$
                BEGIN
                    IF EXISTS (SELECT FROM pg_catalog.pg_roles WHERE rolname = 'practice_app') THEN
                        GRANT USAGE ON SCHEMA clients TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON ALL TABLES IN SCHEMA clients TO practice_app;
                        GRANT SELECT, INSERT, UPDATE, DELETE ON import.client_import_mappings, import.client_import_results TO practice_app;
                        GRANT USAGE, SELECT ON ALL SEQUENCES IN SCHEMA import, clients TO practice_app;
                        ALTER DEFAULT PRIVILEGES IN SCHEMA clients
                            GRANT SELECT, INSERT, UPDATE, DELETE ON TABLES TO practice_app;
                    END IF;
                END $$;
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "client_addresses",
                schema: "clients");

            migrationBuilder.DropTable(
                name: "client_contacts",
                schema: "clients");

            migrationBuilder.DropTable(
                name: "client_group_memberships",
                schema: "clients");

            migrationBuilder.DropTable(
                name: "client_import_mappings",
                schema: "import");

            migrationBuilder.DropTable(
                name: "client_import_results",
                schema: "import");

            migrationBuilder.DropTable(
                name: "gst_registrations",
                schema: "clients");

            migrationBuilder.DropTable(
                name: "client_groups",
                schema: "clients");

            migrationBuilder.DropTable(
                name: "clients",
                schema: "clients");

            migrationBuilder.DropTable(
                name: "client_categories",
                schema: "clients");

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "clients.client", "categoryId" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "clients.client", "clientCode" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "clients.client", "displayName" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "clients.client", "legalName" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "clients.client", "onboardedOn" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "clients.client", "pan" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "clients.client", "primaryAddress" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "clients.client", "primaryContact" });

            migrationBuilder.DeleteData(
                schema: "system",
                table: "field_definitions",
                keyColumns: new[] { "entity_type", "field_key" },
                keyValues: new object[] { "clients.client", "tan" });
        }
    }
}

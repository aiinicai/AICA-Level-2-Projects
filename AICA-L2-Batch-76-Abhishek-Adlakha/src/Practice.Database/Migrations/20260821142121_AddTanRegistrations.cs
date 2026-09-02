using System;
using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1861 // Generated migration uses inline column/key arrays.

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class AddTanRegistrations : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.CreateTable(
                name: "tan_registrations",
                schema: "clients",
                columns: table => new
                {
                    id = table.Column<Guid>(type: "uuid", nullable: false),
                    client_id = table.Column<Guid>(type: "uuid", nullable: false),
                    tan = table.Column<string>(type: "character(10)", fixedLength: true, maxLength: 10, nullable: false),
                    deductor_name = table.Column<string>(type: "character varying(250)", maxLength: 250, nullable: true),
                    branch = table.Column<string>(type: "character varying(150)", maxLength: 150, nullable: true),
                    effective_from = table.Column<DateOnly>(type: "date", nullable: true),
                    effective_to = table.Column<DateOnly>(type: "date", nullable: true),
                    is_primary = table.Column<bool>(type: "boolean", nullable: false),
                    is_active = table.Column<bool>(type: "boolean", nullable: false),
                    notes = table.Column<string>(type: "character varying(1000)", maxLength: 1000, nullable: true),
                    created_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false),
                    updated_at_utc = table.Column<DateTimeOffset>(type: "timestamp with time zone", nullable: false)
                },
                constraints: table =>
                {
                    table.PrimaryKey("pk_tan_registrations", x => x.id);
                    table.CheckConstraint("ck_tan_registrations_dates", "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from");
                    table.CheckConstraint("ck_tan_registrations_shape", "tan ~ '^[A-Z]{4}[0-9]{5}[A-Z]$'");
                    table.ForeignKey(
                        name: "fk_tan_registrations_client",
                        column: x => x.client_id,
                        principalSchema: "clients",
                        principalTable: "clients",
                        principalColumn: "id",
                        onDelete: ReferentialAction.Cascade);
                });

            migrationBuilder.CreateIndex(
                name: "ix_tan_registrations_client_active",
                schema: "clients",
                table: "tan_registrations",
                columns: new[] { "client_id", "is_active" });

            migrationBuilder.CreateIndex(
                name: "ix_tan_registrations_tan",
                schema: "clients",
                table: "tan_registrations",
                column: "tan");

            migrationBuilder.CreateIndex(
                name: "ux_tan_registrations_primary",
                schema: "clients",
                table: "tan_registrations",
                column: "client_id",
                unique: true,
                filter: "is_primary AND is_active");

            // Existing clients already carry a single TAN. Copy it in as the primary registration
            // so nothing is stranded on the old column and the new screen shows what is already
            // known. clients.tan continues to mirror whichever registration is primary.
            migrationBuilder.Sql("""
                INSERT INTO clients.tan_registrations
                    (id, client_id, tan, deductor_name, branch, effective_from, effective_to,
                     is_primary, is_active, notes, created_at_utc, updated_at_utc)
                SELECT gen_random_uuid(), c.id, c.tan, NULL, NULL, NULL, NULL,
                       TRUE, TRUE, NULL, now(), now()
                FROM clients.clients c
                WHERE c.tan IS NOT NULL AND c.tan ~ '^[A-Z]{4}[0-9]{5}[A-Z]$';
                """);
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropTable(
                name: "tan_registrations",
                schema: "clients");
        }
    }
}

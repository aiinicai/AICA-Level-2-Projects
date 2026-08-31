using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1861 // Generated migration uses inline column/key arrays.

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class AllowEmployeeImportMappings : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_client_import_mappings_target",
                schema: "import",
                table: "client_import_mappings");

            migrationBuilder.AddCheckConstraint(
                name: "ck_client_import_mappings_target",
                schema: "import",
                table: "client_import_mappings",
                sql: "target_type IN ('CATEGORY', 'GROUP', 'EMPLOYEE')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_client_import_mappings_target",
                schema: "import",
                table: "client_import_mappings");

            migrationBuilder.AddCheckConstraint(
                name: "ck_client_import_mappings_target",
                schema: "import",
                table: "client_import_mappings",
                sql: "target_type IN ('CATEGORY', 'GROUP')");
        }
    }
}

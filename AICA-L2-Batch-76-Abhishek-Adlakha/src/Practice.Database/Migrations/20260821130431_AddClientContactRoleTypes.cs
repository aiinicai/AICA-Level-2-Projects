using Microsoft.EntityFrameworkCore.Migrations;

#nullable disable

#pragma warning disable CA1814 // Prefer jagged arrays over multidimensional
#pragma warning disable CA1861 // Generated migration uses inline column/key arrays.

namespace Practice.Database.Migrations
{
    /// <inheritdoc />
    public partial class AddClientContactRoleTypes : Migration
    {
        /// <inheritdoc />
        protected override void Up(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_client_contacts_type",
                schema: "clients",
                table: "client_contacts");

            migrationBuilder.AddCheckConstraint(
                name: "ck_client_contacts_type",
                schema: "clients",
                table: "client_contacts",
                sql: "contact_type IN ('GENERAL', 'AUTHORIZED_PERSON', 'ACCOUNTS', 'TAX', 'OWNER', 'DIRECTOR', 'PARTNER', 'ACCOUNTANT', 'OTHER')");
        }

        /// <inheritdoc />
        protected override void Down(MigrationBuilder migrationBuilder)
        {
            migrationBuilder.DropCheckConstraint(
                name: "ck_client_contacts_type",
                schema: "clients",
                table: "client_contacts");

            migrationBuilder.AddCheckConstraint(
                name: "ck_client_contacts_type",
                schema: "clients",
                table: "client_contacts",
                sql: "contact_type IN ('GENERAL', 'AUTHORIZED_PERSON', 'ACCOUNTS', 'TAX', 'OTHER')");
        }
    }
}

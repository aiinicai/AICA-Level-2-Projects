using Microsoft.EntityFrameworkCore;
using Practice.Database.Entities;

namespace Practice.Database;

internal static class ClientModel
{
    public static void Configure(ModelBuilder modelBuilder)
    {
        ConfigureCategories(modelBuilder);
        ConfigureClients(modelBuilder);
        ConfigureContacts(modelBuilder);
        ConfigureAddresses(modelBuilder);
        ConfigureGst(modelBuilder);
        ConfigureGroups(modelBuilder);
        ConfigureImport(modelBuilder);
    }

    private static void ConfigureCategories(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ClientCategory>();
        entity.ToTable("client_categories", "clients");
        entity.HasKey(x => x.Id).HasName("pk_client_categories");
        entity.Property(x => x.Id).HasColumnName("id");
        entity.Property(x => x.Code).HasColumnName("code").HasMaxLength(50);
        entity.Property(x => x.Name).HasColumnName("name").HasMaxLength(120);
        entity.Property(x => x.NormalizedName).HasColumnName("normalized_name").HasMaxLength(120);
        entity.Property(x => x.DisplayOrder).HasColumnName("display_order");
        entity.Property(x => x.IsActive).HasColumnName("is_active");
        entity.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_client_categories_code");
        entity.HasIndex(x => x.NormalizedName).IsUnique().HasDatabaseName("ux_client_categories_name");
        entity.HasData(ClientSeed.Categories);
    }

    private static void ConfigureClients(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<Client>();
        entity.ToTable("clients", "clients", table =>
        {
            table.HasCheckConstraint("ck_clients_status", "status IN ('ACTIVE', 'INACTIVE')");
            table.HasCheckConstraint("ck_clients_pan", "pan IS NULL OR pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'");
            table.HasCheckConstraint("ck_clients_tan", "tan IS NULL OR tan ~ '^[A-Z]{4}[0-9]{5}[A-Z]$'");
            table.HasCheckConstraint("ck_clients_deactivation", "(status = 'ACTIVE' AND deactivated_on IS NULL AND deactivation_reason IS NULL) OR (status = 'INACTIVE' AND deactivated_on IS NOT NULL AND length(trim(deactivation_reason)) > 0)");
        });
        entity.HasKey(x => x.Id).HasName("pk_clients");
        entity.Property(x => x.Id).HasColumnName("id");
        entity.Property(x => x.ClientCode).HasColumnName("client_code").HasMaxLength(30);
        entity.Property(x => x.NormalizedClientCode).HasColumnName("normalized_client_code").HasMaxLength(30);
        entity.Property(x => x.LegacyCode).HasColumnName("legacy_code").HasMaxLength(30);
        entity.Property(x => x.DisplayName).HasColumnName("display_name").HasMaxLength(250);
        entity.Property(x => x.NormalizedDisplayName).HasColumnName("normalized_display_name").HasMaxLength(250);
        entity.Property(x => x.LegalName).HasColumnName("legal_name").HasMaxLength(250);
        entity.Property(x => x.CategoryId).HasColumnName("category_id");
        entity.Property(x => x.Pan).HasColumnName("pan").HasMaxLength(10).IsFixedLength();
        entity.Property(x => x.Tan).HasColumnName("tan").HasMaxLength(10).IsFixedLength();
        entity.Property(x => x.OnboardedOn).HasColumnName("onboarded_on");
        entity.Property(x => x.Status).HasColumnName("status").HasMaxLength(20);
        entity.Property(x => x.DeactivatedOn).HasColumnName("deactivated_on");
        entity.Property(x => x.DeactivationReason).HasColumnName("deactivation_reason").HasMaxLength(1000);
        entity.Property(x => x.Notes).HasColumnName("notes").HasMaxLength(4000);
        entity.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        entity.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        entity.HasOne(x => x.Category).WithMany(x => x.Clients).HasForeignKey(x => x.CategoryId)
            .OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_clients_category");
        entity.HasIndex(x => x.NormalizedClientCode).IsUnique().HasDatabaseName("ux_clients_code");
        entity.HasIndex(x => new { x.Status, x.NormalizedDisplayName }).HasDatabaseName("ix_clients_status_name");
        entity.HasIndex(x => new { x.CategoryId, x.Status }).HasDatabaseName("ix_clients_category_status");
        entity.HasIndex(x => x.Pan).HasDatabaseName("ix_clients_pan");
        entity.HasIndex(x => x.Tan).HasDatabaseName("ix_clients_tan");
        entity.HasIndex(x => x.LegacyCode).HasDatabaseName("ix_clients_legacy_code");
    }

    private static void ConfigureContacts(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ClientContact>();
        entity.ToTable("client_contacts", "clients", table => table.HasCheckConstraint(
            "ck_client_contacts_type", "contact_type IN ('GENERAL', 'AUTHORIZED_PERSON', 'ACCOUNTS', 'TAX', 'OWNER', 'DIRECTOR', 'PARTNER', 'ACCOUNTANT', 'OTHER')"));
        entity.HasKey(x => x.Id).HasName("pk_client_contacts");
        entity.Property(x => x.Id).HasColumnName("id"); entity.Property(x => x.ClientId).HasColumnName("client_id");
        entity.Property(x => x.ContactType).HasColumnName("contact_type").HasMaxLength(30);
        entity.Property(x => x.Name).HasColumnName("name").HasMaxLength(200);
        entity.Property(x => x.Designation).HasColumnName("designation").HasMaxLength(100);
        entity.Property(x => x.Phone).HasColumnName("phone").HasMaxLength(20);
        entity.Property(x => x.Email).HasColumnName("email").HasMaxLength(320);
        entity.Property(x => x.IsPrimary).HasColumnName("is_primary"); entity.Property(x => x.IsActive).HasColumnName("is_active");
        entity.Property(x => x.Notes).HasColumnName("notes").HasMaxLength(1000);
        entity.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc"); entity.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        entity.HasOne(x => x.Client).WithMany(x => x.Contacts).HasForeignKey(x => x.ClientId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_client_contacts_client");
        entity.HasIndex(x => new { x.ClientId, x.ContactType }).IsUnique().HasFilter("is_primary AND is_active").HasDatabaseName("ux_client_contacts_primary");
        entity.HasIndex(x => new { x.ClientId, x.IsActive }).HasDatabaseName("ix_client_contacts_active");
        entity.HasIndex(x => x.Phone).HasDatabaseName("ix_client_contacts_phone"); entity.HasIndex(x => x.Email).HasDatabaseName("ix_client_contacts_email");
    }

    private static void ConfigureAddresses(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<ClientAddress>();
        entity.ToTable("client_addresses", "clients", table =>
        {
            table.HasCheckConstraint("ck_client_addresses_dates", "valid_to IS NULL OR valid_to >= valid_from");
            table.HasCheckConstraint("ck_client_addresses_country", "country_code ~ '^[A-Z]{2}$'");
            table.HasCheckConstraint("ck_client_addresses_postal", "postal_code IS NULL OR country_code <> 'IN' OR postal_code ~ '^[1-9][0-9]{5}$'");
        });
        entity.HasKey(x => x.Id).HasName("pk_client_addresses");
        entity.Property(x => x.Id).HasColumnName("id"); entity.Property(x => x.ClientId).HasColumnName("client_id");
        entity.Property(x => x.AddressType).HasColumnName("address_type").HasMaxLength(30); entity.Property(x => x.Line1).HasColumnName("line1").HasMaxLength(250);
        entity.Property(x => x.Line2).HasColumnName("line2").HasMaxLength(250); entity.Property(x => x.City).HasColumnName("city").HasMaxLength(100);
        entity.Property(x => x.District).HasColumnName("district").HasMaxLength(100); entity.Property(x => x.StateCode).HasColumnName("state_code").HasMaxLength(2).IsFixedLength();
        entity.Property(x => x.PostalCode).HasColumnName("postal_code").HasMaxLength(12); entity.Property(x => x.CountryCode).HasColumnName("country_code").HasMaxLength(2).IsFixedLength();
        entity.Property(x => x.IsPrimary).HasColumnName("is_primary"); entity.Property(x => x.IsActive).HasColumnName("is_active");
        entity.Property(x => x.ValidFrom).HasColumnName("valid_from"); entity.Property(x => x.ValidTo).HasColumnName("valid_to");
        entity.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc"); entity.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        entity.HasOne(x => x.Client).WithMany(x => x.Addresses).HasForeignKey(x => x.ClientId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_client_addresses_client");
        entity.HasOne(x => x.State).WithMany().HasForeignKey(x => x.StateCode).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_client_addresses_state");
        entity.HasIndex(x => new { x.ClientId, x.AddressType }).IsUnique().HasFilter("is_primary AND is_active").HasDatabaseName("ux_client_addresses_primary");
        entity.HasIndex(x => new { x.ClientId, x.IsActive }).HasDatabaseName("ix_client_addresses_active"); entity.HasIndex(x => x.PostalCode).HasDatabaseName("ix_client_addresses_postal");
    }

    private static void ConfigureGst(ModelBuilder modelBuilder)
    {
        var entity = modelBuilder.Entity<GstRegistration>();
        entity.ToTable("gst_registrations", "clients", table =>
        {
            table.HasCheckConstraint("ck_gst_registrations_shape", "gstin ~ '^[0-9]{2}[A-Z]{5}[0-9]{4}[A-Z][0-9A-Z]Z[0-9A-Z]$'");
            table.HasCheckConstraint("ck_gst_registrations_state", "substring(gstin from 1 for 2) = state_code");
            table.HasCheckConstraint("ck_gst_registrations_dates", "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from");
            table.HasCheckConstraint("ck_gst_registrations_status", "registration_status IN ('ACTIVE', 'INACTIVE', 'CANCELLED', 'SUSPENDED')");
        });
        entity.HasKey(x => x.Id).HasName("pk_gst_registrations");
        entity.HasAlternateKey(x => new { x.Id, x.ClientId }).HasName("ak_gst_registrations_id_client");
        entity.Property(x => x.Id).HasColumnName("id"); entity.Property(x => x.ClientId).HasColumnName("client_id");
        entity.Property(x => x.Gstin).HasColumnName("gstin").HasMaxLength(15).IsFixedLength(); entity.Property(x => x.StateCode).HasColumnName("state_code").HasMaxLength(2).IsFixedLength();
        entity.Property(x => x.TradeName).HasColumnName("trade_name").HasMaxLength(250); entity.Property(x => x.RegistrationStatus).HasColumnName("registration_status").HasMaxLength(30);
        entity.Property(x => x.EffectiveFrom).HasColumnName("effective_from"); entity.Property(x => x.EffectiveTo).HasColumnName("effective_to");
        entity.Property(x => x.IsPrimary).HasColumnName("is_primary"); entity.Property(x => x.IsActive).HasColumnName("is_active"); entity.Property(x => x.CancellationReason).HasColumnName("cancellation_reason").HasMaxLength(1000);
        entity.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc"); entity.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        entity.HasOne(x => x.Client).WithMany(x => x.GstRegistrations).HasForeignKey(x => x.ClientId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_gst_registrations_client");
        entity.HasOne(x => x.State).WithMany().HasForeignKey(x => x.StateCode).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_gst_registrations_state");
        entity.HasIndex(x => x.Gstin).IsUnique().HasDatabaseName("ux_gst_registrations_gstin");
        entity.HasIndex(x => x.ClientId).IsUnique().HasFilter("is_primary AND is_active").HasDatabaseName("ux_gst_registrations_primary");
        entity.HasIndex(x => new { x.ClientId, x.IsActive }).HasDatabaseName("ix_gst_registrations_client_active"); entity.HasIndex(x => new { x.StateCode, x.IsActive }).HasDatabaseName("ix_gst_registrations_state_active");
    }

    private static void ConfigureGroups(ModelBuilder modelBuilder)
    {
        var tan = modelBuilder.Entity<TanRegistration>();
        tan.ToTable("tan_registrations", "clients", table =>
        {
            table.HasCheckConstraint("ck_tan_registrations_shape", "tan ~ '^[A-Z]{4}[0-9]{5}[A-Z]$'");
            table.HasCheckConstraint("ck_tan_registrations_dates", "effective_to IS NULL OR effective_from IS NULL OR effective_to >= effective_from");
        });
        tan.HasKey(x => x.Id).HasName("pk_tan_registrations");
        tan.Property(x => x.Id).HasColumnName("id");
        tan.Property(x => x.ClientId).HasColumnName("client_id");
        tan.Property(x => x.Tan).HasColumnName("tan").HasMaxLength(10).IsFixedLength();
        tan.Property(x => x.DeductorName).HasColumnName("deductor_name").HasMaxLength(250);
        tan.Property(x => x.Branch).HasColumnName("branch").HasMaxLength(150);
        tan.Property(x => x.EffectiveFrom).HasColumnName("effective_from");
        tan.Property(x => x.EffectiveTo).HasColumnName("effective_to");
        tan.Property(x => x.IsPrimary).HasColumnName("is_primary");
        tan.Property(x => x.IsActive).HasColumnName("is_active");
        tan.Property(x => x.Notes).HasColumnName("notes").HasMaxLength(1000);
        tan.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc");
        tan.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        tan.HasOne(x => x.Client).WithMany(x => x.TanRegistrations).HasForeignKey(x => x.ClientId)
            .OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_tan_registrations_client");
        // A TAN should identify one deductor, but the source workbook already contains the same TAN
        // against two different PANs. Following BIZ-003, duplicates are reported rather than
        // enforced, so this stays a plain index until the firm has signed off the exceptions.
        tan.HasIndex(x => x.Tan).HasDatabaseName("ix_tan_registrations_tan");
        tan.HasIndex(x => x.ClientId).IsUnique().HasFilter("is_primary AND is_active").HasDatabaseName("ux_tan_registrations_primary");
        tan.HasIndex(x => new { x.ClientId, x.IsActive }).HasDatabaseName("ix_tan_registrations_client_active");

        var group = modelBuilder.Entity<ClientGroup>();
        group.ToTable("client_groups", "clients"); group.HasKey(x => x.Id).HasName("pk_client_groups");
        group.Property(x => x.Id).HasColumnName("id"); group.Property(x => x.Code).HasColumnName("code").HasMaxLength(50); group.Property(x => x.Name).HasColumnName("name").HasMaxLength(150);
        group.Property(x => x.NormalizedName).HasColumnName("normalized_name").HasMaxLength(150); group.Property(x => x.Description).HasColumnName("description").HasMaxLength(1000);
        group.Property(x => x.IsActive).HasColumnName("is_active"); group.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc"); group.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        group.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_client_groups_code"); group.HasIndex(x => x.NormalizedName).IsUnique().HasDatabaseName("ux_client_groups_name");

        var membership = modelBuilder.Entity<ClientGroupMembership>();
        membership.ToTable("client_group_memberships", "clients", table =>
        {
            table.HasCheckConstraint("ck_client_group_memberships_type", "membership_type IN ('PRIMARY', 'SECONDARY')");
            table.HasCheckConstraint("ck_client_group_memberships_dates", "valid_to IS NULL OR valid_to >= effective_from");
        });
        membership.HasKey(x => x.Id).HasName("pk_client_group_memberships");
        membership.Property(x => x.Id).HasColumnName("id"); membership.Property(x => x.ClientId).HasColumnName("client_id"); membership.Property(x => x.GroupId).HasColumnName("group_id");
        membership.Property(x => x.MembershipType).HasColumnName("membership_type").HasMaxLength(20); membership.Property(x => x.EffectiveFrom).HasColumnName("effective_from"); membership.Property(x => x.ValidTo).HasColumnName("valid_to"); membership.Property(x => x.Notes).HasColumnName("notes").HasMaxLength(1000);
        membership.HasOne(x => x.Client).WithMany(x => x.GroupMemberships).HasForeignKey(x => x.ClientId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_client_group_memberships_client");
        membership.HasOne(x => x.Group).WithMany(x => x.Memberships).HasForeignKey(x => x.GroupId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_client_group_memberships_group");
        membership.HasIndex(x => new { x.ClientId, x.GroupId, x.EffectiveFrom }).IsUnique().HasDatabaseName("ux_client_group_memberships_period");
        membership.HasIndex(x => x.ClientId).IsUnique().HasFilter("membership_type = 'PRIMARY' AND valid_to IS NULL").HasDatabaseName("ux_client_group_memberships_primary");
        membership.HasIndex(x => new { x.GroupId, x.ValidTo, x.ClientId }).HasDatabaseName("ix_client_group_memberships_group_current");
    }

    private static void ConfigureImport(ModelBuilder modelBuilder)
    {
        var mapping = modelBuilder.Entity<ClientImportMapping>();
        mapping.ToTable("client_import_mappings", "import", table => table.HasCheckConstraint("ck_client_import_mappings_target", "target_type IN ('CATEGORY', 'GROUP', 'EMPLOYEE')"));
        mapping.HasKey(x => x.Id).HasName("pk_client_import_mappings"); mapping.Property(x => x.Id).HasColumnName("id");
        mapping.Property(x => x.SourceField).HasColumnName("source_field").HasMaxLength(100); mapping.Property(x => x.SourceValue).HasColumnName("source_value").HasMaxLength(250); mapping.Property(x => x.NormalizedSourceValue).HasColumnName("normalized_source_value").HasMaxLength(250);
        mapping.Property(x => x.TargetType).HasColumnName("target_type").HasMaxLength(30); mapping.Property(x => x.TargetId).HasColumnName("target_id"); mapping.Property(x => x.IsApproved).HasColumnName("is_approved"); mapping.Property(x => x.Notes).HasColumnName("notes").HasMaxLength(1000); mapping.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc"); mapping.Property(x => x.UpdatedByUserId).HasColumnName("updated_by_user_id");
        mapping.HasIndex(x => new { x.SourceField, x.NormalizedSourceValue }).IsUnique().HasDatabaseName("ux_client_import_mappings_source");

        var result = modelBuilder.Entity<ClientImportResult>();
        result.ToTable("client_import_results", "import", table => table.HasCheckConstraint("ck_client_import_results_outcome", "outcome IN ('READY', 'EXCEPTION', 'IMPORTED', 'SKIPPED')"));
        result.HasKey(x => x.Id).HasName("pk_client_import_results"); result.Property(x => x.Id).HasColumnName("id").UseIdentityByDefaultColumn();
        result.Property(x => x.ImportRunId).HasColumnName("import_run_id"); result.Property(x => x.SourceRowNumber).HasColumnName("source_row_number"); result.Property(x => x.SourceClientCode).HasColumnName("source_client_code").HasMaxLength(100); result.Property(x => x.ProposedClientCode).HasColumnName("proposed_client_code").HasMaxLength(30); result.Property(x => x.ClientId).HasColumnName("client_id"); result.Property(x => x.Outcome).HasColumnName("outcome").HasMaxLength(20); result.Property(x => x.DataJson).HasColumnName("data_json").HasColumnType("jsonb");
        result.HasOne(x => x.ImportRun).WithMany().HasForeignKey(x => x.ImportRunId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_client_import_results_run");
        result.HasOne<Client>().WithMany().HasForeignKey(x => x.ClientId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_client_import_results_client");
        result.HasIndex(x => new { x.ImportRunId, x.SourceRowNumber }).IsUnique().HasDatabaseName("ux_client_import_results_run_row"); result.HasIndex(x => new { x.ImportRunId, x.Outcome }).HasDatabaseName("ix_client_import_results_outcome");
    }
}

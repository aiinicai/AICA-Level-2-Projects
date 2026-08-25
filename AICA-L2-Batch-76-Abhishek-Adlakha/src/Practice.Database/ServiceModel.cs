using Microsoft.EntityFrameworkCore;
using Practice.Database.Entities;

namespace Practice.Database;

internal static class ServiceModel
{
    public static void Configure(ModelBuilder modelBuilder)
    {
        var category = modelBuilder.Entity<ServiceCategory>();
        category.ToTable("service_categories", "services");
        category.HasKey(x => x.Id).HasName("pk_service_categories");
        category.Property(x => x.Id).HasColumnName("id"); category.Property(x => x.Code).HasColumnName("code").HasMaxLength(50);
        category.Property(x => x.Name).HasColumnName("name").HasMaxLength(120); category.Property(x => x.NormalizedName).HasColumnName("normalized_name").HasMaxLength(120);
        category.Property(x => x.DisplayOrder).HasColumnName("display_order"); category.Property(x => x.IsActive).HasColumnName("is_active");
        category.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_service_categories_code");
        category.HasIndex(x => x.NormalizedName).IsUnique().HasDatabaseName("ux_service_categories_name");
        category.HasData(ServiceSeed.Categories);

        var service = modelBuilder.Entity<ServiceDefinition>();
        service.ToTable("services", "services"); service.HasKey(x => x.Id).HasName("pk_services");
        service.Property(x => x.Id).HasColumnName("id"); service.Property(x => x.CategoryId).HasColumnName("category_id");
        service.Property(x => x.Code).HasColumnName("code").HasMaxLength(50); service.Property(x => x.Name).HasColumnName("name").HasMaxLength(150);
        service.Property(x => x.NormalizedName).HasColumnName("normalized_name").HasMaxLength(150); service.Property(x => x.Description).HasColumnName("description").HasMaxLength(1000);
        service.Property(x => x.DefaultBillable).HasColumnName("default_billable"); service.Property(x => x.SupportsRecurrence).HasColumnName("supports_recurrence");
        service.Property(x => x.SupportsGstinScope).HasColumnName("supports_gstin_scope"); service.Property(x => x.IsActive).HasColumnName("is_active");
        service.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc"); service.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        service.HasOne(x => x.Category).WithMany(x => x.Services).HasForeignKey(x => x.CategoryId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_services_category");
        service.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_services_code"); service.HasIndex(x => x.NormalizedName).IsUnique().HasDatabaseName("ux_services_name");
        service.HasIndex(x => new { x.CategoryId, x.IsActive }).HasDatabaseName("ix_services_category_active"); service.HasData(ServiceSeed.Services);

        var clientService = modelBuilder.Entity<ClientService>();
        clientService.ToTable("client_services", "services", table =>
        {
            table.HasCheckConstraint("ck_client_services_dates", "effective_to IS NULL OR effective_to >= effective_from");
            table.HasCheckConstraint("ck_client_services_priority", "default_priority IN ('LOW', 'NORMAL', 'HIGH', 'URGENT')");
            table.HasCheckConstraint("ck_client_services_deactivation", "(is_active AND deactivated_at_utc IS NULL AND deactivation_reason IS NULL) OR (NOT is_active AND deactivated_at_utc IS NOT NULL AND length(trim(deactivation_reason)) > 0)");
        });
        clientService.HasKey(x => x.Id).HasName("pk_client_services");
        clientService.Property(x => x.Id).HasColumnName("id"); clientService.Property(x => x.ClientId).HasColumnName("client_id"); clientService.Property(x => x.ServiceId).HasColumnName("service_id");
        clientService.Property(x => x.GstRegistrationId).HasColumnName("gst_registration_id"); clientService.Property(x => x.EngagementCode).HasColumnName("engagement_code").HasMaxLength(50);
        clientService.Property(x => x.TitleOverride).HasColumnName("title_override").HasMaxLength(200); clientService.Property(x => x.EffectiveFrom).HasColumnName("effective_from");
        clientService.Property(x => x.EffectiveTo).HasColumnName("effective_to"); clientService.Property(x => x.IsActive).HasColumnName("is_active");
        clientService.Property(x => x.DefaultPriority).HasColumnName("default_priority").HasMaxLength(20); clientService.Property(x => x.ResponsibleTeamId).HasColumnName("responsible_team_id");
        clientService.Property(x => x.Notes).HasColumnName("notes").HasMaxLength(2000); clientService.Property(x => x.DeactivatedAtUtc).HasColumnName("deactivated_at_utc");
        clientService.Property(x => x.DeactivationReason).HasColumnName("deactivation_reason").HasMaxLength(1000); clientService.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc"); clientService.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        clientService.HasOne(x => x.Client).WithMany().HasForeignKey(x => x.ClientId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_client_services_client");
        clientService.HasOne(x => x.Service).WithMany(x => x.ClientServices).HasForeignKey(x => x.ServiceId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_client_services_service");
        clientService.HasOne(x => x.GstRegistration).WithMany().HasForeignKey(x => new { x.GstRegistrationId, x.ClientId })
            .HasPrincipalKey(x => new { x.Id, x.ClientId }).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_client_services_gstin_client");
        clientService.HasOne(x => x.ResponsibleTeam).WithMany().HasForeignKey(x => x.ResponsibleTeamId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_client_services_team");
        clientService.HasIndex(x => new { x.ClientId, x.ServiceId }).IsUnique().HasFilter("is_active AND gst_registration_id IS NULL").HasDatabaseName("ux_client_services_unscoped_active");
        clientService.HasIndex(x => new { x.ClientId, x.ServiceId, x.GstRegistrationId }).IsUnique().HasFilter("is_active AND gst_registration_id IS NOT NULL").HasDatabaseName("ux_client_services_gstin_active");
        clientService.HasIndex(x => new { x.ClientId, x.IsActive }).HasDatabaseName("ix_client_services_client_active");
        clientService.HasIndex(x => new { x.ServiceId, x.IsActive }).HasDatabaseName("ix_client_services_service_active");
        clientService.HasIndex(x => new { x.ResponsibleTeamId, x.IsActive }).HasDatabaseName("ix_client_services_team_active");

        var proposal = modelBuilder.Entity<ServiceImportProposal>();
        proposal.ToTable("service_import_proposals", "import", table => table.HasCheckConstraint("ck_service_import_proposals_outcome", "outcome IN ('READY', 'EXCEPTION', 'IMPORTED', 'SKIPPED')"));
        proposal.HasKey(x => x.Id).HasName("pk_service_import_proposals"); proposal.Property(x => x.Id).HasColumnName("id").UseIdentityByDefaultColumn();
        proposal.Property(x => x.ImportRunId).HasColumnName("import_run_id"); proposal.Property(x => x.SourceRowNumber).HasColumnName("source_row_number");
        proposal.Property(x => x.SourceClientCode).HasColumnName("source_client_code").HasMaxLength(100); proposal.Property(x => x.ProposedClientCode).HasColumnName("proposed_client_code").HasMaxLength(30);
        proposal.Property(x => x.SourceColumn).HasColumnName("source_column").HasMaxLength(100); proposal.Property(x => x.ServiceCode).HasColumnName("service_code").HasMaxLength(50);
        proposal.Property(x => x.ProposedGstin).HasColumnName("proposed_gstin").HasMaxLength(15); proposal.Property(x => x.ClientServiceId).HasColumnName("client_service_id");
        proposal.Property(x => x.Outcome).HasColumnName("outcome").HasMaxLength(20); proposal.Property(x => x.DataJson).HasColumnName("data_json").HasColumnType("jsonb");
        proposal.HasOne(x => x.ImportRun).WithMany().HasForeignKey(x => x.ImportRunId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_service_import_proposals_run");
        proposal.HasOne(x => x.ClientService).WithMany().HasForeignKey(x => x.ClientServiceId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_service_import_proposals_client_service");
        proposal.HasIndex(x => new { x.ImportRunId, x.SourceRowNumber, x.ServiceCode }).IsUnique().HasDatabaseName("ux_service_import_proposals_run_row_service");
        proposal.HasIndex(x => new { x.ImportRunId, x.Outcome }).HasDatabaseName("ix_service_import_proposals_outcome");
    }
}

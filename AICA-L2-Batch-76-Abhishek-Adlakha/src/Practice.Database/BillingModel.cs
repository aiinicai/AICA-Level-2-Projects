using Microsoft.EntityFrameworkCore;
using Practice.Database.Entities;

namespace Practice.Database;

internal static class BillingModel
{
    public static void Configure(ModelBuilder modelBuilder)
    {
        ConfigureEntity(modelBuilder.Entity<BillingEntity>());
        ConfigureTerm(modelBuilder.Entity<BillingTerm>());
        ConfigureSchedule(modelBuilder.Entity<BillingSchedule>());
        ConfigureScheduleMonth(modelBuilder.Entity<BillingScheduleMonth>());
        ConfigureImportProposal(modelBuilder.Entity<BillingImportProposal>());
    }

    private static void ConfigureEntity(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<BillingEntity> entity)
    {
        entity.ToTable("billing_entities", "billing", table =>
        {
            table.HasCheckConstraint("ck_billing_entities_dates", "effective_to IS NULL OR effective_to >= effective_from");
            table.HasCheckConstraint("ck_billing_entities_currency", "currency_code ~ '^[A-Z]{3}$'");
            table.HasCheckConstraint("ck_billing_entities_pan", "pan IS NULL OR pan ~ '^[A-Z]{5}[0-9]{4}[A-Z]$'");
            table.HasCheckConstraint("ck_billing_entities_gstin", "gstin IS NULL OR gstin ~ '^[0-9]{2}[A-Z0-9]{13}$'");
        });
        entity.HasKey(x => x.Id).HasName("pk_billing_entities");
        entity.Property(x => x.Id).HasColumnName("id"); entity.Property(x => x.Code).HasColumnName("code").HasMaxLength(30);
        entity.Property(x => x.LegalName).HasColumnName("legal_name").HasMaxLength(200); entity.Property(x => x.TradeName).HasColumnName("trade_name").HasMaxLength(200);
        entity.Property(x => x.Pan).HasColumnName("pan").HasMaxLength(10).IsFixedLength(); entity.Property(x => x.Gstin).HasColumnName("gstin").HasMaxLength(15).IsFixedLength();
        entity.Property(x => x.Address).HasColumnName("address").HasMaxLength(1000); entity.Property(x => x.Email).HasColumnName("email").HasMaxLength(320);
        entity.Property(x => x.Phone).HasColumnName("phone").HasMaxLength(30); entity.Property(x => x.CurrencyCode).HasColumnName("currency_code").HasMaxLength(3).IsFixedLength();
        entity.Property(x => x.EffectiveFrom).HasColumnName("effective_from"); entity.Property(x => x.EffectiveTo).HasColumnName("effective_to"); entity.Property(x => x.IsActive).HasColumnName("is_active");
        entity.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc"); entity.Property(x => x.UpdatedAtUtc).HasColumnName("updated_at_utc");
        entity.Property(x => x.RowVersion).HasColumnName("row_version").IsConcurrencyToken();
        entity.HasIndex(x => x.Code).IsUnique().HasDatabaseName("ux_billing_entities_code");
        entity.HasIndex(x => x.Gstin).IsUnique().HasFilter("gstin IS NOT NULL").HasDatabaseName("ux_billing_entities_gstin");
        entity.HasIndex(x => new { x.IsActive, x.LegalName }).HasDatabaseName("ix_billing_entities_active_name");
    }

    private static void ConfigureTerm(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<BillingTerm> term)
    {
        term.ToTable("billing_terms", "billing", table =>
        {
            table.HasCheckConstraint("ck_billing_terms_dates", "effective_to IS NULL OR effective_to >= effective_from");
            table.HasCheckConstraint("ck_billing_terms_pricing", "pricing_model = 'FIXED'");
            table.HasCheckConstraint("ck_billing_terms_currency", "currency_code ~ '^[A-Z]{3}$'");
            table.HasCheckConstraint("ck_billing_terms_amount", "(is_billable AND billing_entity_id IS NOT NULL AND amount IS NOT NULL AND amount >= 0) OR (NOT is_billable AND billing_entity_id IS NULL AND amount IS NULL)");
            table.HasCheckConstraint("ck_billing_terms_version", "version > 0");
        });
        term.HasKey(x => x.Id).HasName("pk_billing_terms");
        term.Property(x => x.Id).HasColumnName("id"); term.Property(x => x.ClientServiceId).HasColumnName("client_service_id"); term.Property(x => x.BillingEntityId).HasColumnName("billing_entity_id");
        term.Property(x => x.IsBillable).HasColumnName("is_billable"); term.Property(x => x.PricingModel).HasColumnName("pricing_model").HasMaxLength(20);
        term.Property(x => x.Amount).HasColumnName("amount").HasPrecision(19, 2); term.Property(x => x.CurrencyCode).HasColumnName("currency_code").HasMaxLength(3).IsFixedLength();
        term.Property(x => x.TaxInclusive).HasColumnName("tax_inclusive"); term.Property(x => x.EffectiveFrom).HasColumnName("effective_from"); term.Property(x => x.EffectiveTo).HasColumnName("effective_to");
        term.Property(x => x.Version).HasColumnName("version"); term.Property(x => x.Notes).HasColumnName("notes").HasMaxLength(2000);
        term.Property(x => x.CreatedAtUtc).HasColumnName("created_at_utc"); term.Property(x => x.CreatedByUserId).HasColumnName("created_by_user_id");
        term.HasOne(x => x.ClientService).WithMany().HasForeignKey(x => x.ClientServiceId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_billing_terms_client_service");
        term.HasOne(x => x.BillingEntity).WithMany(x => x.Terms).HasForeignKey(x => x.BillingEntityId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_billing_terms_entity");
        term.HasOne(x => x.CreatedByUser).WithMany().HasForeignKey(x => x.CreatedByUserId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_billing_terms_creator");
        term.HasIndex(x => new { x.ClientServiceId, x.Version }).IsUnique().HasDatabaseName("ux_billing_terms_agreement_version");
        term.HasIndex(x => new { x.ClientServiceId, x.EffectiveFrom, x.EffectiveTo }).HasDatabaseName("ix_billing_terms_agreement_dates");
        term.HasIndex(x => new { x.BillingEntityId, x.EffectiveFrom }).HasDatabaseName("ix_billing_terms_entity_dates");
    }

    private static void ConfigureSchedule(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<BillingSchedule> schedule)
    {
        schedule.ToTable("billing_schedules", "billing", table =>
        {
            table.HasCheckConstraint("ck_billing_schedules_frequency", "frequency_code IN ('MONTHLY','QUARTERLY','HALF_YEARLY','ANNUALLY','SPECIFIC_MONTH','ONE_TIME','CUSTOM_MONTHS')");
            table.HasCheckConstraint("ck_billing_schedules_interval", "interval_months IS NULL OR interval_months IN (1,3,6,12)");
            table.HasCheckConstraint("ck_billing_schedules_day", "billing_day IS NULL OR billing_day BETWEEN 1 AND 31");
            table.HasCheckConstraint("ck_billing_schedules_adjustment", "business_day_adjustment IN ('NONE','PREVIOUS','NEXT')");
            table.HasCheckConstraint("ck_billing_schedules_projection", "projection_timing = 'PER_BILLING_EVENT'");
            table.HasCheckConstraint("ck_billing_schedules_shape", "(frequency_code = 'ONE_TIME' AND one_time_date IS NOT NULL AND anchor_date IS NULL AND billing_day IS NULL AND interval_months IS NULL) OR (frequency_code <> 'ONE_TIME' AND one_time_date IS NULL AND anchor_date IS NOT NULL AND billing_day IS NOT NULL AND interval_months IS NOT NULL)");
        });
        schedule.HasKey(x => x.BillingTermId).HasName("pk_billing_schedules");
        schedule.Property(x => x.BillingTermId).HasColumnName("billing_term_id"); schedule.Property(x => x.FrequencyCode).HasColumnName("frequency_code").HasMaxLength(30);
        schedule.Property(x => x.IntervalMonths).HasColumnName("interval_months"); schedule.Property(x => x.AnchorDate).HasColumnName("anchor_date"); schedule.Property(x => x.BillingDay).HasColumnName("billing_day");
        schedule.Property(x => x.BusinessDayAdjustment).HasColumnName("business_day_adjustment").HasMaxLength(20); schedule.Property(x => x.ProjectionTiming).HasColumnName("projection_timing").HasMaxLength(30);
        schedule.Property(x => x.OneTimeDate).HasColumnName("one_time_date");
        schedule.HasOne(x => x.BillingTerm).WithOne(x => x.Schedule).HasForeignKey<BillingSchedule>(x => x.BillingTermId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_billing_schedules_term");
    }

    private static void ConfigureScheduleMonth(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<BillingScheduleMonth> month)
    {
        month.ToTable("billing_schedule_months", "billing", table => table.HasCheckConstraint("ck_billing_schedule_months_month", "month BETWEEN 1 AND 12"));
        month.HasKey(x => new { x.BillingTermId, x.Month }).HasName("pk_billing_schedule_months");
        month.Property(x => x.BillingTermId).HasColumnName("billing_term_id"); month.Property(x => x.Month).HasColumnName("month");
        month.HasOne(x => x.BillingSchedule).WithMany(x => x.Months).HasForeignKey(x => x.BillingTermId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_billing_schedule_months_schedule");
    }

    private static void ConfigureImportProposal(Microsoft.EntityFrameworkCore.Metadata.Builders.EntityTypeBuilder<BillingImportProposal> proposal)
    {
        proposal.ToTable("billing_import_proposals", "import", table => table.HasCheckConstraint("ck_billing_import_proposals_outcome", "outcome IN ('READY','EXCEPTION','IMPORTED','SKIPPED')"));
        proposal.HasKey(x => x.Id).HasName("pk_billing_import_proposals"); proposal.Property(x => x.Id).HasColumnName("id").UseIdentityByDefaultColumn();
        proposal.Property(x => x.ImportRunId).HasColumnName("import_run_id"); proposal.Property(x => x.SourceRowNumber).HasColumnName("source_row_number");
        proposal.Property(x => x.SourceClientCode).HasColumnName("source_client_code").HasMaxLength(100); proposal.Property(x => x.SourceService).HasColumnName("source_service").HasMaxLength(150);
        proposal.Property(x => x.SourceBillingEntity).HasColumnName("source_billing_entity").HasMaxLength(200); proposal.Property(x => x.SourceAmount).HasColumnName("source_amount").HasPrecision(19, 2);
        proposal.Property(x => x.SourceFrequency).HasColumnName("source_frequency").HasMaxLength(100); proposal.Property(x => x.ClientServiceId).HasColumnName("client_service_id");
        proposal.Property(x => x.BillingEntityId).HasColumnName("billing_entity_id"); proposal.Property(x => x.Outcome).HasColumnName("outcome").HasMaxLength(20);
        proposal.Property(x => x.IssueCode).HasColumnName("issue_code").HasMaxLength(100); proposal.Property(x => x.DataJson).HasColumnName("data_json").HasColumnType("jsonb");
        proposal.HasOne(x => x.ImportRun).WithMany().HasForeignKey(x => x.ImportRunId).OnDelete(DeleteBehavior.Cascade).HasConstraintName("fk_billing_import_proposals_run");
        proposal.HasOne(x => x.ClientService).WithMany().HasForeignKey(x => x.ClientServiceId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_billing_import_proposals_client_service");
        proposal.HasOne(x => x.BillingEntity).WithMany().HasForeignKey(x => x.BillingEntityId).OnDelete(DeleteBehavior.Restrict).HasConstraintName("fk_billing_import_proposals_entity");
        proposal.HasIndex(x => new { x.ImportRunId, x.SourceRowNumber }).HasDatabaseName("ix_billing_import_proposals_run_row");
        proposal.HasIndex(x => new { x.ImportRunId, x.Outcome }).HasDatabaseName("ix_billing_import_proposals_outcome");
    }
}

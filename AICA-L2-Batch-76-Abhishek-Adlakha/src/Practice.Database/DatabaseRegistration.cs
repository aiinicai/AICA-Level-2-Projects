using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.Configuration;
using Microsoft.Extensions.DependencyInjection;
using Practice.BuildingBlocks.Auditing;

namespace Practice.Database;

public static class DatabaseRegistration
{
    public static IServiceCollection AddPracticeDatabase(
        this IServiceCollection services,
        IConfiguration configuration,
        bool addReadinessCheck = true)
    {
        var connectionString = configuration.GetConnectionString("PracticeDatabase")
            ?? throw new InvalidOperationException("ConnectionStrings:PracticeDatabase is required.");

        services.AddDbContext<AppDbContext>(options => options.UseNpgsql(
            connectionString,
            npgsql => npgsql.MigrationsHistoryTable("ef_migrations_history", "system")));
        services.AddScoped<IAuditWriter, EfAuditWriter>();

        if (addReadinessCheck)
        {
            services.AddHealthChecks().AddDbContextCheck<AppDbContext>("practice_database");
        }

        return services;
    }
}

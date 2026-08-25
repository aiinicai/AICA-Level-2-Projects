using Microsoft.EntityFrameworkCore;
using Microsoft.EntityFrameworkCore.Design;

namespace Practice.Database;

public sealed class DesignTimeAppDbContextFactory : IDesignTimeDbContextFactory<AppDbContext>
{
    public AppDbContext CreateDbContext(string[] args)
    {
        var connectionString = Environment.GetEnvironmentVariable("PRACTICE_MIGRATION_CONNECTION")
            ?? "Host=127.0.0.1;Port=5432;Database=practice_management;Username=practice_migrator;Password=local-migrator-password";
        var options = new DbContextOptionsBuilder<AppDbContext>()
            .UseNpgsql(connectionString, npgsql =>
                npgsql.MigrationsHistoryTable("ef_migrations_history", "system"))
            .Options;
        return new AppDbContext(options);
    }
}

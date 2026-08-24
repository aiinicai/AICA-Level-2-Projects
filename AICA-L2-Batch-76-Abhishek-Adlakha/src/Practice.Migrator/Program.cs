using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Logging;
using Practice.Database;

var builder = Host.CreateApplicationBuilder(args);
builder.Logging.ClearProviders();
builder.Logging.AddJsonConsole(options => options.TimestampFormat = "yyyy-MM-ddTHH:mm:ss.fffZ");
builder.Services.AddPracticeDatabase(builder.Configuration, addReadinessCheck: false);

using var host = builder.Build();
await using var scope = host.Services.CreateAsyncScope();
var database = scope.ServiceProvider.GetRequiredService<AppDbContext>();
var logger = scope.ServiceProvider.GetRequiredService<ILoggerFactory>().CreateLogger("Practice.Migrator");

var pending = (await database.Database.GetPendingMigrationsAsync()).ToArray();
MigrationLog.Applying(logger, pending.Length);
await database.Database.MigrateAsync();
MigrationLog.Current(logger);

internal static partial class MigrationLog
{
    [LoggerMessage(EventId = 2000, Level = LogLevel.Information,
        Message = "Applying {MigrationCount} pending database migration(s)")]
    public static partial void Applying(ILogger logger, int migrationCount);

    [LoggerMessage(EventId = 2001, Level = LogLevel.Information,
        Message = "Database schema is current")]
    public static partial void Current(ILogger logger);
}

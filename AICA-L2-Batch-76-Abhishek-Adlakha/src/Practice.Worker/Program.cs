using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Microsoft.Extensions.Configuration;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Scheduling;
using Practice.Worker;

var builder = Host.CreateApplicationBuilder(args);
var externalConfigurationPath = Environment.GetEnvironmentVariable("PRACTICE_CONFIG_FILE");
if (string.IsNullOrWhiteSpace(externalConfigurationPath) && OperatingSystem.IsWindows())
{
    externalConfigurationPath = Path.Combine(Environment.GetFolderPath(Environment.SpecialFolder.CommonApplicationData), "PracticeManagement", "appsettings.Production.json");
}
if (!string.IsNullOrWhiteSpace(externalConfigurationPath)) builder.Configuration.AddJsonFile(externalConfigurationPath, optional: false, reloadOnChange: true);
builder.Services.AddSingleton<IClock, SystemClock>();
builder.Services.AddPracticeDatabase(builder.Configuration, addReadinessCheck: false);
builder.Services.AddPracticeScheduling();
builder.Services.AddScoped<AuditRetentionService>();
builder.Services.AddSingleton(new WorkerOptions(args.Contains("--once", StringComparer.OrdinalIgnoreCase)));
builder.Services.AddHostedService<Worker>();

await builder.Build().RunAsync();

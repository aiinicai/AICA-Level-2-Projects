using System.Threading.RateLimiting;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.AspNetCore.Http.Metadata;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.DataProtection;
using Microsoft.AspNetCore.Diagnostics.HealthChecks;
using Microsoft.EntityFrameworkCore;
using Practice.Api.Identity;
using Practice.Api.Audit;
using Practice.Api.Import;
using Practice.Api.Clients;
using Practice.Api.Services;
using Practice.Api.Tasks;
using Practice.Api.Scheduling;
using Practice.Api.Billing;
using Practice.Api.Reporting;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Identity;
using Practice.Scheduling;

var builder = WebApplication.CreateBuilder(args);
var externalConfigurationPath = Environment.GetEnvironmentVariable("PRACTICE_CONFIG_FILE");
if (!string.IsNullOrWhiteSpace(externalConfigurationPath))
{
    builder.Configuration.AddJsonFile(externalConfigurationPath, optional: false, reloadOnChange: true);
}

builder.Logging.ClearProviders();
builder.Logging.AddJsonConsole(options => options.TimestampFormat = "yyyy-MM-ddTHH:mm:ss.fffZ");
builder.Services.AddProblemDetails();
builder.Services.AddHealthChecks();
builder.Services.AddSingleton<IClock, SystemClock>();
builder.Services.AddPracticeDatabase(builder.Configuration);
builder.Services.AddPracticeIdentity();
builder.Services.AddPracticeScheduling();
var dataProtectionKeyPath = builder.Configuration["Security:DataProtectionKeyPath"];
if (!string.IsNullOrWhiteSpace(dataProtectionKeyPath))
{
    builder.Services.AddDataProtection()
        .PersistKeysToFileSystem(new DirectoryInfo(dataProtectionKeyPath))
        .SetApplicationName("PracticeManagement");
}
builder.Services.AddScoped<SessionCookieEvents>();
builder.Services.AddAuthentication(IdentityConstants.AuthenticationScheme).AddCookie(
    IdentityConstants.AuthenticationScheme,
    options =>
    {
        options.Cookie.Name = builder.Environment.IsDevelopment() ? "Practice.Session" : "__Host-Practice.Session";
        options.Cookie.HttpOnly = true;
        options.Cookie.IsEssential = true;
        options.Cookie.SameSite = SameSiteMode.Strict;
        options.Cookie.SecurePolicy = builder.Environment.IsDevelopment()
            ? CookieSecurePolicy.SameAsRequest
            : CookieSecurePolicy.Always;
        options.ExpireTimeSpan = IdentityConstants.SessionDuration;
        options.SlidingExpiration = false;
        options.EventsType = typeof(SessionCookieEvents);
    });
builder.Services.AddAuthorization(options =>
{
    options.AddPolicy("password-current", policy => policy.RequireClaim("must_change_password", "false"));
    foreach (var permission in new[]
    {
        PermissionCodes.UsersView, PermissionCodes.UsersManage, PermissionCodes.RolesView,
        PermissionCodes.RolesManage, PermissionCodes.EmployeesView, PermissionCodes.EmployeesManage,
        PermissionCodes.TeamsManage, PermissionCodes.FieldPoliciesManage, PermissionCodes.DiagnosticsView,
        PermissionCodes.AuditView,
        PermissionCodes.ClientsView, PermissionCodes.ClientsCreate, PermissionCodes.ClientsEdit,
        PermissionCodes.ClientsDeactivate, PermissionCodes.ServicesView, PermissionCodes.ServicesCatalogueManage,
        PermissionCodes.ServiceEnrollmentsView, PermissionCodes.ServiceEnrollmentsManage,
        PermissionCodes.TasksView, PermissionCodes.TasksCreate, PermissionCodes.TasksAssign,
        PermissionCodes.TasksChangeStatus, PermissionCodes.TasksReopen, PermissionCodes.TasksComment,
        PermissionCodes.SchedulingView, PermissionCodes.SchedulingManage, PermissionCodes.SchedulingGenerate,
        PermissionCodes.CalendarView, PermissionCodes.HolidaysManage
        , PermissionCodes.BillingView, PermissionCodes.BillingConfigure, PermissionCodes.BillingProject,
        PermissionCodes.ReportsView, PermissionCodes.ReportsExport
    })
    {
        options.AddPolicy(permission, policy => policy.RequireClaim(IdentityConstants.PermissionClaim, permission));
    }
});
builder.Services.AddAntiforgery(options =>
{
    options.HeaderName = "X-CSRF-TOKEN";
    options.Cookie.Name = builder.Environment.IsDevelopment() ? "Practice.Antiforgery" : "__Host-Practice.Antiforgery";
    options.Cookie.HttpOnly = true;
    options.Cookie.SameSite = SameSiteMode.Strict;
    options.Cookie.SecurePolicy = builder.Environment.IsDevelopment()
        ? CookieSecurePolicy.SameAsRequest
        : CookieSecurePolicy.Always;
});
builder.Services.AddRateLimiter(options =>
{
    options.RejectionStatusCode = StatusCodes.Status429TooManyRequests;
    options.AddPolicy("login", context => RateLimitPartition.GetFixedWindowLimiter(
        context.Connection.RemoteIpAddress?.ToString() ?? "unknown",
        _ => new FixedWindowRateLimiterOptions
        {
            PermitLimit = 10, Window = TimeSpan.FromMinutes(1), QueueLimit = 0,
            AutoReplenishment = true
        }));
});

var app = builder.Build();

// Applied here as well as at the reverse proxy, because the Windows production host serves the
// SPA directly from wwwroot and never passes through Nginx. style-src allows inline styles: the
// task and status chips set their colour through a style attribute.
app.Use(async (context, next) =>
{
    var headers = context.Response.Headers;
    headers["Content-Security-Policy"] =
        "default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline'; img-src 'self' data:; " +
        "font-src 'self'; connect-src 'self'; object-src 'none'; base-uri 'self'; form-action 'self'; " +
        "frame-ancestors 'none'";
    headers["X-Content-Type-Options"] = "nosniff";
    headers["X-Frame-Options"] = "DENY";
    headers["Referrer-Policy"] = "no-referrer";
    headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=(), payment=(), usb=()";
    headers["Cross-Origin-Opener-Policy"] = "same-origin";
    headers["Cross-Origin-Resource-Policy"] = "same-origin";
    await next(context);
});

app.UseExceptionHandler();
app.UseDefaultFiles();
app.UseStaticFiles();
app.UseRateLimiter();
app.UseAuthentication();
app.UseAuthorization();
app.UseAntiforgery();

// UseAntiforgery records a failed validation in IAntiforgeryValidationFeature but only form
// binding ever reads it, so JSON mutations carrying RequireAntiforgeryToken metadata were
// reaching their handler with an invalid or absent token. Reject them here instead.
app.Use(async (context, next) =>
{
    if (context.GetEndpoint()?.Metadata.GetMetadata<IAntiforgeryMetadata>() is { RequiresValidation: true }
        && context.Features.Get<IAntiforgeryValidationFeature>() is { IsValid: false })
    {
        await Results.Problem(statusCode: StatusCodes.Status400BadRequest,
            title: "Invalid antiforgery token",
            detail: "The request did not include a valid antiforgery token.").ExecuteAsync(context);
        return;
    }

    await next(context);
});

app.MapGet("/api/v1/system/info", (IClock clock) => Results.Ok(new
{
    application = "CA Firm Practice Management",
    phase = 9,
    environment = app.Environment.EnvironmentName,
    serverTimeUtc = clock.UtcNow,
    apiVersion = "v1"
}));

app.MapGet("/api/v1/system/diagnostics", async (AppDbContext database, CancellationToken cancellationToken) =>
{
    var canConnect = await database.Database.CanConnectAsync(cancellationToken);
    var appliedMigrations = canConnect
        ? (await database.Database.GetAppliedMigrationsAsync(cancellationToken)).ToArray()
        : [];
    var stateCount = canConnect
        ? await database.IndiaStates.CountAsync(cancellationToken)
        : 0;

    return Results.Ok(new
    {
        database = new
        {
            status = canConnect ? "Healthy" : "Unavailable",
            provider = database.Database.ProviderName,
            appliedMigrations,
            indiaStateCount = stateCount
        },
        capabilities = new
        {
            workbookProfiling = true,
            businessCrud = true,
            clientRegistry = true,
            serviceCatalogue = true,
            clientServiceAgreements = true,
            taskLifecycle = true,
            taskAssignments = true,
            recurringTaskGeneration = true,
            businessDayCalendar = true,
            calendarReadModel = true,
            billingConfiguration = true,
            billingProjection = true,
            projectionCsvExport = true,
            projectionXlsxExport = true,
            operationalDashboard = true,
            scopedReports = true,
            authentication = true,
            configurableRoles = true,
            configurableFieldPolicies = true
        }
    });
}).RequireAuthorization(PermissionCodes.DiagnosticsView);

app.MapIdentityEndpoints();
app.MapAuditEndpoints();
app.MapImportMappingEndpoints();
app.MapClientEndpoints();
app.MapServiceEndpoints();
app.MapTaskEndpoints();
app.MapSchedulingEndpoints();
app.MapCalendarEndpoints();
app.MapBillingEndpoints();
app.MapBillingProjectionEndpoints();
app.MapReportingEndpoints();

app.MapHealthChecks("/health/live", new HealthCheckOptions
{
    Predicate = _ => false
});
app.MapHealthChecks("/health/ready");
app.MapFallbackToFile("index.html");

app.Run();

public partial class Program
{
}

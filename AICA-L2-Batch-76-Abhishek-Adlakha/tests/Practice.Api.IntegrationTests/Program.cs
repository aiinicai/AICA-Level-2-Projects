// The API host and this console harness both define a top-level Program, so the host entry
// point that WebApplicationFactory boots is referenced through an alias.
extern alias PracticeApi;

using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Mvc.Testing;
using Microsoft.AspNetCore.Mvc.Testing.Handlers;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Microsoft.Extensions.Hosting;
using Practice.Database;
using Practice.Identity;

// PostgreSQL-backed checks for the real HTTP pipeline. The other suites verify rules in
// isolation and cannot catch EF-to-PostgreSQL translation failures or authorization gaps,
// which is how two report endpoints shipped returning HTTP 500.
var connectionString = Environment.GetEnvironmentVariable("PRACTICE_TEST_DATABASE");
if (string.IsNullOrWhiteSpace(connectionString))
{
    Console.WriteLine("API integration checks skipped: set PRACTICE_TEST_DATABASE to a disposable PostgreSQL database.");
    return 0;
}

Environment.SetEnvironmentVariable("ConnectionStrings__PracticeDatabase", connectionString);
Environment.SetEnvironmentVariable("ASPNETCORE_ENVIRONMENT", "Development");

await using var factory = new Practice.Api.IntegrationTests.ApiFactory();
using (var scope = factory.Services.CreateScope())
{
    // The API never migrates itself, so the harness prepares the disposable schema instead.
    var database = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    await database.Database.MigrateAsync();
    if (await database.Users.AnyAsync())
    {
        Console.Error.WriteLine("PRACTICE_TEST_DATABASE must point at a disposable database with no existing users.");
        return 1;
    }
}

var failures = new List<string>();
const string mobile = "9000000001";
var password = "Integration-" + Guid.NewGuid().ToString("N");

using (var scope = factory.Services.CreateScope())
{
    var bootstrap = scope.ServiceProvider.GetRequiredService<BootstrapAdministratorService>();
    var errors = await bootstrap.BootstrapAsync(
        new BootstrapAdministratorRequest("Integration Administrator", "INT-ADMIN", mobile, password),
        CancellationToken.None);
    if (errors.Count > 0)
    {
        Console.Error.WriteLine($"Bootstrap failed: {string.Join("; ", errors)}");
        return 1;
    }
}

// Anonymous callers must never reach privileged data. Direct-URL denial is the check that
// matters here, because the browser navigation is not an authorization boundary.
using (var anonymous = factory.CreateDefaultClient(new CookieContainerHandler()))
{
    foreach (var route in new[]
    {
        "/api/v1/system/diagnostics", "/api/v1/admin/audit", "/api/v1/admin/audit/filters",
        "/api/v1/admin/roles", "/api/v1/admin/employees", "/api/v1/admin/operations",
        "/api/v1/admin/import/people", "/api/v1/dashboard",
        "/api/v1/reports/clients?page=1&pageSize=25", "/api/v1/reports/tasks?page=1&pageSize=25",
        "/api/v1/clients", "/api/v1/tasks"
    })
    {
        var response = await anonymous.GetAsync(route);
        if (response.StatusCode != HttpStatusCode.Unauthorized)
        {
            failures.Add($"Anonymous request to {route} returned {(int)response.StatusCode}, expected 401.");
        }
    }

    var info = await anonymous.GetAsync("/api/v1/system/info");
    if (!info.IsSuccessStatusCode)
    {
        failures.Add("The intentionally public system info endpoint must remain reachable.");
    }
}

using var client = factory.CreateDefaultClient(new CookieContainerHandler());
var csrf = await CsrfTokenAsync(client);
var login = new HttpRequestMessage(HttpMethod.Post, "/api/v1/auth/login")
{
    Content = JsonContent.Create(new { mobileNumber = mobile, password })
};
login.Headers.Add("X-CSRF-TOKEN", csrf);
var loginResponse = await client.SendAsync(login);
if (!loginResponse.IsSuccessStatusCode)
{
    Console.Error.WriteLine($"Integration login failed with {(int)loginResponse.StatusCode}; cannot continue.");
    return 1;
}

// Every authorised read must execute against PostgreSQL. A translation failure surfaces as 500
// and is invisible to the in-process rule suites.
foreach (var route in new[]
{
    "/api/v1/system/diagnostics", "/api/v1/admin/audit", "/api/v1/admin/audit/filters",
    "/api/v1/admin/roles", "/api/v1/admin/permissions", "/api/v1/admin/employees",
    "/api/v1/admin/field-policies", "/api/v1/admin/teams", "/api/v1/admin/operations",
    "/api/v1/admin/import/people", "/api/v1/dashboard",
    "/api/v1/reports/catalog", "/api/v1/reports/masters",
    "/api/v1/reports/clients?page=1&pageSize=25", "/api/v1/reports/tasks?page=1&pageSize=25",
    "/api/v1/clients", "/api/v1/tasks", "/api/v1/services", "/api/v1/client-services",
    "/api/v1/billing/entities", "/api/v1/calendar", "/api/v1/scheduling/rules"
})
{
    var response = await client.GetAsync(route);
    if (!response.IsSuccessStatusCode)
    {
        failures.Add($"Authorised request to {route} returned {(int)response.StatusCode}, expected success.");
    }
}

// A mutation without the antiforgery header must be rejected.
var withoutToken = await client.PostAsJsonAsync("/api/v1/admin/teams", new { code = "CSRF", name = "No token" });
if (withoutToken.StatusCode is not (HttpStatusCode.BadRequest or HttpStatusCode.Forbidden))
{
    failures.Add($"A mutation without an antiforgery token returned {(int)withoutToken.StatusCode}, expected rejection.");
}

// Security headers must be present on the responses the browser actually renders, not only at
// the reverse proxy, because the Windows production host serves the SPA from wwwroot.
var headerResponse = await client.GetAsync("/api/v1/system/info");
foreach (var header in new[]
{
    "Content-Security-Policy", "X-Content-Type-Options", "X-Frame-Options",
    "Referrer-Policy", "Permissions-Policy"
})
{
    if (!headerResponse.Headers.Contains(header) && !headerResponse.Content.Headers.Contains(header))
    {
        failures.Add($"Response is missing the {header} security header.");
    }
}
if (headerResponse.Headers.TryGetValues("Content-Security-Policy", out var policies)
    && !string.Join(" ", policies).Contains("frame-ancestors 'none'", StringComparison.Ordinal))
{
    failures.Add("The content security policy must deny framing.");
}

// An export removes confidential data from the system, so it must leave an audit record.
var exportToken = await CsrfTokenAsync(client);
var exportRequest = new HttpRequestMessage(HttpMethod.Post, "/api/v1/reports/clients:export")
{
    Content = JsonContent.Create(new { format = "CSV", filters = new { } })
};
exportRequest.Headers.Add("X-CSRF-TOKEN", exportToken);
var exportResponse = await client.SendAsync(exportRequest);
if (!exportResponse.IsSuccessStatusCode)
{
    failures.Add($"Client export returned {(int)exportResponse.StatusCode}, expected success.");
}

// Failed logins and session revocation must reach the audit trail; brute-force detection
// depends on them, and neither was recorded before Phase 10.
using (var attacker = factory.CreateDefaultClient(new CookieContainerHandler()))
{
    var attackerCsrf = await CsrfTokenAsync(attacker);
    var badLogin = new HttpRequestMessage(HttpMethod.Post, "/api/v1/auth/login")
    {
        Content = JsonContent.Create(new { mobileNumber = mobile, password = "definitely-not-the-password" })
    };
    badLogin.Headers.Add("X-CSRF-TOKEN", attackerCsrf);
    var badResponse = await attacker.SendAsync(badLogin);
    if (badResponse.StatusCode != HttpStatusCode.Unauthorized)
    {
        failures.Add($"A wrong password returned {(int)badResponse.StatusCode}, expected 401.");
    }
}

var logoutCsrf = await CsrfTokenAsync(client);
var logout = new HttpRequestMessage(HttpMethod.Post, "/api/v1/auth/logout");
logout.Headers.Add("X-CSRF-TOKEN", logoutCsrf);
var logoutResponse = await client.SendAsync(logout);
if (!logoutResponse.IsSuccessStatusCode)
{
    failures.Add($"Logout returned {(int)logoutResponse.StatusCode}, expected success.");
}

using (var scope = factory.Services.CreateScope())
{
    var database = scope.ServiceProvider.GetRequiredService<AppDbContext>();
    foreach (var action in new[] { "identity.login", "identity.login_failed", "identity.session_revoked", "reports.exported" })
    {
        if (!await database.AuditEvents.AnyAsync(item => item.Action == action))
        {
            failures.Add($"No audit event was recorded for {action}.");
        }
    }

    var failure = await database.AuditEvents.SingleOrDefaultAsync(item => item.Action == "identity.login_failed");
    if (failure is not null && failure.DataJson.Contains("definitely-not-the-password", StringComparison.OrdinalIgnoreCase))
    {
        failures.Add("The submitted password must never be written to the audit trail.");
    }

    // The session the browser used must be revoked server-side, not merely cleared client-side.
    if (!await database.UserSessions.AnyAsync(item => item.RevokedAtUtc != null))
    {
        failures.Add("Logout must revoke the server-side session record.");
    }
}

await Practice.Api.IntegrationTests.ScopeChecks.RunAsync(factory, failures);
await Practice.Api.IntegrationTests.BillingTermChecks.RunAsync(factory, mobile, password, failures);

if (failures.Count > 0)
{
    Console.Error.WriteLine("API integration checks failed:");
    failures.ForEach(failure => Console.Error.WriteLine($"- {failure}"));
    return 1;
}

Console.WriteLine("API integration checks passed against PostgreSQL.");
return 0;

static async Task<string> CsrfTokenAsync(HttpClient client)
{
    using var document = JsonDocument.Parse(await client.GetStringAsync("/api/v1/auth/csrf"));
    return document.RootElement.GetProperty("token").GetString()!;
}

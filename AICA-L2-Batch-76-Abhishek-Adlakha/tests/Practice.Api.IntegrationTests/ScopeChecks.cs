using System.Globalization;
using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.AspNetCore.Identity;
using Microsoft.AspNetCore.Mvc.Testing.Handlers;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;

namespace Practice.Api.IntegrationTests;

// OWN/TEAM/ALL record scope is the security boundary of this system and it is computed
// independently inside each endpoint module. Nothing else exercises it, so these checks build a
// two-team fixture and assert what each ceiling may read — through the list view AND through the
// direct-ID route, because hiding a row from a list is not the same as refusing it by identifier.
internal static class ScopeChecks
{
    private const string Password = "Scope-Check-Password-9x2";

    // The task report caps its window at five years, so the fixture window stays near today.
    private static readonly DateOnly WindowFrom = DateOnly.FromDateTime(DateTime.UtcNow).AddDays(-30);
    private static readonly DateOnly WindowTo = DateOnly.FromDateTime(DateTime.UtcNow).AddDays(30);
    private static string Window => FormattableString.Invariant($"from={WindowFrom:yyyy-MM-dd}&to={WindowTo:yyyy-MM-dd}");

    public static async Task RunAsync(ApiFactory factory, List<string> failures)
    {
        var fixture = await SeedAsync(factory);

        var admin = await SignInAsync(factory, fixture.AdminMobile, failures);
        var manager = await SignInAsync(factory, fixture.ManagerMobile, failures);
        var member = await SignInAsync(factory, fixture.MemberMobile, failures);
        if (admin is null || manager is null || member is null)
        {
            return;
        }

        using (admin)
        using (manager)
        using (member)
        {
            // ALL sees everything.
            await ExpectTasksAsync(admin, "ALL", [fixture.AlphaTaskNumber, fixture.BetaTaskNumber], failures);
            await ExpectClientsAsync(admin, "ALL", [fixture.AlphaClientCode, fixture.BetaClientCode, fixture.GammaClientCode], failures);

            // OWN sees only work currently assigned to that employee.
            await ExpectTasksAsync(member, "OWN", [fixture.AlphaTaskNumber], failures);

            // TEAM reaches the managed team's members, and stops there.
            await ExpectTasksAsync(manager, "TEAM", [fixture.AlphaTaskNumber], failures);
            // The register and the report must return the same clients for the same permission and
            // ceiling. The gamma client belongs to a team the manager neither joins nor manages —
            // only a direct report sits there — so neither surface may return it. The register used
            // to, which is why both are asserted together here rather than only one of them.
            await ExpectClientsAsync(manager, "TEAM register", [fixture.AlphaClientCode], failures);
            await ExpectReportClientsAsync(manager, "TEAM report", [fixture.AlphaClientCode], failures);

            // Direct-ID denial. An out-of-scope record must not be readable by identifier, and the
            // in-scope one must still be readable, so a 404 cannot pass by denying everything.
            await ExpectStatusAsync(member, $"/api/v1/tasks/{fixture.BetaTaskId}", HttpStatusCode.NotFound,
                "OWN scope must not read another employee's task by id", failures);
            await ExpectStatusAsync(member, $"/api/v1/tasks/{fixture.AlphaTaskId}", HttpStatusCode.OK,
                "OWN scope must still read its own task by id", failures);
            await ExpectStatusAsync(manager, $"/api/v1/tasks/{fixture.BetaTaskId}", HttpStatusCode.NotFound,
                "TEAM scope must not read another team's task by id", failures);
            await ExpectStatusAsync(manager, $"/api/v1/tasks/{fixture.AlphaTaskId}", HttpStatusCode.OK,
                "TEAM scope must read its own team's task by id", failures);
            await ExpectStatusAsync(manager, $"/api/v1/clients/{fixture.BetaClientId}", HttpStatusCode.NotFound,
                "TEAM scope must not read another team's client by id", failures);
            await ExpectStatusAsync(manager, $"/api/v1/clients/{fixture.AlphaClientId}", HttpStatusCode.OK,
                "TEAM scope must read its own team's client by id", failures);
            await ExpectStatusAsync(manager, $"/api/v1/clients/{fixture.GammaClientId}", HttpStatusCode.NotFound,
                "TEAM scope must not reach a direct report's unrelated team by id", failures);

            // Reports must narrow with the same ceiling as the registers they mirror.
            await ExpectReportTaskCountAsync(manager, 1, "TEAM task report", failures);
            await ExpectReportTaskCountAsync(member, 1, "OWN task report", failures);
            await ExpectReportTaskCountAsync(admin, 2, "ALL task report", failures);

            // Agreements, billing and scheduling all scope through the same responsible team on the
            // client-service agreement, so each must answer with the same set for the same ceiling.
            await ExpectIdsAsync(admin, "/api/v1/client-services", "ALL agreements",
                [fixture.AlphaAgreementId, fixture.BetaAgreementId, fixture.GammaAgreementId], failures);
            await ExpectIdsAsync(manager, "/api/v1/client-services", "TEAM agreements",
                [fixture.AlphaAgreementId], failures);
            await ExpectStatusAsync(manager, $"/api/v1/client-services/{fixture.BetaAgreementId}", HttpStatusCode.NotFound,
                "TEAM scope must not read another team's agreement by id", failures);
            await ExpectStatusAsync(manager, $"/api/v1/client-services/{fixture.AlphaAgreementId}", HttpStatusCode.OK,
                "TEAM scope must read its own team's agreement by id", failures);

            await ExpectTermAgreementsAsync(admin, "ALL billing terms",
                [fixture.AlphaAgreementId, fixture.BetaAgreementId], failures);
            await ExpectTermAgreementsAsync(manager, "TEAM billing terms", [fixture.AlphaAgreementId], failures);

            await ExpectIdsAsync(admin, "/api/v1/scheduling/rules", "ALL recurrence rules",
                [fixture.AlphaRuleId, fixture.BetaRuleId], failures);
            await ExpectIdsAsync(manager, "/api/v1/scheduling/rules", "TEAM recurrence rules",
                [fixture.AlphaRuleId], failures);

            // The calendar scopes by assignment, not by responsible team, and it deliberately
            // defaults to the signed-in employee's own work: a TEAM ceiling only widens when the
            // caller asks for it with view=team. An ALL ceiling defaults to everything.
            await ExpectCalendarAsync(admin, null, "ALL calendar", 2, failures);
            await ExpectCalendarAsync(member, null, "OWN calendar", 1, failures);
            await ExpectCalendarAsync(manager, null, "TEAM calendar default", 0, failures);
            await ExpectCalendarAsync(manager, "team", "TEAM calendar widened", 1, failures);
            // A ceiling must not be exceeded by asking for more than it grants.
            await ExpectCalendarAsync(member, "all", "OWN calendar cannot request all", 1, failures);
            await ExpectCalendarAsync(manager, "all", "TEAM calendar cannot request all", 0, failures);

            // An export must never widen what the same session can already see on screen.
            await ExpectExportRowsAsync(manager, 1, "TEAM task export", failures);
            await ExpectExportRowsAsync(admin, 2, "ALL task export", failures);
        }
    }

    private static async Task ExpectTasksAsync(HttpClient client, string label, long[] expected, List<string> failures)
    {
        using var document = JsonDocument.Parse(await client.GetStringAsync("/api/v1/tasks"));
        var actual = document.RootElement.GetProperty("items").EnumerateArray()
            .Select(item => item.GetProperty("taskNumber").GetInt64()).OrderBy(value => value).ToArray();
        if (!actual.SequenceEqual(expected.OrderBy(value => value)))
        {
            failures.Add($"{label} task list returned [{string.Join(",", actual)}], expected [{string.Join(",", expected)}].");
        }
    }

    private static async Task ExpectClientsAsync(HttpClient client, string label, string[] expected, List<string> failures)
    {
        using var document = JsonDocument.Parse(await client.GetStringAsync("/api/v1/clients"));
        var actual = document.RootElement.GetProperty("items").EnumerateArray()
            .Select(item => item.GetProperty("clientCode").GetString()!).OrderBy(value => value, StringComparer.Ordinal).ToArray();
        if (!actual.SequenceEqual(expected.OrderBy(value => value, StringComparer.Ordinal)))
        {
            failures.Add($"{label} client list returned [{string.Join(",", actual)}], expected [{string.Join(",", expected)}].");
        }
    }

    private static async Task ExpectIdsAsync(
        HttpClient client, string route, string label, Guid[] expected, List<string> failures)
    {
        var payload = await client.GetStringAsync(route);
        using var document = JsonDocument.Parse(payload);
        var root = document.RootElement.ValueKind == JsonValueKind.Array
            ? document.RootElement
            : document.RootElement.GetProperty("items");
        var actual = root.EnumerateArray().Select(item => item.GetProperty("id").GetGuid()).OrderBy(value => value).ToArray();
        if (!actual.SequenceEqual(expected.OrderBy(value => value)))
        {
            failures.Add($"{label} returned {actual.Length} rows [{string.Join(",", actual)}], expected {expected.Length} [{string.Join(",", expected)}].");
        }
    }

    private static async Task ExpectTermAgreementsAsync(
        HttpClient client, string label, Guid[] expected, List<string> failures)
    {
        using var document = JsonDocument.Parse(await client.GetStringAsync("/api/v1/billing/terms"));
        var root = document.RootElement.ValueKind == JsonValueKind.Array
            ? document.RootElement
            : document.RootElement.GetProperty("items");
        var actual = root.EnumerateArray().Select(item => item.GetProperty("clientServiceId").GetGuid())
            .Distinct().OrderBy(value => value).ToArray();
        if (!actual.SequenceEqual(expected.OrderBy(value => value)))
        {
            failures.Add($"{label} covered [{string.Join(",", actual)}], expected [{string.Join(",", expected)}].");
        }
    }

    private static async Task ExpectCalendarAsync(
        HttpClient client, string? view, string label, int expected, List<string> failures)
    {
        var route = FormattableString.Invariant($"/api/v1/calendar?from={WindowFrom:yyyy-MM-dd}&to={WindowTo:yyyy-MM-dd}")
            + (view is null ? string.Empty : $"&view={view}");
        using var document = JsonDocument.Parse(await client.GetStringAsync(route));
        var actual = document.RootElement.GetProperty("tasks").GetArrayLength();
        if (actual != expected)
        {
            failures.Add($"{label} returned {actual} tasks, expected {expected}.");
        }
    }

    private static async Task ExpectReportClientsAsync(HttpClient client, string label, string[] expected, List<string> failures)
    {
        using var document = JsonDocument.Parse(await client.GetStringAsync("/api/v1/reports/clients"));
        var actual = document.RootElement.GetProperty("items").EnumerateArray()
            .Select(item => item.GetProperty("clientCode").GetString()!).OrderBy(value => value, StringComparer.Ordinal).ToArray();
        if (!actual.SequenceEqual(expected.OrderBy(value => value, StringComparer.Ordinal)))
        {
            failures.Add($"{label} returned [{string.Join(",", actual)}], expected [{string.Join(",", expected)}].");
        }
    }

    private static async Task ExpectReportTaskCountAsync(HttpClient client, int expected, string label, List<string> failures)
    {
        using var document = JsonDocument.Parse(
            await client.GetStringAsync($"/api/v1/reports/tasks?{Window}"));
        var actual = document.RootElement.GetProperty("totalCount").GetInt32();
        if (actual != expected)
        {
            failures.Add($"{label} returned {actual} rows, expected {expected}.");
        }
    }

    private static async Task ExpectExportRowsAsync(HttpClient client, int expected, string label, List<string> failures)
    {
        var token = await CsrfAsync(client);
        var request = new HttpRequestMessage(HttpMethod.Post, "/api/v1/reports/tasks:export")
        {
            Content = JsonContent.Create(new
            {
                format = "CSV",
                filters = new { from = WindowFrom.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), to = WindowTo.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture) }
            })
        };
        request.Headers.Add("X-CSRF-TOKEN", token);
        var response = await client.SendAsync(request);
        if (!response.IsSuccessStatusCode)
        {
            failures.Add($"{label} returned {(int)response.StatusCode}, expected success.");
            return;
        }
        var csv = await response.Content.ReadAsStringAsync();
        var rows = csv.Split('\n', StringSplitOptions.RemoveEmptyEntries).Length - 1;
        if (rows != expected)
        {
            failures.Add($"{label} contained {rows} data rows, expected {expected}.");
        }
    }

    private static async Task ExpectStatusAsync(
        HttpClient client, string route, HttpStatusCode expected, string reason, List<string> failures)
    {
        var response = await client.GetAsync(route);
        if (response.StatusCode != expected)
        {
            failures.Add($"{reason}: {route} returned {(int)response.StatusCode}, expected {(int)expected}.");
        }
    }

    private static async Task<HttpClient?> SignInAsync(ApiFactory factory, string mobile, List<string> failures)
    {
        var client = factory.CreateDefaultClient(new CookieContainerHandler());
        var request = new HttpRequestMessage(HttpMethod.Post, "/api/v1/auth/login")
        {
            Content = JsonContent.Create(new { mobileNumber = mobile, password = Password })
        };
        request.Headers.Add("X-CSRF-TOKEN", await CsrfAsync(client));
        var response = await client.SendAsync(request);
        if (!response.IsSuccessStatusCode)
        {
            failures.Add($"Scope fixture sign-in for {mobile} returned {(int)response.StatusCode}.");
            client.Dispose();
            return null;
        }
        return client;
    }

    private static async Task<string> CsrfAsync(HttpClient client)
    {
        using var document = JsonDocument.Parse(await client.GetStringAsync("/api/v1/auth/csrf"));
        return document.RootElement.GetProperty("token").GetString()!;
    }

    private static async Task<ScopeFixture> SeedAsync(ApiFactory factory)
    {
        using var scope = factory.Services.CreateScope();
        var database = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var hasher = scope.ServiceProvider.GetRequiredService<IPasswordHasher<LoginUser>>();
        var now = DateTimeOffset.UtcNow;
        var today = DateOnly.FromDateTime(now.UtcDateTime);

        var serviceId = await database.Services.Select(item => item.Id).FirstAsync();
        var statusId = await database.TaskStatuses.Where(item => item.Code == "NOT_STARTED").Select(item => item.Id).SingleAsync();

        var alphaManager = Employee("SCOPE-MGR-A", "Alpha Manager", "9100000001", now);
        var alphaMember = Employee("SCOPE-EMP-A", "Alpha Member", "9100000002", now);
        var betaMember = Employee("SCOPE-EMP-B", "Beta Member", "9100000003", now);
        var directReport = Employee("SCOPE-EMP-G", "Gamma Direct Report", "9100000005", now);
        var administrator = Employee("SCOPE-ADMIN", "Scope Administrator", "9100000004", now);
        directReport.ManagerEmployeeId = alphaManager.Id;
        database.Employees.AddRange(alphaManager, alphaMember, betaMember, administrator, directReport);

        var alphaTeam = new Team { Id = Guid.NewGuid(), Code = "SCOPE-ALPHA", Name = "Scope Alpha", ManagerEmployeeId = alphaManager.Id, IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now };
        var betaTeam = new Team { Id = Guid.NewGuid(), Code = "SCOPE-BETA", Name = "Scope Beta", IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now };
        var gammaTeam = new Team { Id = Guid.NewGuid(), Code = "SCOPE-GAMMA", Name = "Scope Gamma", IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now };
        database.Teams.AddRange(alphaTeam, betaTeam, gammaTeam);
        database.TeamMemberships.AddRange(
            new TeamMembership { TeamId = alphaTeam.Id, EmployeeId = alphaMember.Id, ValidFrom = today.AddYears(-1) },
            new TeamMembership { TeamId = betaTeam.Id, EmployeeId = betaMember.Id, ValidFrom = today.AddYears(-1) },
            new TeamMembership { TeamId = gammaTeam.Id, EmployeeId = directReport.Id, ValidFrom = today.AddYears(-1) });

        // Scope ceilings are per role, so each ceiling under test needs its own role.
        var readPermissions = new[]
        {
            PermissionCodes.TasksView, PermissionCodes.ClientsView, PermissionCodes.ReportsView,
            PermissionCodes.ReportsExport, PermissionCodes.ServicesView, PermissionCodes.ServiceEnrollmentsView,
            PermissionCodes.BillingView, PermissionCodes.SchedulingView, PermissionCodes.CalendarView
        };
        var permissions = await database.Permissions.Where(item => readPermissions.Contains(item.Code)).ToArrayAsync();
        var allRole = Role("SCOPE_ALL", "Scope All", now);
        var teamRole = Role("SCOPE_TEAM", "Scope Team", now);
        var ownRole = Role("SCOPE_OWN", "Scope Own", now);
        database.Roles.AddRange(allRole, teamRole, ownRole);
        foreach (var (role, ceiling) in new[] { (allRole, "ALL"), (teamRole, "TEAM"), (ownRole, "OWN") })
        {
            database.RolePermissions.AddRange(permissions.Select(permission => new RolePermissionGrant
            {
                RoleId = role.Id, PermissionId = permission.Id, ScopeCeiling = ceiling
            }));
        }

        var adminUser = User(administrator, "9100000004", hasher, now);
        var managerUser = User(alphaManager, "9100000001", hasher, now);
        var memberUser = User(alphaMember, "9100000002", hasher, now);
        database.Users.AddRange(adminUser, managerUser, memberUser);
        database.UserRoles.AddRange(
            new UserRole { UserId = adminUser.Id, RoleId = allRole.Id, AssignedAtUtc = now },
            new UserRole { UserId = managerUser.Id, RoleId = teamRole.Id, AssignedAtUtc = now },
            new UserRole { UserId = memberUser.Id, RoleId = ownRole.Id, AssignedAtUtc = now });

        var alphaClient = Client("SCOPE-CLI-A", "Scope Alpha Client", now);
        var betaClient = Client("SCOPE-CLI-B", "Scope Beta Client", now);
        var gammaClient = Client("SCOPE-CLI-G", "Scope Gamma Client", now);
        database.Clients.AddRange(alphaClient, betaClient, gammaClient);

        var alphaAgreement = Agreement(alphaClient.Id, serviceId, alphaTeam.Id, today, now);
        var betaAgreement = Agreement(betaClient.Id, serviceId, betaTeam.Id, today, now);
        var gammaAgreement = Agreement(gammaClient.Id, serviceId, gammaTeam.Id, today, now);
        database.ClientServices.AddRange(alphaAgreement, betaAgreement, gammaAgreement);

        var alphaTask = Task(alphaClient.Id, serviceId, alphaAgreement.Id, statusId, "Scope alpha task", today, now);
        var betaTask = Task(betaClient.Id, serviceId, betaAgreement.Id, statusId, "Scope beta task", today, now);
        database.Tasks.AddRange(alphaTask, betaTask);
        database.TaskAssignments.AddRange(
            new TaskAssignment { Id = Guid.NewGuid(), TaskId = alphaTask.Id, EmployeeId = alphaMember.Id, AssignmentRole = "PRIMARY", AssignedAtUtc = now },
            new TaskAssignment { Id = Guid.NewGuid(), TaskId = betaTask.Id, EmployeeId = betaMember.Id, AssignmentRole = "PRIMARY", AssignedAtUtc = now });

        // Billing terms and recurrence rules both hang off the agreement, so scoping them exercises
        // the same responsible-team rule through two more modules.
        var billingEntity = new BillingEntity
        {
            Id = Guid.NewGuid(), Code = "SCOPE-ENT", LegalName = "Scope Billing Entity",
            CurrencyCode = "INR", EffectiveFrom = today.AddYears(-1), IsActive = true,
            CreatedAtUtc = now, UpdatedAtUtc = now
        };
        database.BillingEntities.Add(billingEntity);
        database.BillingTerms.AddRange(
            Term(alphaAgreement.Id, billingEntity.Id, adminUser.Id, today, now),
            Term(betaAgreement.Id, billingEntity.Id, adminUser.Id, today, now));

        var calendarId = await database.HolidayCalendars.Select(item => item.Id).FirstAsync();
        var alphaRule = Rule(alphaAgreement.Id, calendarId, adminUser.Id, today, now);
        var betaRule = Rule(betaAgreement.Id, calendarId, adminUser.Id, today, now);
        database.RecurrenceRules.AddRange(alphaRule, betaRule);

        await database.SaveChangesAsync();

        return new ScopeFixture(
            "9100000004", "9100000001", "9100000002",
            alphaTask.Id, betaTask.Id, alphaTask.TaskNumber, betaTask.TaskNumber,
            alphaClient.Id, betaClient.Id, gammaClient.Id, alphaClient.ClientCode, betaClient.ClientCode, gammaClient.ClientCode,
            alphaAgreement.Id, betaAgreement.Id, gammaAgreement.Id, alphaRule.Id, betaRule.Id);
    }

    private static Employee Employee(string code, string name, string mobile, DateTimeOffset now) => new()
    {
        Id = Guid.NewGuid(), EmployeeCode = code, NormalizedEmployeeCode = code,
        DisplayName = name, MobileNumber = mobile, IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now
    };

    private static Role Role(string code, string name, DateTimeOffset now) => new()
    {
        Id = Guid.NewGuid(), Code = code, Name = name, Description = "Scope integration fixture role.",
        IsSystem = false, IsProtected = false, IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now
    };

    private static LoginUser User(Employee employee, string mobile, IPasswordHasher<LoginUser> hasher, DateTimeOffset now)
    {
        var user = new LoginUser
        {
            Id = Guid.NewGuid(), MobileUsername = mobile, PasswordHash = string.Empty,
            SecurityStamp = Guid.NewGuid().ToString("N"), MustChangePassword = false,
            IsActive = true, CreatedAtUtc = now, UpdatedAtUtc = now
        };
        user.PasswordHash = hasher.HashPassword(user, Password);
        employee.UserId = user.Id;
        return user;
    }

    private static Client Client(string code, string name, DateTimeOffset now) => new()
    {
        Id = Guid.NewGuid(), ClientCode = code, NormalizedClientCode = code,
        DisplayName = name, NormalizedDisplayName = name.ToUpperInvariant(),
        Status = "ACTIVE", CreatedAtUtc = now, UpdatedAtUtc = now
    };

    private static ClientService Agreement(Guid clientId, Guid serviceId, Guid teamId, DateOnly today, DateTimeOffset now) => new()
    {
        Id = Guid.NewGuid(), ClientId = clientId, ServiceId = serviceId, EffectiveFrom = today.AddMonths(-6),
        IsActive = true, DefaultPriority = "NORMAL", ResponsibleTeamId = teamId, CreatedAtUtc = now, UpdatedAtUtc = now
    };

    private static PracticeTask Task(
        Guid clientId, Guid serviceId, Guid agreementId, Guid statusId, string title, DateOnly today, DateTimeOffset now) => new()
    {
        Id = Guid.NewGuid(), ClientId = clientId, ServiceId = serviceId, ClientServiceId = agreementId,
        Title = title, DueDate = today, StatusId = statusId, Priority = "NORMAL", BillableSnapshot = true,
        CreatedSource = "MANUAL", CreatedAtUtc = now, UpdatedAtUtc = now
    };

    private static BillingTerm Term(Guid agreementId, Guid entityId, Guid actorId, DateOnly today, DateTimeOffset now) => new()
    {
        Id = Guid.NewGuid(), ClientServiceId = agreementId, BillingEntityId = entityId, IsBillable = true,
        PricingModel = "FIXED", Amount = 5000m, CurrencyCode = "INR", EffectiveFrom = today.AddMonths(-3),
        Version = 1, CreatedAtUtc = now, CreatedByUserId = actorId
    };

    private static RecurrenceRule Rule(Guid agreementId, Guid calendarId, Guid actorId, DateOnly today, DateTimeOffset now) => new()
    {
        Id = Guid.NewGuid(), ClientServiceId = agreementId, HolidayCalendarId = calendarId,
        FrequencyCode = "MONTHLY", IntervalCount = 1, AnchorDate = today.AddMonths(-3),
        DueRuleCode = "FIXED_DAY_OF_OFFSET_MONTH", DueDay = 10, DueMonthOffset = 1,
        BusinessDayAdjustment = "NONE", GenerateLeadDays = 21, TimeZoneId = "Asia/Kolkata",
        EffectiveFrom = today.AddMonths(-3), RuleVersion = 1, IsActive = true,
        CreatedByUserId = actorId, UpdatedByUserId = actorId, CreatedAtUtc = now, UpdatedAtUtc = now
    };

    private sealed record ScopeFixture(
        string AdminMobile, string ManagerMobile, string MemberMobile,
        Guid AlphaTaskId, Guid BetaTaskId, long AlphaTaskNumber, long BetaTaskNumber,
        Guid AlphaClientId, Guid BetaClientId, Guid GammaClientId, string AlphaClientCode, string BetaClientCode, string GammaClientCode,
        Guid AlphaAgreementId, Guid BetaAgreementId, Guid GammaAgreementId, Guid AlphaRuleId, Guid BetaRuleId);
}

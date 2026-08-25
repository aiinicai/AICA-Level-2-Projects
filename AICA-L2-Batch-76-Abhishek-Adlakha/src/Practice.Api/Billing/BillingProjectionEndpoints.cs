using System.Globalization;
using System.IO.Compression;
using System.Security.Claims;
using System.Text;
using System.Xml;
using Microsoft.AspNetCore.Antiforgery;
using Microsoft.EntityFrameworkCore;
using Practice.Billing;
using Practice.BuildingBlocks.Clock;
using Practice.Database;
using Practice.Database.Entities;
using Practice.Identity;
using Practice.Reporting;

namespace Practice.Api.Billing;

public static class BillingProjectionEndpoints
{
    private static readonly Guid DefaultCalendarId = new("70a45f7b-dfde-4af0-a634-876797f19501");
    private const int MaximumProjectionDays = 1_827;

    public static IEndpointRouteBuilder MapBillingProjectionEndpoints(this IEndpointRouteBuilder endpoints)
    {
        endpoints.MapGet("/api/v1/billing-projections/masters", MastersAsync)
            .RequireAuthorization("password-current", PermissionCodes.BillingProject);
        endpoints.MapPost("/api/v1/billing-projections:calculate", CalculateAsync)
            .RequireAuthorization("password-current", PermissionCodes.BillingProject)
            .WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        endpoints.MapPost("/api/v1/billing-projections:export", ExportAsync)
            .RequireAuthorization("password-current", PermissionCodes.BillingProject, PermissionCodes.ReportsExport)
            .WithMetadata(new RequireAntiforgeryTokenAttribute(true));
        return endpoints;
    }

    private static async Task<IResult> MastersAsync(
        ClaimsPrincipal principal,
        AppDbContext database,
        CancellationToken cancellationToken)
    {
        var agreements = await ApplyScopeAsync(database.ClientServices.AsNoTracking(), principal, PermissionCodes.BillingProject, database, cancellationToken);
        var agreementIds = await agreements.Select(item => item.Id).ToArrayAsync(cancellationToken);
        var clientIds = await agreements.Select(item => item.ClientId).Distinct().ToArrayAsync(cancellationToken);
        var serviceIds = await agreements.Select(item => item.ServiceId).Distinct().ToArrayAsync(cancellationToken);
        var entityIds = await database.BillingTerms.AsNoTracking()
            .Where(item => agreementIds.Contains(item.ClientServiceId) && item.IsBillable && item.BillingEntityId != null)
            .Select(item => item.BillingEntityId!.Value).Distinct().ToArrayAsync(cancellationToken);

        return Results.Ok(new
        {
            clients = await database.Clients.AsNoTracking().Where(item => clientIds.Contains(item.Id))
                .OrderBy(item => item.DisplayName).Select(item => new { item.Id, item.ClientCode, item.DisplayName }).ToArrayAsync(cancellationToken),
            groups = await database.ClientGroupMemberships.AsNoTracking().Where(item => clientIds.Contains(item.ClientId) && item.MembershipType == "PRIMARY")
                .Select(item => new { item.Group.Id, item.Group.Code, item.Group.Name }).Distinct().OrderBy(item => item.Name).ToArrayAsync(cancellationToken),
            services = await database.Services.AsNoTracking().Where(item => serviceIds.Contains(item.Id))
                .OrderBy(item => item.Name).Select(item => new { item.Id, item.Code, item.Name }).ToArrayAsync(cancellationToken),
            entities = await database.BillingEntities.AsNoTracking().Where(item => entityIds.Contains(item.Id))
                .OrderBy(item => item.LegalName).Select(item => new { item.Id, item.Code, item.LegalName, item.CurrencyCode }).ToArrayAsync(cancellationToken),
            teams = await agreements.Where(item => item.ResponsibleTeamId != null).Select(item => new
                { Id = item.ResponsibleTeamId!.Value, item.ResponsibleTeam!.Code, item.ResponsibleTeam.Name, EmployeeId = item.ResponsibleTeam.ManagerEmployeeId, EmployeeName = item.ResponsibleTeam.ManagerEmployee == null ? null : item.ResponsibleTeam.ManagerEmployee.DisplayName })
                .Distinct().OrderBy(item => item.Name).ToArrayAsync(cancellationToken),
            defaults = new { timeZoneId = "Asia/Kolkata", financialYearStartMonth = 4, groupRule = "PRIMARY_EFFECTIVE_ON_OCCURRENCE", employeeRule = "RESPONSIBLE_TEAM_MANAGER" }
        });
    }

    private static async Task<IResult> CalculateAsync(
        ProjectionRequest request,
        ClaimsPrincipal principal,
        AppDbContext database,
        IClock clock,
        CancellationToken cancellationToken)
    {
        var validation = Validate(request);
        if (validation is not null) return validation;
        return Results.Ok(await CalculateReportAsync(request, principal, database, clock, cancellationToken));
    }

    private static async Task<IResult> ExportAsync(
        ProjectionExportRequest request,
        ClaimsPrincipal principal,
        AppDbContext database,
        IClock clock,
        CancellationToken cancellationToken)
    {
        var validation = Validate(request.Projection);
        if (validation is not null) return validation;
        var format = request.Format.Trim().ToLowerInvariant();
        if (format is not ("csv" or "xlsx"))
        {
            return Results.ValidationProblem(new Dictionary<string, string[]> { ["format"] = ["Export format must be CSV or XLSX."] });
        }

        var report = await CalculateReportAsync(request.Projection, principal, database, clock, cancellationToken, PermissionCodes.ReportsExport);
        var stem = $"billing-projection-{request.Projection.From:yyyyMMdd}-{request.Projection.To:yyyyMMdd}";
        return format == "csv"
            ? Results.File(ProjectionExport.CreateCsv(report), "text/csv; charset=utf-8", $"{stem}.csv")
            : Results.File(ProjectionExport.CreateXlsx(report), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", $"{stem}.xlsx");
    }

    internal static async Task<ProjectionReport> CalculateReportAsync(
        ProjectionRequest request,
        ClaimsPrincipal principal,
        AppDbContext database,
        IClock clock,
        CancellationToken cancellationToken,
        string? additionalScopePermission = null)
    {
        var agreements = await ApplyScopeAsync(database.ClientServices.AsNoTracking(), principal, PermissionCodes.BillingProject, database, cancellationToken);
        if (additionalScopePermission is not null)
        {
            agreements = await ApplyScopeAsync(agreements, principal, additionalScopePermission, database, cancellationToken);
        }
        if (request.ClientId is { } clientId) agreements = agreements.Where(item => item.ClientId == clientId);
        if (request.ServiceId is { } serviceId) agreements = agreements.Where(item => item.ServiceId == serviceId);
        if (request.TeamId is { } teamId) agreements = agreements.Where(item => item.ResponsibleTeamId == teamId);
        if (request.EmployeeId is { } employeeId) agreements = agreements.Where(item => item.ResponsibleTeam != null && item.ResponsibleTeam.ManagerEmployeeId == employeeId);
        var agreementIds = await agreements.Select(item => item.Id).ToArrayAsync(cancellationToken);

        var termQuery = database.BillingTerms.AsNoTracking()
            .Where(item => agreementIds.Contains(item.ClientServiceId) && item.IsBillable && item.PricingModel == "FIXED" && item.Amount != null && item.BillingEntityId != null && item.Schedule != null &&
                           item.EffectiveFrom <= request.To && (item.EffectiveTo == null || item.EffectiveTo >= request.From));
        if (request.BillingEntityId is { } entityId) termQuery = termQuery.Where(item => item.BillingEntityId == entityId);
        var terms = await termQuery
            .Include(item => item.Schedule!).ThenInclude(item => item.Months)
            .Include(item => item.BillingEntity)
            .Include(item => item.ClientService).ThenInclude(item => item.Client)
            .Include(item => item.ClientService).ThenInclude(item => item.Service)
            .Include(item => item.ClientService).ThenInclude(item => item.ResponsibleTeam!).ThenInclude(item => item.ManagerEmployee)
            .OrderBy(item => item.ClientService.Client.DisplayName).ThenBy(item => item.ClientService.Service.Name).ThenBy(item => item.EffectiveFrom)
            .ToArrayAsync(cancellationToken);

        var clientIds = terms.Select(item => item.ClientService.ClientId).Distinct().ToArray();
        var memberships = await database.ClientGroupMemberships.AsNoTracking()
            .Where(item => clientIds.Contains(item.ClientId) && item.MembershipType == "PRIMARY" && item.EffectiveFrom <= request.To && (item.ValidTo == null || item.ValidTo >= request.From))
            .Include(item => item.Group).OrderByDescending(item => item.EffectiveFrom).ThenBy(item => item.Group.Name)
            .ToArrayAsync(cancellationToken);
        var membershipsByClient = memberships.GroupBy(item => item.ClientId).ToDictionary(group => group.Key, group => group.ToArray());
        var holidays = await database.Holidays.AsNoTracking()
            .Where(item => item.HolidayCalendarId == DefaultCalendarId && item.HolidayDate >= request.From.AddDays(-7) && item.HolidayDate <= request.To.AddDays(7))
            .ToDictionaryAsync(item => item.HolidayDate, item => item.IsWorkingDayOverride, cancellationToken);

        var details = new List<ProjectionDetail>();
        foreach (var term in terms)
        {
            var schedule = term.Schedule!;
            var projectionTerm = new ProjectionTerm(term.Id, term.Version, term.Amount!.Value, term.CurrencyCode, term.EffectiveFrom, term.EffectiveTo,
                new ProjectionSchedule(schedule.FrequencyCode, schedule.AnchorDate, schedule.BillingDay, schedule.BusinessDayAdjustment, schedule.OneTimeDate, schedule.Months.Select(item => item.Month).ToArray()));
            foreach (var occurrence in BillingProjectionCalculator.Calculate(projectionTerm, request.From, request.To, holidays))
            {
                var agreement = term.ClientService;
                var entity = term.BillingEntity!;
                if (!EffectiveOn(agreement.EffectiveFrom, agreement.EffectiveTo, occurrence.ProjectionDate) ||
                    !EffectiveOn(entity.EffectiveFrom, entity.EffectiveTo, occurrence.ProjectionDate)) continue;

                var primaryMembership = membershipsByClient.GetValueOrDefault(agreement.ClientId)?
                    .FirstOrDefault(item => EffectiveOn(item.EffectiveFrom, item.ValidTo, occurrence.ProjectionDate));
                if (request.GroupId is { } groupId && primaryMembership?.GroupId != groupId) continue;
                var team = agreement.ResponsibleTeam;
                details.Add(new ProjectionDetail(
                    occurrence.TermId, occurrence.TermVersion, agreement.Id, agreement.ClientId, agreement.Client.ClientCode,
                    agreement.Client.DisplayName, primaryMembership?.GroupId, primaryMembership?.Group.Name ?? "Ungrouped",
                    agreement.ServiceId, agreement.Service.Code, agreement.Service.Name, entity.Id, entity.Code, entity.LegalName,
                    team?.Id, team?.Name, team?.ManagerEmployeeId, team?.ManagerEmployee?.DisplayName,
                    occurrence.NominalDate, occurrence.ProjectionDate, occurrence.ServicePeriodStart, occurrence.ServicePeriodEnd,
                    occurrence.Amount, occurrence.CurrencyCode, term.TaxInclusive, schedule.FrequencyCode, occurrence.Explanation));
            }
        }

        var ordered = details.OrderBy(item => item.ProjectionDate).ThenBy(item => item.ClientName).ThenBy(item => item.ServiceName).ToArray();
        return new ProjectionReport(
            request.From,
            request.To,
            request.AsOf ?? DateOnly.FromDateTime(clock.UtcNow.ToOffset(TimeSpan.FromHours(5.5)).DateTime),
            clock.UtcNow,
            "Expected fixed fees per configured billing event; not invoices, receivables, payments, revenue or tax calculations.",
            ["Primary client group effective on each projection date; no multi-group double counting.", "Amounts are aggregated only inside the same currency.", "Employee attribution means the responsible team manager on the current agreement and is not revenue ownership.", "Sunday and India firm-calendar holidays follow the term's previous/next business-day rule.", "The as-of date labels this calculation context; configuration is calculated from the currently stored effective-dated terms."],
            Summarize(ordered, item => item.CurrencyCode, item => item.CurrencyCode),
            Summarize(ordered, item => $"{item.ProjectionDate:yyyy-MM}|{item.CurrencyCode}", item => $"{item.ProjectionDate:MMM yyyy}"),
            Summarize(ordered, item => $"{item.ProjectionDate.Year}-Q{((item.ProjectionDate.Month - 1) / 3) + 1}|{item.CurrencyCode}", item => $"{item.ProjectionDate.Year} Q{((item.ProjectionDate.Month - 1) / 3) + 1}"),
            Summarize(ordered, item => $"{FinancialYear(item.ProjectionDate)}|{item.CurrencyCode}", item => FinancialYear(item.ProjectionDate)),
            Summarize(ordered, item => $"{item.ClientId}|{item.CurrencyCode}", item => $"{item.ClientName} · {item.ClientCode}"),
            Summarize(ordered, item => $"{item.GroupId}|{item.CurrencyCode}", item => item.GroupName),
            Summarize(ordered, item => $"{item.BillingEntityId}|{item.CurrencyCode}", item => $"{item.BillingEntityName} · {item.BillingEntityCode}"),
            Summarize(ordered, item => $"{item.ServiceId}|{item.CurrencyCode}", item => item.ServiceName),
            Summarize(ordered, item => $"{item.TeamId}|{item.CurrencyCode}", item => item.TeamName ?? "No responsible team"),
            Summarize(ordered, item => $"{item.EmployeeId}|{item.CurrencyCode}", item => item.EmployeeName ?? "No responsible manager"),
            ordered);
    }

    private static ProjectionSummary[] Summarize(
        IReadOnlyCollection<ProjectionDetail> details,
        Func<ProjectionDetail, string> key,
        Func<ProjectionDetail, string> label) => details
        .GroupBy(key).Select(group => new ProjectionSummary(group.Key, label(group.First()), group.First().CurrencyCode, group.Sum(item => item.Amount), group.Count()))
        .OrderBy(item => item.Label).ThenBy(item => item.CurrencyCode).ToArray();

    // Delegates to the shared rule so billing and tasks cannot drift on what a financial year is.
    private static string FinancialYear(DateOnly date) => ReportingRules.FinancialYearLabel(date);

    private static bool EffectiveOn(DateOnly from, DateOnly? to, DateOnly date) => from <= date && (to is null || to >= date);

    private static IResult? Validate(ProjectionRequest request)
    {
        var errors = new Dictionary<string, string[]>();
        if (request.From == default) errors["from"] = ["Projection start date is required."];
        if (request.To == default) errors["to"] = ["Projection end date is required."];
        if (request.To < request.From) errors["to"] = ["Projection end date cannot precede its start date."];
        else if (request.To.DayNumber - request.From.DayNumber > MaximumProjectionDays) errors["to"] = ["One projection may cover at most five years."];
        if (request.AsOf is { } asOf && asOf.Year < 2000) errors["asOf"] = ["Choose a valid as-of date."];
        return errors.Count == 0 ? null : Results.ValidationProblem(errors);
    }

    private static async Task<IQueryable<ClientService>> ApplyScopeAsync(
        IQueryable<ClientService> query,
        ClaimsPrincipal principal,
        string permission,
        AppDbContext database,
        CancellationToken cancellationToken)
    {
        var scope = principal.FindFirstValue(IdentityConstants.ScopeClaimPrefix + permission);
        if (scope == "ALL") return query;
        var employeeId = await database.Employees.Where(item => item.UserId == UserId(principal) && item.IsActive).Select(item => (Guid?)item.Id).SingleOrDefaultAsync(cancellationToken);
        if (employeeId is null) return query.Where(_ => false);
        var teamIds = database.TeamMemberships.Where(item => item.EmployeeId == employeeId && item.ValidTo == null).Select(item => item.TeamId);
        if (scope == "TEAM")
        {
            var reports = database.Employees.Where(item => item.ManagerEmployeeId == employeeId && item.IsActive).Select(item => item.Id);
            teamIds = teamIds.Concat(database.Teams.Where(item => item.ManagerEmployeeId == employeeId && item.IsActive).Select(item => item.Id))
                .Concat(database.TeamMemberships.Where(item => reports.Contains(item.EmployeeId) && item.ValidTo == null).Select(item => item.TeamId));
        }
        var accessible = await teamIds.Distinct().ToArrayAsync(cancellationToken);
        return query.Where(item => item.ResponsibleTeamId != null && accessible.Contains(item.ResponsibleTeamId.Value));
    }

    private static Guid UserId(ClaimsPrincipal principal) => Guid.Parse(principal.FindFirstValue(ClaimTypes.NameIdentifier)!);
}

public sealed record ProjectionRequest(DateOnly From, DateOnly To, DateOnly? AsOf, Guid? ClientId, Guid? GroupId, Guid? ServiceId, Guid? BillingEntityId, Guid? TeamId, Guid? EmployeeId);
public sealed record ProjectionExportRequest(string Format, ProjectionRequest Projection);
public sealed record ProjectionSummary(string Key, string Label, string CurrencyCode, decimal Amount, int OccurrenceCount);
public sealed record ProjectionDetail(
    Guid TermId, int TermVersion, Guid ClientServiceId, Guid ClientId, string ClientCode, string ClientName,
    Guid? GroupId, string GroupName, Guid ServiceId, string ServiceCode, string ServiceName,
    Guid BillingEntityId, string BillingEntityCode, string BillingEntityName,
    Guid? TeamId, string? TeamName, Guid? EmployeeId, string? EmployeeName,
    DateOnly NominalDate, DateOnly ProjectionDate, DateOnly ServicePeriodStart, DateOnly ServicePeriodEnd,
    decimal Amount, string CurrencyCode, bool TaxInclusive, string FrequencyCode, string Explanation);
public sealed record ProjectionReport(
    DateOnly From, DateOnly To, DateOnly AsOf, DateTimeOffset GeneratedAtUtc, string Definition, string[] Assumptions,
    ProjectionSummary[] Totals, ProjectionSummary[] Months, ProjectionSummary[] Quarters, ProjectionSummary[] FinancialYears,
    ProjectionSummary[] Clients, ProjectionSummary[] Groups, ProjectionSummary[] BillingEntities, ProjectionSummary[] Services,
    ProjectionSummary[] Teams, ProjectionSummary[] Employees, ProjectionDetail[] Details);

public static class ProjectionExport
{
    private static readonly string[] Headers = ["Projection date", "Nominal date", "Service period start", "Service period end", "Client code", "Client", "Primary group", "Service code", "Service", "Billing entity code", "Billing entity", "Responsible team", "Responsible manager", "Frequency", "Term version", "Currency", "Amount", "Tax inclusive", "Explanation"];

    public static byte[] CreateCsv(ProjectionReport report)
    {
        var output = new StringBuilder("\uFEFF");
        output.AppendLine(string.Join(',', Headers.Select(Csv)));
        foreach (var row in Rows(report)) output.AppendLine(string.Join(',', row.Select(Csv)));
        return Encoding.UTF8.GetBytes(output.ToString());
    }

    public static byte[] CreateXlsx(ProjectionReport report)
    {
        using var stream = new MemoryStream();
        using (var archive = new ZipArchive(stream, ZipArchiveMode.Create, true))
        {
            WriteText(archive, "[Content_Types].xml", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Types xmlns=\"http://schemas.openxmlformats.org/package/2006/content-types\"><Default Extension=\"rels\" ContentType=\"application/vnd.openxmlformats-package.relationships+xml\"/><Default Extension=\"xml\" ContentType=\"application/xml\"/><Override PartName=\"/xl/workbook.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet.main+xml\"/><Override PartName=\"/xl/worksheets/sheet1.xml\" ContentType=\"application/vnd.openxmlformats-officedocument.spreadsheetml.worksheet+xml\"/></Types>");
            WriteText(archive, "_rels/.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/officeDocument\" Target=\"xl/workbook.xml\"/></Relationships>");
            WriteText(archive, "xl/workbook.xml", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><workbook xmlns=\"http://schemas.openxmlformats.org/spreadsheetml/2006/main\" xmlns:r=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships\"><sheets><sheet name=\"Projection detail\" sheetId=\"1\" r:id=\"rId1\"/></sheets></workbook>");
            WriteText(archive, "xl/_rels/workbook.xml.rels", "<?xml version=\"1.0\" encoding=\"UTF-8\"?><Relationships xmlns=\"http://schemas.openxmlformats.org/package/2006/relationships\"><Relationship Id=\"rId1\" Type=\"http://schemas.openxmlformats.org/officeDocument/2006/relationships/worksheet\" Target=\"worksheets/sheet1.xml\"/></Relationships>");
            var entry = archive.CreateEntry("xl/worksheets/sheet1.xml", CompressionLevel.Fastest);
            using var writer = XmlWriter.Create(entry.Open(), new XmlWriterSettings { Encoding = new UTF8Encoding(false), CloseOutput = true });
            writer.WriteStartDocument(); writer.WriteStartElement("worksheet", "http://schemas.openxmlformats.org/spreadsheetml/2006/main"); writer.WriteStartElement("sheetData");
            WriteRow(writer, Headers);
            foreach (var row in Rows(report)) WriteRow(writer, row, 16);
            writer.WriteEndElement(); writer.WriteEndElement(); writer.WriteEndDocument();
        }
        return stream.ToArray();
    }

    private static IEnumerable<string[]> Rows(ProjectionReport report) => report.Details.Select(item => new[]
    {
        item.ProjectionDate.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), item.NominalDate.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
        item.ServicePeriodStart.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture), item.ServicePeriodEnd.ToString("yyyy-MM-dd", CultureInfo.InvariantCulture),
        item.ClientCode, item.ClientName, item.GroupName, item.ServiceCode, item.ServiceName, item.BillingEntityCode, item.BillingEntityName,
        item.TeamName ?? string.Empty, item.EmployeeName ?? string.Empty, item.FrequencyCode, item.TermVersion.ToString(CultureInfo.InvariantCulture),
        item.CurrencyCode, item.Amount.ToString("0.00", CultureInfo.InvariantCulture), item.TaxInclusive ? "Yes" : "No", item.Explanation
    });

    private static string Csv(string value)
    {
        if (value.Length > 0 && "=+-@".Contains(value[0])) value = "'" + value;
        return $"\"{value.Replace("\"", "\"\"")}\"";
    }

    private static void WriteText(ZipArchive archive, string path, string content)
    {
        var entry = archive.CreateEntry(path, CompressionLevel.Fastest);
        using var writer = new StreamWriter(entry.Open(), new UTF8Encoding(false)); writer.Write(content);
    }

    private static void WriteRow(XmlWriter writer, IEnumerable<string> values, int? numericColumn = null)
    {
        writer.WriteStartElement("row");
        var index = 0;
        foreach (var value in values)
        {
            writer.WriteStartElement("c");
            if (index == numericColumn)
            {
                writer.WriteElementString("v", value);
            }
            else
            {
                writer.WriteAttributeString("t", "inlineStr"); writer.WriteStartElement("is"); writer.WriteElementString("t", value); writer.WriteEndElement();
            }
            writer.WriteEndElement(); index++;
        }
        writer.WriteEndElement();
    }
}

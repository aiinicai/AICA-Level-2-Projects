using System.Net;
using System.Net.Http.Json;
using System.Text.Json;
using Microsoft.EntityFrameworkCore;
using Microsoft.Extensions.DependencyInjection;
using Practice.Database;
using Practice.Database.Entities;

namespace Practice.Api.IntegrationTests;

// A fee timeline is effective-dated history, so the only safe way to undo a mistaken revision is to
// remove the current version and reopen the one it replaced. These checks pin that behaviour, and
// the two defects that produced it: the timeline offered "Replace" on a closed agreement, and the
// refusal that followed told the user to "choose an active client-service agreement" on a form
// where the agreement cannot be chosen.
internal static class BillingTermChecks
{
    public static async Task RunAsync(ApiFactory factory, string mobile, string password, List<string> failures)
    {
        var (agreementId, entityId) = await SeedAsync(factory);

        using var client = factory.CreateDefaultClient(new Microsoft.AspNetCore.Mvc.Testing.Handlers.CookieContainerHandler());
        var login = new HttpRequestMessage(HttpMethod.Post, "/api/v1/auth/login")
        {
            Content = JsonContent.Create(new { mobileNumber = mobile, password })
        };
        login.Headers.Add("X-CSRF-TOKEN", await CsrfAsync(client));
        if (!(await client.SendAsync(login)).IsSuccessStatusCode)
        {
            failures.Add("Billing term fixture sign-in failed.");
            return;
        }

        var today = DateOnly.FromDateTime(DateTime.UtcNow);
        var first = await PostAsync(client, "/api/v1/billing/terms", Term(agreementId, entityId, 5000m, today.AddMonths(-3)));
        if (first.Status != HttpStatusCode.Created)
        {
            failures.Add($"Creating the first billing term returned {(int)first.Status}, expected 201.");
            return;
        }
        var firstId = first.Body.RootElement.GetProperty("id").GetGuid();

        var second = await PostAsync(client, $"/api/v1/billing/terms/{firstId}/replace", Term(agreementId, entityId, 7500m, today));
        if (second.Status != HttpStatusCode.Created)
        {
            failures.Add($"Revising the billing term returned {(int)second.Status}, expected 201.");
            return;
        }
        var secondId = second.Body.RootElement.GetProperty("id").GetGuid();

        // History is not rewritten: the superseded version records what was actually agreed.
        var superseded = await PostAsync(client, $"/api/v1/billing/terms/{firstId}/remove", new { reason = "rewriting history" });
        if (superseded.Status != HttpStatusCode.Conflict)
        {
            failures.Add($"Removing a superseded billing term returned {(int)superseded.Status}, expected 409.");
        }

        var unexplained = await PostAsync(client, $"/api/v1/billing/terms/{secondId}/remove", new { reason = "  " });
        if (unexplained.Status != HttpStatusCode.BadRequest)
        {
            failures.Add($"Removing a billing term without a reason returned {(int)unexplained.Status}, expected 400.");
        }

        var removed = await PostAsync(client, $"/api/v1/billing/terms/{secondId}/remove", new { reason = "entered the wrong amount" });
        if (removed.Status != HttpStatusCode.NoContent)
        {
            failures.Add($"Removing the current billing term returned {(int)removed.Status}, expected 204.");
        }

        // Removing the revision must restore the state that existed before it, not leave the
        // agreement with a fee timeline that ends in the past.
        var reopened = await TermsAsync(client, agreementId);
        if (reopened.Length != 1)
        {
            failures.Add($"After removal the fee timeline held {reopened.Length} versions, expected 1.");
        }
        else if (reopened[0].GetProperty("effectiveTo").ValueKind != JsonValueKind.Null)
        {
            failures.Add("Removing a revision must reopen the version it replaced, leaving no end date.");
        }

        using (var scope = factory.Services.CreateScope())
        {
            var database = scope.ServiceProvider.GetRequiredService<AppDbContext>();
            if (!await database.AuditEvents.AnyAsync(item => item.Action == "billing.term_removed"))
            {
                failures.Add("Removing a billing term must be written to the audit trail.");
            }
            if (await database.BillingSchedules.AnyAsync(item => item.BillingTermId == secondId))
            {
                failures.Add("Removing a billing term must not leave its billing schedule behind.");
            }

            // Closing an agreement carries a timestamp and a reason; the database refuses it otherwise.
            var agreement = await database.ClientServices.SingleAsync(item => item.Id == agreementId);
            agreement.IsActive = false;
            agreement.DeactivatedAtUtc = DateTimeOffset.UtcNow;
            agreement.DeactivationReason = "Client stopped using this service.";
            await database.SaveChangesAsync();
        }

        // The screen must be able to tell that a fee can no longer be revised, rather than offering
        // an action the API will refuse.
        var closed = await TermsAsync(client, agreementId);
        if (closed.Length != 1 || closed[0].GetProperty("agreementIsActive").GetBoolean())
        {
            failures.Add("The fee timeline must report a closed agreement as inactive.");
        }

        var refused = await PostAsync(client, $"/api/v1/billing/terms/{firstId}/replace", Term(agreementId, entityId, 9000m, today.AddMonths(1)));
        if (refused.Status != HttpStatusCode.BadRequest)
        {
            failures.Add($"Revising a fee on a closed agreement returned {(int)refused.Status}, expected 400.");
        }
        else
        {
            var message = refused.Body.RootElement.GetProperty("errors").GetProperty("clientServiceId")[0].GetString() ?? string.Empty;
            if (!message.Contains("has been closed", StringComparison.Ordinal))
            {
                failures.Add($"The refusal must name the real cause; it said: {message}");
            }
        }
    }

    private static object Term(Guid agreementId, Guid entityId, decimal amount, DateOnly effectiveFrom) => new
    {
        clientServiceId = agreementId,
        isBillable = true,
        billingEntityId = entityId,
        amount,
        currencyCode = "INR",
        taxInclusive = false,
        effectiveFrom,
        effectiveTo = (DateOnly?)null,
        notes = "Billing term regression fixture.",
        schedule = new
        {
            frequencyCode = "MONTHLY",
            anchorDate = effectiveFrom,
            billingDay = 1,
            businessDayAdjustment = "NONE",
            oneTimeDate = (DateOnly?)null,
            months = Array.Empty<int>()
        }
    };

    private static async Task<(HttpStatusCode Status, JsonDocument Body)> PostAsync(HttpClient client, string route, object payload)
    {
        var request = new HttpRequestMessage(HttpMethod.Post, route) { Content = JsonContent.Create(payload) };
        request.Headers.Add("X-CSRF-TOKEN", await CsrfAsync(client));
        var response = await client.SendAsync(request);
        var body = await response.Content.ReadAsStringAsync();
        return (response.StatusCode, JsonDocument.Parse(string.IsNullOrWhiteSpace(body) ? "{}" : body));
    }

    private static async Task<JsonElement[]> TermsAsync(HttpClient client, Guid agreementId)
    {
        using var document = JsonDocument.Parse(
            await client.GetStringAsync($"/api/v1/billing/terms?clientServiceId={agreementId}"));
        return document.RootElement.EnumerateArray().Select(item => item.Clone()).ToArray();
    }

    private static async Task<string> CsrfAsync(HttpClient client)
    {
        using var document = JsonDocument.Parse(await client.GetStringAsync("/api/v1/auth/csrf"));
        return document.RootElement.GetProperty("token").GetString()!;
    }

    private static async Task<(Guid AgreementId, Guid EntityId)> SeedAsync(ApiFactory factory)
    {
        using var scope = factory.Services.CreateScope();
        var database = scope.ServiceProvider.GetRequiredService<AppDbContext>();
        var now = DateTimeOffset.UtcNow;
        var today = DateOnly.FromDateTime(now.UtcDateTime);
        var serviceId = await database.Services.Select(item => item.Id).FirstAsync();

        var client = new Client
        {
            Id = Guid.NewGuid(), ClientCode = "TERM-CLI", NormalizedClientCode = "TERM-CLI",
            DisplayName = "Billing Term Client", NormalizedDisplayName = "BILLING TERM CLIENT",
            Status = "ACTIVE", CreatedAtUtc = now, UpdatedAtUtc = now
        };
        var agreement = new ClientService
        {
            Id = Guid.NewGuid(), ClientId = client.Id, ServiceId = serviceId, EffectiveFrom = today.AddYears(-1),
            IsActive = true, DefaultPriority = "NORMAL", CreatedAtUtc = now, UpdatedAtUtc = now
        };
        var entity = new BillingEntity
        {
            Id = Guid.NewGuid(), Code = "TERM-ENT", LegalName = "Billing Term Entity",
            CurrencyCode = "INR", EffectiveFrom = today.AddYears(-2), IsActive = true,
            CreatedAtUtc = now, UpdatedAtUtc = now
        };
        database.Clients.Add(client);
        database.ClientServices.Add(agreement);
        database.BillingEntities.Add(entity);
        await database.SaveChangesAsync();
        return (agreement.Id, entity.Id);
    }
}

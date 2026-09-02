using System.Security.Claims;
using Microsoft.AspNetCore.Authentication;
using Microsoft.AspNetCore.Authentication.Cookies;
using Microsoft.AspNetCore.Http;

namespace Practice.Identity;

public sealed class SessionCookieEvents(IdentityService identityService) : CookieAuthenticationEvents
{
    public override async Task ValidatePrincipal(CookieValidatePrincipalContext context)
    {
        var userIdValue = context.Principal?.FindFirstValue(ClaimTypes.NameIdentifier);
        var rawToken = context.Principal?.FindFirstValue(IdentityConstants.SessionTokenClaim);
        if (!Guid.TryParse(userIdValue, out var userId))
        {
            context.RejectPrincipal();
            return;
        }

        var session = await identityService.ValidateSessionAsync(userId, rawToken, context.HttpContext.RequestAborted);
        if (session is null)
        {
            context.RejectPrincipal();
            return;
        }

        context.ReplacePrincipal(IdentityService.CreatePrincipal(session, rawToken!));
    }

    public override Task RedirectToLogin(RedirectContext<CookieAuthenticationOptions> context)
    {
        context.Response.StatusCode = StatusCodes.Status401Unauthorized;
        return Task.CompletedTask;
    }

    public override Task RedirectToAccessDenied(RedirectContext<CookieAuthenticationOptions> context)
    {
        context.Response.StatusCode = StatusCodes.Status403Forbidden;
        return Task.CompletedTask;
    }
}

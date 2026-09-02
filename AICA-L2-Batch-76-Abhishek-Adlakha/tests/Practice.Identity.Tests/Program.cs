using System.Security.Claims;
using Practice.Identity;

Require(CredentialRules.TryNormalizeMobile("98765 43210", out var mobile) && mobile == "9876543210",
    "A valid formatted Indian mobile number should normalize to ten digits.");
Require(!CredentialRules.TryNormalizeMobile("5123456789", out _),
    "An Indian mobile login must begin with 6, 7, 8, or 9.");
Require(!CredentialRules.TryNormalizeMobile("987654321", out _),
    "A mobile login must contain exactly ten digits.");
Require(!CredentialRules.TryNormalizeMobile("mobile9876543210", out _),
    "Unexpected non-formatting characters must not be ignored in a mobile login.");

Require(CredentialRules.ValidatePassword("short", mobile).Count > 0,
    "A short password must be rejected.");
Require(CredentialRules.ValidatePassword("Strong-9876543210!", mobile).Count > 0,
    "A password containing the login mobile must be rejected.");
Require(CredentialRules.ValidatePassword("Correct-Horse-71!", mobile).Count == 0,
    "A valid long password should pass the Phase 2 rules.");

var first = SessionToken.Create();
var second = SessionToken.Create();
Require(first != second, "Session tokens must be randomly unique.");
Require(SessionToken.Hash(first).Length == 32, "Only a 32-byte SHA-256 session-token hash is persisted.");

var userId = Guid.NewGuid();
var loginPrincipal = IdentityService.CreatePrincipal(new AuthenticatedSession(
    userId, mobile, "Test Administrator", false, first, DateTimeOffset.UtcNow.AddHours(12),
    ["Administrators"], new Dictionary<string, string>
    {
        [PermissionCodes.UsersManage] = "ALL",
        [PermissionCodes.RolesManage] = "ALL"
    }));
Require(loginPrincipal.FindFirst(ClaimTypes.NameIdentifier)?.Value == userId.ToString(),
    "The login ticket must identify its user.");
Require(loginPrincipal.FindFirst(IdentityConstants.SessionTokenClaim)?.Value == first,
    "The login ticket must contain its server-session token.");
Require(loginPrincipal.Claims.Count() == 2,
    "The login ticket must remain compact; access claims are reloaded during cookie validation.");
Require(!loginPrincipal.HasClaim(claim => claim.Type == IdentityConstants.PermissionClaim),
    "Permissions must not be serialized into the browser cookie.");

Console.WriteLine("Identity credential and session-token checks passed.");
return 0;

static void Require(bool condition, string message)
{
    if (!condition) throw new InvalidOperationException(message);
}

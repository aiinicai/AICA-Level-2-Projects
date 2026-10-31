using System.Security.Claims;
using System.Text.Json;
using System.Text.Json.Nodes;
using Sales360.Domain;
namespace Sales360.Api;
public static class AreaAccess
{
    public static readonly string[] Areas=["dashboard","customers","projects","documents","billing","approvals","receivables","collections","statements","reports","compliance","imports","integrations","audit","backup","settings","users"];
    public static string[] Defaults(string tier,string duty)=>tier=="Administrator"?["*"]:duty switch {
        "Finance Administrator"=>["dashboard","customers","projects","documents","billing","approvals","receivables","collections","statements","reports","compliance","imports","integrations","audit","backup"],
        "Accountant"=>["dashboard","customers","projects","documents","billing","approvals","statements","reports","compliance","imports"],
        "Reviewer 1" or "Reviewer 2" or "Approver"=>["dashboard","projects","documents","billing","approvals","reports"],
        "Collections Officer"=>["dashboard","customers","projects","receivables","collections","statements","reports"],
        "Auditor"=>["dashboard","customers","projects","billing","receivables","collections","statements","reports","audit"],
        _=>tier=="Super user"?["dashboard","customers","projects","imports","reports"]:["dashboard"]};
    public static string[] Parse(JsonNode? node,string tier,string duty){var areas=node==null?Defaults(tier,duty):node.AsArray().Select(x=>x!.GetValue<string>()).Distinct().ToArray();Billing.Require(areas.All(x=>x=="*"||Areas.Contains(x)),"Choose valid work areas.");return tier=="Administrator"?["*"]:areas;}
    public static string[] Granted(ClaimsPrincipal user)=>JsonSerializer.Deserialize<string[]>(user.FindFirstValue("work_areas")??"[]")??[];
    public static string[] Required(PathString path)
    {
        var p=path.Value??"";
        if(p.StartsWith("/api/vat"))return p.EndsWith("/pdf")?["billing","compliance"]:["compliance"];
        if(p.StartsWith("/api/analytics"))return ["reports"];
        if(p.StartsWith("/api/utility"))return ["integrations"];
        if(p.StartsWith("/api/customers")||p.StartsWith("/api/customer-fields"))return ["customers"];
        if(p.StartsWith("/api/projects"))return ["projects"];
        if(p.StartsWith("/api/contracts"))return ["documents"];
        if(p.StartsWith("/api/certificates"))return p.EndsWith("/transition")?["approvals"]:["billing"];
        if(p.StartsWith("/api/drafts"))return ["billing"];
        if(p.StartsWith("/api/invoices"))return ["billing","receivables"];
        if(p.StartsWith("/api/corrections"))return ["receivables"];
        if(p.StartsWith("/api/receipts")||p.StartsWith("/api/allocations"))return ["collections"];
        if(p.StartsWith("/api/statements"))return ["statements"];
        if(p.StartsWith("/api/dashboard"))return ["dashboard","reports"];
        if(p.StartsWith("/api/imports")||p.StartsWith("/api/workbook-imports"))return ["imports"];
        if(p.StartsWith("/api/integrations")||p.StartsWith("/api/simulator")||p.StartsWith("/api/jobs"))return ["integrations"];
        if(p.StartsWith("/api/audit"))return ["audit"];
        return [];
    }
    public static async Task Check(HttpContext h,RequestDelegate next)
    {
        if(h.User.Identity?.IsAuthenticated==true&&!h.User.IsInRole("Administrator")){
            var required=Required(h.Request.Path);var grants=Granted(h.User);
            if(required.Length>0&&!grants.Contains("*")&&!required.Any(grants.Contains)){h.Response.StatusCode=403;await h.Response.WriteAsJsonAsync(new{error="Your Administrator has not assigned this work area."});return;}
        }
        await next(h);
    }
}

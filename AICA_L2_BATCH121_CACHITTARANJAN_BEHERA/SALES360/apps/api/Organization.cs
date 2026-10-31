using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Npgsql;
using Sales360.Domain;
namespace Sales360.Api;

public static class Organization
{
    public static async Task<JsonObject> Read(NpgsqlConnection c,string company)=>await Store.One(c,"SELECT c.id,c.name,c.currency,coalesce(p.details,'{}'::jsonb) AS profile,coalesce(p.revision,0) AS revision,p.updated_at,p.updated_by FROM company c LEFT JOIN organization_profile p ON p.company_id=c.id WHERE c.id=@p0",company);
    public static async Task<JsonObject> Snapshot(NpgsqlConnection c,string company)
    {
        var record=await Read(c,company);var profile=record["profile"]!.DeepClone().AsObject();
        if(profile.Text("legal_name")=="")profile["legal_name"]=record.Text("name");
        profile["currency"]=record.Text("currency");profile["profile_revision"]=record.Integer("revision");return profile;
    }
    public static void ValidatePeriod(JsonObject b)
    {
        Billing.Require(DateOnly.TryParseExact(b.Text("period_start"),"yyyy-MM-dd",out var start)&&DateOnly.TryParseExact(b.Text("period_end"),"yyyy-MM-dd",out var end)&&start<=end,"Enter an accounting period with valid start and end dates, in order.");
    }
    public static void Map(RouteGroupBuilder api,Store store,Func<HttpContext,string> company,Func<HttpContext,string> actor)
    {
        api.MapGet("/organization",async(HttpContext h)=>{await using var c=await store.Open();var result=await Read(c,company(h));if(!h.User.IsInRole("Administrator"))result.Remove("profile");return result;});
        api.MapPost("/organization",async(HttpContext h,JsonObject b)=>{
            Accounts.Administrator(h);return await store.Transaction(company(h),async c=>{
                var current=await Read(c,company(h));Billing.Require(b.Integer("expected_revision")==current.Integer("revision"),"Settings changed since you opened this page. Reload before saving.");
                ValidatePeriod(b);var p=new JsonObject();
                foreach(var key in new[]{"legal_name","registered_address","trn","bank_details","invoice_prefix","finance_approver","approval_reference","vat_policy","advance_policy","retention_policy","review_status","period_start","period_end"}){
                    var value=b.Text(key);var limit=key.EndsWith("policy")?4000:key is "registered_address" or "bank_details"?2000:200;
                    Billing.Require(value.Length<=limit,$"{key} exceeds {limit} characters.");p[key]=value;
                }
                Billing.Require(p.Text("legal_name").Length>=2,"Enter the company's legal/display name.");
                Billing.Require(p.Text("trn")==""||Regex.IsMatch(p.Text("trn"),"^[0-9]{15}$"),"TRN must be blank or exactly 15 digits.");
                Billing.Require(Regex.IsMatch(p.Text("invoice_prefix"),"^[A-Za-z0-9][A-Za-z0-9_-]{0,19}$"),"Invoice prefix must be 1–20 letters, numbers, hyphens or underscores.");
                Billing.Require(p.Text("review_status") is "Draft" or "Reviewed","Choose Draft or Reviewed policy status.");
                if(p.Text("review_status")=="Reviewed"){
                    Billing.Require(new[]{"registered_address","finance_approver","approval_reference","vat_policy","advance_policy","retention_policy"}.All(k=>p.Text(k).Length>=3),"Reviewed settings need an address, named approver, review reference and all three policy descriptions.");
                }
                var revision=current.Integer("revision")+1;
                await Store.Exec(c,"INSERT INTO organization_profile(company_id,details,revision,updated_by) VALUES(@p0,@p1::jsonb,@p2,@p3) ON CONFLICT(company_id) DO UPDATE SET details=excluded.details,revision=excluded.revision,updated_by=excluded.updated_by,updated_at=now()",company(h),p.ToJsonString(),revision,actor(h));
                await Store.Exec(c,"UPDATE company SET name=@p1 WHERE id=@p0",company(h),p.Text("legal_name"));
                await Store.Audit(c,company(h),actor(h),"Organization settings saved",company(h),new{revision,profile=p});return await Read(c,company(h));
            });
        });
    }
}

using System.Security.Cryptography;
using System.Text;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Sales360.Domain;
namespace Sales360.Api;
public static class Enrollment
{
    public static (string? Email,string? Username) Identifier(string value,bool offline)
    {
        value=value.Trim().ToLowerInvariant();if(value.Contains('@'))return (Accounts.Email(value),null);
        Billing.Require(offline&&Regex.IsMatch(value,"^[a-z0-9][a-z0-9._-]{2,63}$"),"Enter an email address or a username of 3–64 letters, numbers, dots, hyphens or underscores.");return (null,value);
    }
    public static async Task Initialize(Store store,string hash)
    {
        if(Environment.GetEnvironmentVariable("SALES360_MAIL_MODE")!="Offline")throw new InvalidOperationException("First-owner enrollment requires Offline mode.");
        await store.Transaction("local",async c=>{
            if((await Store.One(c,"SELECT count(*) AS count FROM app_user")).Integer("count")>0)return 0;
            await Store.Exec(c,"INSERT INTO company(id,name) VALUES('local','My Company') ON CONFLICT DO NOTHING; INSERT INTO numbering(company_id) VALUES('local') ON CONFLICT DO NOTHING");
            await Store.Exec(c,"INSERT INTO first_admin_setup(company_id,token_hash) VALUES('local',@p0) ON CONFLICT DO NOTHING",hash);return 0;
        });
    }
    public static void Map(WebApplication app,Store store,IdentityMail mail)
    {
        app.MapPost("/api/auth/first-administrator",async(HttpContext h,JsonObject b)=>{
            Billing.Require(mail.IsOffline&&h.Connection.RemoteIpAddress is not null&&System.Net.IPAddress.IsLoopback(h.Connection.RemoteIpAddress),"Administrator setup is local only.");
            Accounts.Password(Accounts.Secret(b));Billing.Require(Accounts.Secret(b)==Accounts.Secret(b,"confirm_password"),"Passwords do not match.");var identity=Identifier(b.Text("identifier"),true);var recoveryEmail=Accounts.Email(b.Text("recovery_email"));Billing.Require(identity.Email==null||identity.Email==recoveryEmail,"When using email as your login, use the same recovery email.");var companyName=b.Text("company_name");Billing.Require(companyName.Length is >=2 and <=200,"Enter your company name.");Organization.ValidatePeriod(b);var name=b.Text("name");Billing.Require(name.Length is >=2 and <=120,"Enter your full name.");
            return await store.Transaction("local",async c=>{
                var setup=await Store.One(c,"SELECT * FROM first_admin_setup WHERE company_id='local' AND consumed_at IS NULL FOR UPDATE");
                Billing.Require(CryptographicOperations.FixedTimeEquals(Encoding.ASCII.GetBytes(setup.Text("token_hash")),Encoding.ASCII.GetBytes(Store.Hash(b.Text("setup_token")))) ,"The local first-run setup code is invalid.");
                Billing.Require((await Store.One(c,"SELECT count(*) AS count FROM app_user")).Integer("count")==0,"An Administrator is already enrolled.");var id=Guid.NewGuid().ToString("N");
                await Store.Exec(c,"INSERT INTO app_user(id,company_id,name,role,password_hash,active,email,username,access_role,account_status,work_areas) VALUES(@p0,'local',@p1,'None',@p2,true,@p3,@p4,'Administrator','Approved','[\"*\"]')",id,name,Store.Password(Accounts.Secret(b)),recoveryEmail,identity.Username);
                await Store.Exec(c,"UPDATE company SET name=@p0 WHERE id='local'",companyName);
                var profile=new JsonObject{["legal_name"]=companyName,["invoice_prefix"]="INV",["review_status"]="Draft",["period_start"]=b.Text("period_start"),["period_end"]=b.Text("period_end")};
                await Store.Exec(c,"INSERT INTO organization_profile(company_id,details,revision,updated_by) VALUES('local',@p0::jsonb,1,@p1) ON CONFLICT(company_id) DO UPDATE SET details=excluded.details,revision=organization_profile.revision+1,updated_by=excluded.updated_by",profile.ToJsonString(),id);
                await Store.Exec(c,"UPDATE first_admin_setup SET consumed_at=now() WHERE company_id='local'");await Store.Audit(c,"local",id,"First Administrator enrolled",id,new{accessRole="Administrator",localOnly=true});
                await Accounts.SignIn(h,await Store.One(c,"SELECT * FROM app_user WHERE id=@p0",id));return Results.Ok(new{message="Administrator created. Assign account roles, duties and work areas in User access."});
            });
        }).RequireRateLimiting("identity");
    }
}

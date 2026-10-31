using Sales360.Domain;
namespace Sales360.Api;
public static class OfflineBootstrap
{
    public static async Task Run(Store store,string password)
    {
        if(Environment.GetEnvironmentVariable("SALES360_MAIL_MODE")!="Offline")throw new InvalidOperationException("Local bootstrap is restricted to Offline mode.");
        Accounts.Password(password);
        await store.Transaction("local",async c=>{
            var exists=(await Store.One(c,"SELECT count(*) AS count FROM company")).Integer("count");if(exists>0)return 0;
            await Store.Exec(c,"INSERT INTO company(id,name) VALUES('local','My Company'); INSERT INTO numbering(company_id) VALUES('local')");
            await Store.Exec(c,"INSERT INTO app_user(id,company_id,name,role,password_hash,active,access_role,account_status) VALUES('administrator','local','Administrator','None',@p0,true,'Administrator','Approved')",Store.Password(password));
            await Store.Audit(c,"local","system","Offline company enrolled","local",new{administrator="administrator",externalServices=false});return 0;
        });
    }
}

using System.Text.Json.Nodes;
using System.Text.Json;
using Sales360.Domain;
namespace Sales360.Api;
public static class ProjectMaster
{
    public static void Map(RouteGroupBuilder api,Store store)
    {
        api.MapPost("/projects/{id}/master",async(HttpContext h,string id,JsonObject b)=>{
            if(!CustomerMaster.CanWrite(h))throw new UnauthorizedAccessException("A project-master duty is required.");return await store.Transaction(Accounts.Company(h),async c=>{
                var current=await Store.One(c,"SELECT * FROM project WHERE company_id=@p0 AND id=@p1 FOR UPDATE",Accounts.Company(h),id);Billing.Require(b.Integer("expected_version")==current.Integer("version"),"Project changed since you opened it. Reload before saving.");
                var name=b.Text("name");var category=b.Text("category");var location=b.Text("location");var fee=Billing.Money(b.Decimal("fee"));Billing.Require(name.Length is >=2 and <=400&&location.Length<=400&&Billing.Categories.Contains(category)&&fee>=0&&fee<=9999999999999999m,"Enter a project name, supported category and a nonnegative fee.");
                if(fee!=current.Decimal("fee")||category!=current.Text("category"))Billing.Require((await Store.One(c,"SELECT count(*) AS count FROM certificate WHERE company_id=@p0 AND project_id=@p1",Accounts.Company(h),id)).Integer("count")==0,"This project already has certificates. A fee/category variation needs a separate reviewed workflow; existing certificate schedules cannot be changed here.");
                var confirmed=b["confirm_contract_fee"]?.GetValue<bool>()==true;Billing.Require(!confirmed||fee>0,"A positive reviewed contract fee is required before enabling certificate billing.");var status=confirmed?"Active":"Needs contract review";
                var totals=await Store.One(c,"SELECT greatest(coalesce((SELECT sum(net) FROM invoice WHERE company_id=@p0 AND project_id=@p1),0)-coalesce((SELECT sum(f.net) FROM financial_correction f JOIN invoice i ON i.id=f.invoice_id WHERE i.company_id=@p0 AND i.project_id=@p1 AND f.kind='Credit note'),0),coalesce((SELECT max(cumulative) FROM certificate WHERE company_id=@p0 AND project_id=@p1 AND state='Approved'),0)) AS required",Accounts.Company(h),id);
                var required=totals.Decimal("required");var opening=new List<Stage>();var reference=b.Text("opening_review_reference");decimal openingNet=0;
                if(confirmed&&required>0){
                    Billing.Require(reference.Length is >=12 and <=200,"Record an opening billed-assessment review reference (12-200 characters).");var baseline=current["stages"]!.Deserialize<List<Stage>>()!;opening=b["opening_assessments"]?.Deserialize<List<Stage>>()??[];
                    Billing.Require(opening.Count==baseline.Count&&opening.Zip(baseline).All(pair=>pair.First.Name==pair.Second.Name&&pair.First.Allocation==pair.Second.Allocation&&pair.First.Assessed is >=0 and <=100),"Provide the reviewed previously billed completion percentage for every contract milestone.");
                    var approved=await Store.Rows(c,"SELECT stages FROM certificate WHERE company_id=@p0 AND project_id=@p1 AND state='Approved' ORDER BY cumulative DESC LIMIT 1",Accounts.Company(h),id);
                    if(approved.Count>0){var previous=approved[0]!["stages"]!.Deserialize<List<Stage>>()!;Billing.Require(opening.Zip(previous).All(pair=>pair.First.Assessed>=pair.Second.Assessed),"Opening review cannot reduce a previously approved milestone assessment.");}
                    openingNet=opening.Sum(stage=>Billing.Money(fee*stage.Allocation/100*stage.Assessed/100));Billing.Require(openingNet==required,"Reviewed opening assessments must equal the already billed/approved net amount: "+required.ToString("0.00")+". Cash collections do not reduce previously billed work.");opening=opening.Select(stage=>stage with{Claimed=stage.Assessed,Previous=0}).ToList();
                }
                await Store.Exec(c,"UPDATE project SET name=@p0,category=@p1,location=@p2,fee=@p3,status=@p4,version=version+1,opening_assessments=@p6::jsonb,opening_net=@p7,opening_review_reference=@p8 WHERE id=@p5",name,category,location,fee,status,id,JsonSerializer.Serialize(opening),openingNet,reference);var updated=await Store.One(c,"SELECT * FROM project WHERE id=@p0",id);await Store.Audit(c,Accounts.Company(h),Accounts.Actor(h),"Project master reviewed",id,new{before=current,after=updated,contractFeeConfirmed=confirmed});return updated;
            });
        });
    }
}

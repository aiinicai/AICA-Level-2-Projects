using System.Text.Json;
using System.Text.Json.Nodes;
using Npgsql;
using Sales360.Domain;
namespace Sales360.Api;
public static class Corrections
{
    public static string OpenSql(string alias,string date)=>$"{alias}.total-coalesce((SELECT sum(a.amount) FROM allocation a WHERE a.invoice_id={alias}.id AND a.effective_date<={date} AND NOT EXISTS(SELECT 1 FROM financial_correction ar WHERE ar.allocation_id=a.id AND ar.kind='Allocation reversal' AND ar.effective_date<={date})),0)-coalesce((SELECT sum(f.amount) FROM financial_correction f WHERE f.invoice_id={alias}.id AND f.kind IN ('Credit note','Write-off') AND f.effective_date<={date}),0)";
    public static string CashSql(string alias,string date)=>$"{alias}.amount-coalesce((SELECT sum(a.amount) FROM allocation a WHERE a.receipt_id={alias}.id AND a.effective_date<={date} AND NOT EXISTS(SELECT 1 FROM financial_correction ar WHERE ar.allocation_id=a.id AND ar.kind='Allocation reversal' AND ar.effective_date<={date})),0)-coalesce((SELECT sum(f.amount) FROM financial_correction f WHERE f.receipt_id={alias}.id AND f.kind IN ('Refund','Receipt reversal') AND f.effective_date<={date}),0)";
    public static async Task<JsonObject> Invoice(NpgsqlConnection c,string company,string id)=>await Store.One(c,$"SELECT i.*,({OpenSql("i","'9999-12-31'::date")}) AS open FROM invoice i WHERE company_id=@p0 AND id=@p1",company,id);
    public static async Task<JsonObject> Receipt(NpgsqlConnection c,string company,string id)=>await Store.One(c,$"SELECT r.*,({CashSql("r","'9999-12-31'::date")}) AS available FROM receipt r WHERE company_id=@p0 AND id=@p1",company,id);
    public static async Task EnsureChronology(NpgsqlConnection c,string company,string invoice,string receipt,DateOnly date)
    {
        var f=await Store.One(c,"SELECT coalesce(max(effective_date),'0001-01-01'::date) AS date FROM financial_correction WHERE company_id=@p0 AND (invoice_id=nullif(@p1,'') OR receipt_id=nullif(@p2,''))",company,invoice,receipt);
        Billing.Require(date>=DateOnly.Parse(f.Text("date")),"Date precedes a later correction. Use a date on or after the latest posted correction.");
    }
    public static void Map(RouteGroupBuilder api,Store store,Func<HttpContext,string> company,Func<HttpContext,string> actor,Action<HttpContext,string[]> role)
    {
        api.MapGet("/corrections",async(HttpContext h)=>{await using var c=await store.Open();return await Store.Rows(c,"SELECT f.*,c.name AS customer,i.reference AS invoice_reference,r.reference AS receipt_reference FROM financial_correction f JOIN customer c ON c.id=f.customer_id LEFT JOIN invoice i ON i.id=f.invoice_id LEFT JOIN receipt r ON r.id=f.receipt_id WHERE f.company_id=@p0 ORDER BY f.effective_date DESC,f.created_at DESC",company(h));});
        api.MapGet("/allocations",async(HttpContext h)=>{await using var c=await store.Open();return await Store.Rows(c,"SELECT a.*,i.reference AS invoice_reference,r.reference AS receipt_reference,EXISTS(SELECT 1 FROM financial_correction f WHERE f.allocation_id=a.id AND f.kind='Allocation reversal') AS reversed FROM allocation a JOIN invoice i ON i.id=a.invoice_id JOIN receipt r ON r.id=a.receipt_id WHERE a.company_id=@p0 ORDER BY a.effective_date DESC",company(h));});
        api.MapPost("/corrections",async(HttpContext h,JsonObject b)=>{role(h,["Finance Administrator"]);return await store.Transaction(company(h),async c=>{
            var kind=b.Text("kind");Billing.Require(new[]{"Credit note","Write-off","Refund","Receipt reversal","Allocation reversal"}.Contains(kind),"Choose a supported correction type.");
            var reason=b.Text("reason");Billing.Require(reason.Length is >=8 and <=1000,"Record a clear correction reason (8–1000 characters).");var key=b.Text("idempotency_key");Billing.Require(key.Length is >=8 and <=150,"A unique request key is required.");
            var date=b.Date("effective_date");var amount=kind is "Receipt reversal" or "Allocation reversal"?0:Billing.Money(b.Decimal("amount"));var invoice=b.Text("invoice_id");var receipt=b.Text("receipt_id");var allocation=b.Text("allocation_id");
            var hash=Store.Hash(JsonSerializer.Serialize(new{kind,reason,date,amount,invoice,receipt,allocation}));var prior=await Store.Rows(c,"SELECT * FROM financial_correction WHERE company_id=@p0 AND idempotency_key=@p1",company(h),key);if(prior.Count>0){Billing.Require(prior[0]!.Text("request_hash")==hash,"This request key belongs to different correction details.");return prior[0]!;}
            JsonObject source;string customer;decimal net=0,vat=0;
            if(kind is "Credit note" or "Write-off"){
                source=await Invoice(c,company(h),invoice);customer=source.Text("customer_id");receipt="";allocation="";Billing.Require(amount>0&&amount<=source.Decimal("open"),"Correction exceeds the invoice's current open balance. Reverse cash allocations first if necessary.");Billing.Require(date>=DateOnly.Parse(source.Text("issue_date")),"Correction cannot predate the invoice.");
                var latest=await Store.One(c,"SELECT coalesce(max(effective_date),'0001-01-01'::date) AS date FROM allocation WHERE invoice_id=@p0",invoice);Billing.Require(date>=DateOnly.Parse(latest.Text("date")),"Correction cannot predate an existing allocation.");
                if(kind=="Credit note"){net=Billing.Money(amount*source.Decimal("net")/source.Decimal("total"));vat=amount-net;var previous=await Store.One(c,"SELECT coalesce(sum(net),0) AS net,coalesce(sum(vat),0) AS vat FROM financial_correction WHERE invoice_id=@p0 AND kind='Credit note'",invoice);Billing.Require(net+previous.Decimal("net")<=source.Decimal("net")&&vat+previous.Decimal("vat")<=source.Decimal("vat"),"Credit exceeds the original net or VAT. Review final rounding.");}
            }else if(kind=="Allocation reversal"){
                source=await Store.One(c,"SELECT * FROM allocation WHERE company_id=@p0 AND id=@p1",company(h),allocation);customer=source.Text("customer_id");invoice=source.Text("invoice_id");receipt=source.Text("receipt_id");amount=source.Decimal("amount");Billing.Require(date>=DateOnly.Parse(source.Text("effective_date")),"Reversal cannot predate the allocation.");
            }else{
                source=await Receipt(c,company(h),receipt);customer=source.Text("customer_id");invoice="";allocation="";Billing.Require(date>=DateOnly.Parse(source.Text("receipt_date")),"Correction cannot predate the receipt.");
                Billing.Require((await Store.Rows(c,"SELECT id FROM financial_correction WHERE receipt_id=@p0 AND kind='Receipt reversal'",receipt)).Count==0,"This receipt has already been reversed.");
                if(kind=="Refund")Billing.Require(amount>0&&amount<=source.Decimal("available"),"Refund exceeds unapplied cash. Reverse allocations before recording a refund.");
                else {
                    Billing.Require((await Store.Rows(c,"SELECT id FROM financial_correction WHERE receipt_id=@p0 AND kind='Refund'",receipt)).Count==0,"A refunded receipt cannot be reversed. Use a reviewed adjustment.");amount=source.Decimal("amount");
                    var active=await Store.Rows(c,"SELECT a.* FROM allocation a WHERE a.receipt_id=@p0 AND NOT EXISTS(SELECT 1 FROM financial_correction f WHERE f.allocation_id=a.id AND f.kind='Allocation reversal')",receipt);
                    foreach(var a in active){Billing.Require(date>=DateOnly.Parse(a.Text("effective_date")),"Receipt reversal cannot predate its allocations.");await EnsureChronology(c,company(h),a.Text("invoice_id"),receipt,date);await Insert(c,company(h),actor(h),customer,"Allocation reversal",a.Text("invoice_id"),receipt,a.Text("id"),date,a.Decimal("amount"),0,0,reason,key+":"+a.Text("id"),hash);}
                }
            }
            await EnsureChronology(c,company(h),invoice,receipt,date);var id=await Insert(c,company(h),actor(h),customer,kind,invoice,receipt,allocation,date,amount,net,vat,reason,key,hash);
            await Store.Audit(c,company(h),actor(h),kind+" posted",id,new{invoice,receipt,allocation,amount,net,vat,date,reason});return await Store.One(c,"SELECT * FROM financial_correction WHERE id=@p0",id);
        });});
    }
    static async Task<string> Insert(NpgsqlConnection c,string company,string actor,string customer,string kind,string invoice,string receipt,string allocation,DateOnly date,decimal amount,decimal net,decimal vat,string reason,string key,string hash)
    {
        var id=Guid.NewGuid().ToString("N");var prefix=kind=="Credit note"?"CN":kind=="Write-off"?"WO":kind=="Refund"?"RF":kind=="Receipt reversal"?"RR":"AR";var reference=prefix+"/"+date.ToString("yyyyMMdd")+"/"+id[..12].ToUpperInvariant();
        await Store.Exec(c,"INSERT INTO financial_correction(id,company_id,customer_id,kind,invoice_id,receipt_id,allocation_id,reference,effective_date,amount,net,vat,reason,actor,idempotency_key,request_hash) VALUES(@p0,@p1,@p2,@p3,nullif(@p4,''),nullif(@p5,''),nullif(@p6,''),@p7,@p8,@p9,@p10,@p11,@p12,@p13,@p14,@p15)",id,company,customer,kind,invoice,receipt,allocation,reference,date,amount,net,vat,reason,actor,key,hash);return id;
    }
}

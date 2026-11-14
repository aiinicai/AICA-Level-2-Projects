using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using System.Globalization;
using Npgsql;
using ClosedXML.Excel;
using Sales360.Domain;
namespace Sales360.Api;

public static class Vat
{
    public const string Portal="https://eservices.tax.gov.ae/#/Logon";
    public static readonly string[] Emirates=["Abu Dhabi","Dubai","Sharjah","Ajman","Umm Al Quwain","Ras Al Khaimah","Fujairah"];
    public static readonly string[] Treatments=["Standard rated","Zero rated","Exempt","Out of scope"];
    static readonly Dictionary<int,string> Labels=new(){[1]="Standard-rated supplies",[2]="Tax refunds to tourists",[3]="Reverse-charge outputs",[4]="Zero-rated supplies",[5]="Exempt supplies",[6]="Goods imported into UAE",[7]="Adjustments to imported goods",[8]="Total outputs",[9]="Standard-rated expenses (recoverable portion)",[10]="Reverse-charge inputs (recoverable portion)",[11]="Total inputs",[12]="Total tax due",[13]="Total recoverable tax",[14]="Payable / (recoverable) tax"};
    static DateOnly Today()=>DateOnly.FromDateTime(TimeZoneInfo.ConvertTimeBySystemTimeZoneId(DateTime.UtcNow,"Arabian Standard Time"));
    static void Role(HttpContext h,params string[] roles){if(!h.User.IsInRole("Administrator")&&!roles.Any(h.User.IsInRole))throw new UnauthorizedAccessException("Your assigned duty cannot perform this VAT action.");}
    static void Write(HttpContext h)=>Role(h,"Finance Administrator","Accountant");
    static void Approve(HttpContext h)=>Role(h,"Finance Administrator");
    static bool Yes(JsonNode n,string key)=>n[key] is JsonValue value&&value.TryGetValue<bool>(out var b)&&b;
    static decimal Num(JsonNode n,string key)=>Billing.Money(n.Decimal(key));
    static string Fingerprint(JsonNode n){JsonNode? Sort(JsonNode? v)=>v switch {JsonObject o=>new JsonObject(o.OrderBy(x=>x.Key,StringComparer.Ordinal).Select(x=>new KeyValuePair<string,JsonNode?>(x.Key,Sort(x.Value)))),JsonArray a=>new JsonArray(a.Select(Sort).ToArray()),_=>v?.DeepClone()};return Store.Hash(Sort(n)!.ToJsonString());}
    static void Dates(DateOnly first,DateOnly last)=>Billing.Require(first<=last&&last.DayNumber-first.DayNumber<=366,"Use the FTA-assigned period, up to 366 days.");
    static JsonObject SnapshotCustomer(JsonNode row){var details=row["details"]!;return new(){["name"]=row.Text("name"),["address"]=details.Text("registered_address"),["trn"]=row.Text("trn")};}
    public static async Task<JsonObject> ReviewInvoice(NpgsqlConnection c,string company,string actor,string id,JsonObject b)
    {
        var i=await Store.One(c,"SELECT * FROM invoice WHERE company_id=@p0 AND id=@p1",company,id);
        var old=(await Store.Rows(c,"SELECT * FROM vat_invoice_review WHERE company_id=@p0 AND invoice_id=@p1",company,id)).FirstOrDefault();
        Billing.Require(b.Integer("expected_revision")== (old?.Integer("revision")??0),"VAT details changed. Reload before saving.");
        var point=b.Date("tax_point");var supply=b.Date("supply_date");var issue=i.Date("issue_date");
        Billing.Require(point<=issue&&point<=supply,"Tax point must be no later than invoice or supply date; review earlier payments and continuous-supply rules.");
        Billing.Require(Yes(b,"confirm_tax_point"),"Confirm the earliest applicable tax point, including advance payments and continuous supplies.");
        var type=b.Text("treatment");Billing.Require(Treatments.Contains(type),"Choose a VAT treatment.");
        Billing.Require(type=="Standard rated"?i.Decimal("vat")==Billing.Money(i.Decimal("net")*.05m):i.Decimal("vat")==0,"Treatment disagrees with the posted VAT. Use a reviewed credit/reissue; posted invoice money cannot be changed.");
        Billing.Require(type!="Standard rated"||Emirates.Contains(b.Text("emirate")),"Select the supplier establishment Emirate for Box 1; do not infer it from the customer's address.");
        Billing.Require(b.Text("description").Length is >=3 and <=1000&&b.Text("reason").Length is >=12 and <=2000,"Enter the supply description and a treatment/tax-point evidence reference (12–2000 characters).");
        Billing.Require((await Store.Rows(c,"SELECT id FROM vat_return WHERE company_id=@p0 AND status='Filed' AND ((@p1 BETWEEN period_start AND period_end) OR (@p2 BETWEEN period_start AND period_end))",company,point,old==null?point:old.Date("tax_point"))).Count==0,"These VAT details affect a filed period. Reconcile through the appropriate FTA correction process; the filed snapshot cannot be rewritten.");
        var customer=await Store.One(c,"SELECT * FROM customer WHERE company_id=@p0 AND id=@p1",company,i.Text("customer_id"));
        var supplier=old?["supplier_snapshot"]?.DeepClone()??i["organization_snapshot"]!.DeepClone();
        // Legacy/imported invoices may lack an issuer snapshot; capture the reviewed company profile once.
        if(supplier.Text("trn")=="")supplier=await Organization.Snapshot(c,company);
        var buyer=old?["customer_snapshot"]?.DeepClone()??SnapshotCustomer(customer);
        Billing.Require(supplier.Text("legal_name").Length>1&&supplier.Text("registered_address").Length>2&&Regex.IsMatch(supplier.Text("trn"),"^[0-9]{15}$"),"Complete and review the company legal name, address and 15-digit TRN first.");
        Billing.Require(buyer.Text("name").Length>1&&buyer.Text("address").Length>2&&(buyer.Text("trn")==""||Regex.IsMatch(buyer.Text("trn"),"^[0-9]{15}$")),"Complete the customer's legal name, address and valid TRN where registered before VAT review.");
        await Store.Exec(c,"INSERT INTO vat_invoice_review(invoice_id,company_id,tax_point,supply_date,treatment,emirate,description,reason,customer_snapshot,supplier_snapshot,reviewed_by) VALUES(@p0,@p1,@p2,@p3,@p4,@p5,@p6,@p7,@p8::jsonb,@p9::jsonb,@p10) ON CONFLICT(invoice_id) DO UPDATE SET tax_point=excluded.tax_point,supply_date=excluded.supply_date,treatment=excluded.treatment,emirate=excluded.emirate,description=excluded.description,reason=excluded.reason,revision=vat_invoice_review.revision+1,reviewed_by=excluded.reviewed_by,reviewed_at=now()",id,company,point,supply,type,b.Text("emirate"),b.Text("description"),b.Text("reason"),buyer.ToJsonString(),supplier.ToJsonString(),actor);
        await Store.Audit(c,company,actor,"Invoice VAT classification reviewed",id,b);return await Store.One(c,"SELECT * FROM vat_invoice_review WHERE invoice_id=@p0",id);
    }
    public static Task<JsonArray> Register(NpgsqlConnection c,string company,DateOnly first,DateOnly last)=>Store.Rows(c,"SELECT i.id,i.reference,i.issue_date,i.net,i.vat,i.total,i.customer_id,cu.name AS customer,p.code AS job,coalesce(v.tax_point,i.issue_date) AS tax_point,v.supply_date,coalesce(v.treatment,'Unreviewed') AS treatment,coalesce(v.emirate,'Unassigned') AS emirate,coalesce(v.revision,0) AS revision,coalesce(v.description,i.category) AS description,v.reason,v.customer_snapshot,v.supplier_snapshot FROM invoice i JOIN customer cu ON cu.id=i.customer_id JOIN project p ON p.id=i.project_id LEFT JOIN vat_invoice_review v ON v.invoice_id=i.id WHERE i.company_id=@p0 AND coalesce(v.tax_point,i.issue_date) BETWEEN @p1 AND @p2 ORDER BY coalesce(v.tax_point,i.issue_date),i.reference",company,first,last);
    public static async Task<JsonObject> Compute(NpgsqlConnection c,string company,JsonNode period)
    {
        var first=period.Date("period_start");var last=period.Date("period_end");var lines=await Register(c,company,first,last);var issues=new JsonArray();var warnings=new JsonArray();
        var boxes=new Dictionary<string,JsonObject>();
        JsonObject Box(int box,string emirate=""){var key=box+":"+emirate;if(!boxes.TryGetValue(key,out var value)){value=new(){["box"]=box,["label"]=Labels[box],["emirate"]=emirate,["amount"]=0m,["vat"]=0m,["adjustment"]=0m};boxes.Add(key,value);}return value;}
        void Add(int number,string emirate,decimal amount,decimal vat,decimal adjustment=0){var row=Box(number,emirate);row["amount"]=row.Decimal("amount")+amount;row["vat"]=row.Decimal("vat")+vat;row["adjustment"]=row.Decimal("adjustment")+adjustment;}
        foreach(var emirate in Emirates)Box(1,emirate);foreach(var number in new[]{2,3,4,5,6,7,9,10})Box(number);
        foreach(var line in lines){var type=line!.Text("treatment");if(type=="Unreviewed"){issues.Add(line.Text("reference")+": VAT tax point, treatment, establishment and invoice details require review.");type=line.Decimal("vat")>0?"Standard rated":"Unreviewed";}
            if(type=="Standard rated")Add(1,line.Text("emirate"),line.Decimal("net"),line.Decimal("vat"));else if(type=="Zero rated")Add(4,"",line.Decimal("net"),0);else if(type=="Exempt")Add(5,"",line.Decimal("net"),0);
            if(line.Text("supply_date")!=""&&line!.Date("issue_date").DayNumber-line!.Date("tax_point").DayNumber>14)warnings.Add(line.Text("reference")+": invoice issued more than 14 days after tax point. Review the applicable deadline/exception and any correction obligations.");
        }
        var credits=await Store.Rows(c,"SELECT f.id,f.reference,f.invoice_id,f.effective_date,f.net,f.vat,coalesce(v.treatment,'Unreviewed') AS treatment,coalesce(v.emirate,'Unassigned') AS emirate FROM financial_correction f LEFT JOIN vat_invoice_review v ON v.invoice_id=f.invoice_id WHERE f.company_id=@p0 AND f.kind='Credit note' AND f.effective_date BETWEEN @p1 AND @p2 ORDER BY f.effective_date,f.reference",company,first,last);
        foreach(var cr in credits){var type=cr!.Text("treatment");if(type=="Unreviewed")issues.Add(cr.Text("reference")+": classify the original invoice for this credit note.");var box=type=="Zero rated"?4:type=="Exempt"?5:type=="Out of scope"?0:1;if(box>0)Add(box,box==1?cr.Text("emirate"):"",-cr.Decimal("net"),-cr.Decimal("vat"));}
        var entries=period["entries"]?.AsArray()??new JsonArray();foreach(var entry in entries){var number=entry!.Integer("box");var factor=number==2?-1:1;Add(number,number==1?entry.Text("emirate"):"",factor*entry.Decimal("amount"),factor*entry.Decimal("vat"),entry.Decimal("adjustment"));}
        decimal Sum(IEnumerable<JsonObject> rows,string key)=>rows.Sum(x=>x.Decimal(key));
        var output=boxes.Values.Where(x=>x.Integer("box")<=7).ToArray();var inputs=boxes.Values.Where(x=>x.Integer("box") is 9 or 10).ToArray();
        Add(8,"",Sum(output,"amount"),Sum(output,"vat"),Sum(output,"adjustment"));Add(11,"",Sum(inputs,"amount"),Sum(inputs,"vat"),Sum(inputs,"adjustment"));
        var due=Billing.Money(Sum(output,"vat")+Sum(output,"adjustment"));var recoverable=Billing.Money(Sum(inputs,"vat")+Sum(inputs,"adjustment"));Add(12,"",0,due);Add(13,"",0,recoverable);Add(14,"",0,due-recoverable);
        var organization=await Organization.Snapshot(c,company);if(!Regex.IsMatch(organization.Text("trn"),"^[0-9]{15}$"))issues.Add("Company VAT TRN must contain 15 digits.");if(organization.Text("registered_address").Length<3)issues.Add("Company registered address is required.");
        var snapshot=new JsonObject{["period_start"]=first.ToString("yyyy-MM-dd"),["period_end"]=last.ToString("yyyy-MM-dd"),["due_date"]=period.Text("due_date"),["deadline_reference"]=period.Text("deadline_reference"),["organization"]=organization,["boxes"]=new JsonArray(boxes.Values.OrderBy(x=>x.Integer("box")).ThenBy(x=>x.Text("emirate")).Select(x=>(JsonNode)x).ToArray()),["invoices"]=lines,["credits"]=credits,["entries"]=entries.DeepClone(),["issues"]=issues,["warnings"]=warnings,["output_tax"]=due,["recoverable_tax"]=recoverable,["net_tax"]=Billing.Money(due-recoverable),["basis"]="Issued final invoices by reviewed tax point, credit notes by effective date and evidenced manual VAT201 entries. Drafts, cash allocations and write-offs do not change VAT. Input recovery is reviewed, not assumed. AED."};
        snapshot["source_hash"]=Fingerprint(snapshot);return snapshot;
    }
    static JsonArray ValidateEntries(JsonNode? supplied)
    {
        var result=new JsonArray();if(supplied==null)return result;Billing.Require(supplied is JsonArray&&supplied!.AsArray().Count<=500,"Use up to 500 evidenced VAT entries.");
        foreach(var entry in supplied!.AsArray()){
            var e=entry!;var box=e.Integer("box");Billing.Require(new[]{1,2,3,4,5,6,7,9,10}.Contains(box),"Only detail VAT201 boxes can have manual entries.");
            var amount=Num(e,"amount");var vat=Num(e,"vat");var adj=Num(e,"adjustment");Billing.Require(new[]{amount,vat,adj}.All(x=>Math.Abs(x)<=999999999999m),"VAT entry amount is too large.");
            Billing.Require(box is 1 or 7||amount>=0&&vat>=0,"Use nonnegative purchases/refunds/import amounts; signed corrections belong in the adjustment column with evidence.");
            if(box is 1 or 3 or 6)Billing.Require(vat==Billing.Money(amount*.05m),"Standard-rated/reverse-charge output tax must equal 5% of the taxable amount.");
            if(box is 4 or 5)Billing.Require(vat==0&&adj==0,"Zero-rated and exempt boxes carry no VAT.");
            if(box is 9 or 10)Billing.Require(vat<=Billing.Money(amount*.05m),"Recoverable input tax cannot exceed 5% of the taxable cost; enter only the eligible portion.");
            Billing.Require(box!=1||Emirates.Contains(e.Text("emirate")),"Box 1 requires the supplier's establishment Emirate.");
            Billing.Require(e.Text("reference").Length is >=3 and <=200&&e.Text("reason").Length is >=12 and <=2000,"Every manual entry needs a unique document reference and recovery/treatment evidence (12–2000 characters).");
            Billing.Require(!result.Any(x=>x.Text("reference")==e.Text("reference")),"Duplicate manual VAT entry reference.");
            result.Add(new JsonObject{["box"]=box,["emirate"]=box==1?e.Text("emirate"):"",["amount"]=amount,["vat"]=vat,["adjustment"]=adj,["reference"]=e.Text("reference"),["reason"]=e.Text("reason")});
        }return result;
    }
    public static async Task<JsonObject> FiledReport(NpgsqlConnection c,string company,string start,string end)
    {
        var rows=await Store.Rows(c,"SELECT id,period_start,period_end,filing_date,filing_reference,(snapshot->>'output_tax')::numeric AS output_tax,(snapshot->>'recoverable_tax')::numeric AS recoverable_tax,(snapshot->>'net_tax')::numeric AS net_tax FROM vat_return WHERE company_id=@p0 AND status='Filed' AND period_end BETWEEN @p1 AND @p2 ORDER BY period_end",company,DateOnly.Parse(start),DateOnly.Parse(end));
        foreach(var row in rows){var saved=await Store.One(c,"SELECT * FROM vat_return WHERE company_id=@p0 AND id=@p1",company,row!.Text("id"));var current=await Compute(c,company,saved);row!["post_filing_changes"]=current.Text("source_hash")!=saved.Text("source_hash");}
        var life=await Store.One(c,"SELECT coalesce(sum((snapshot->>'net_tax')::numeric),0) AS total FROM vat_return WHERE company_id=@p0 AND status='Filed'",company);
        var organization=await Organization.Snapshot(c,company);return new(){["kind"]="vat-returns-filed",["company"]=organization.Text("legal_name"),["start"]=start,["end"]=end,["currency"]="AED",["basis"]="Filed local records whose period-end falls in the selected range. Amounts are the frozen filed working paper, not live recomputations or tax payments. Post-filing changes require reconciliation; total also shown for all recorded periods.",["generated_at"]=DateTimeOffset.UtcNow.ToString("O"),["rows"]=rows,["row_count"]=rows.Count,["totals"]=new JsonObject{["output_tax"]=rows.Sum(x=>x.Decimal("output_tax")),["recoverable_tax"]=rows.Sum(x=>x.Decimal("recoverable_tax")),["net_tax"]=rows.Sum(x=>x.Decimal("net_tax")),["all_periods_net_tax"]=life.Decimal("total")}};
    }
    public static void Map(RouteGroupBuilder api,Store store,string root,string data)
    {
        api.MapGet("/vat/catalog",()=>new{emirates=Emirates,treatments=Treatments,boxes=Labels,portal=Portal,rulesChecked="2026-10-29"});
        api.MapGet("/vat/invoices",async(HttpContext h,string start,string end)=>{Dates(DateOnly.Parse(start),DateOnly.Parse(end));await using var c=await store.Open();return await Register(c,Accounts.Company(h),DateOnly.Parse(start),DateOnly.Parse(end));});
        api.MapPost("/vat/invoices/{id}/review",async(HttpContext h,string id,JsonObject b)=>{Write(h);return await store.Transaction(Accounts.Company(h),c=>ReviewInvoice(c,Accounts.Company(h),Accounts.Actor(h),id,b));});
        api.MapGet("/vat/invoices/{id}/pdf",async(HttpContext h,string id)=>{await using var c=await store.Open();var i=await Store.One(c,"SELECT i.*,v.tax_point,v.supply_date,v.treatment,v.description,v.customer_snapshot,v.supplier_snapshot FROM invoice i JOIN vat_invoice_review v ON v.invoice_id=i.id WHERE i.company_id=@p0 AND i.id=@p1",Accounts.Company(h),id);Billing.Require(i.Text("treatment") is "Standard rated" or "Zero rated","Tax invoices are available for reviewed taxable supplies only. Exempt/out-of-scope entries require a commercial document.");return Results.File(await Documents.Generate(root,data,"tax-invoice",i),"application/pdf",i.Text("reference").Replace('/','-')+"-Tax-Invoice.pdf");});
        api.MapGet("/vat/returns",async(HttpContext h)=>{await using var c=await store.Open();return await Store.Rows(c,"SELECT id,period_start,period_end,due_date,status,version,review_reference,filing_date,filing_reference FROM vat_return WHERE company_id=@p0 ORDER BY period_end DESC",Accounts.Company(h));});
        api.MapPost("/vat/returns",async(HttpContext h,JsonObject b)=>{Write(h);return await store.Transaction(Accounts.Company(h),async c=>{var first=b.Date("period_start");var last=b.Date("period_end");Dates(first,last);Billing.Require((await Store.Rows(c,"SELECT id FROM vat_return WHERE company_id=@p0 AND period_start<=@p2 AND period_end>=@p1",Accounts.Company(h),first,last)).Count==0,"This period overlaps an existing VAT working paper.");var id=Guid.NewGuid().ToString("N");await Store.Exec(c,"INSERT INTO vat_return(id,company_id,period_start,period_end,due_date) VALUES(@p0,@p1,@p2,@p3,@p4)",id,Accounts.Company(h),first,last,last.AddDays(28));await Store.Audit(c,Accounts.Company(h),Accounts.Actor(h),"VAT period created",id,b);return new{id};});});
        api.MapGet("/vat/returns/{id}",async(HttpContext h,string id)=>{await using var c=await store.Open();await using var tx=await c.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead);var p=await Store.One(c,"SELECT * FROM vat_return WHERE company_id=@p0 AND id=@p1",Accounts.Company(h),id);var current=await Compute(c,Accounts.Company(h),p);p["current"]=current;p["changed_since_review"]=p.Text("source_hash")!=""&&p.Text("source_hash")!=current.Text("source_hash");await tx.CommitAsync();return p;});
        api.MapPost("/vat/returns/{id}/{action}",async(HttpContext h,string id,string action,JsonObject b)=>{
            if(action is "review" or "file")Approve(h);else Write(h);
            return await store.Transaction(Accounts.Company(h),async c=>{
                var p=await Store.One(c,"SELECT * FROM vat_return WHERE company_id=@p0 AND id=@p1 FOR UPDATE",Accounts.Company(h),id);Billing.Require(p.Text("status")!="Filed","Filed working papers are immutable; retain them and use the appropriate FTA correction process.");Billing.Require(b.Integer("expected_version")==p.Integer("version"),"The VAT working paper changed. Reload it before saving.");
                if(action=="save"){
                    var entries=ValidateEntries(b["entries"]);var due=b.Date("due_date");Billing.Require(due>p.Date("period_end"),"Filing due date must follow the period end.");if(due!=p.Date("period_end").AddDays(28))Billing.Require(b.Text("deadline_reference").Length is >=12 and <=500,"Record the FTA deadline/holiday evidence for an adjusted due date.");
                    await Store.Exec(c,"UPDATE vat_return SET entries=@p0::jsonb,due_date=@p1,deadline_reference=@p2,status='Draft',snapshot=NULL,source_hash='',review_reference='',version=version+1 WHERE id=@p3",entries.ToJsonString(),due,b.Text("deadline_reference"),id);
                }else if(action=="reopen")await Store.Exec(c,"UPDATE vat_return SET status='Draft',snapshot=NULL,source_hash='',version=version+1 WHERE id=@p0",id);
                else if(action is "review" or "file"){
                    var current=await Compute(c,Accounts.Company(h),p);Billing.Require(current["issues"]!.AsArray().Count==0,"Resolve every VAT classification/company issue before review or filing.");
                    if(action=="review"){
                        Billing.Require(b.Text("review_reference").Length is >=12 and <=2000&&Yes(b,"confirm_complete")&&Yes(b,"confirm_input_eligibility")&&Yes(b,"confirm_warnings"),"Record a review reference and confirm all supplies/advances/imports, input eligibility and warnings have been reconciled.");
                        await Store.Exec(c,"UPDATE vat_return SET status='Reviewed',snapshot=@p0::jsonb,source_hash=@p1,review_reference=@p2,reviewed_by=@p3,reviewed_at=now(),version=version+1 WHERE id=@p4",current.ToJsonString(),current.Text("source_hash"),b.Text("review_reference"),Accounts.Actor(h),id);
                    }else{
                        Billing.Require(p.Text("status")=="Reviewed"&&p.Text("source_hash")==current.Text("source_hash"),"Review the current source data again before recording a filing; invoices or adjustments changed.");var date=b.Date("filing_date");Billing.Require(date>p.Date("period_end")&&date<=Today(),"Record the actual filing date after the closed period and not in the future.");
                        Billing.Require(Yes(b,"confirm_submitted")&&b.Text("filing_reference").Length is >=5 and <=200&&b.Text("filing_evidence").Length is >=12 and <=2000,"Submit in EmaraTax yourself, then record the actual acknowledgement reference and evidence. Opening the portal does not submit a return.");
                        await Store.Exec(c,"UPDATE vat_return SET status='Filed',filing_date=@p0,filing_reference=@p1,filing_evidence=@p2,filed_by=@p3,version=version+1 WHERE id=@p4",date,b.Text("filing_reference"),b.Text("filing_evidence"),Accounts.Actor(h),id);
                    }
                }else throw new RuleException("Choose save, reopen, review or file.");
                await Store.Audit(c,Accounts.Company(h),Accounts.Actor(h),"VAT return "+action,id,b);return await Store.One(c,"SELECT * FROM vat_return WHERE id=@p0",id);
            });
        });
        api.MapGet("/vat/returns/{id}/export",async(HttpContext h,string id,string format)=>{
            Billing.Require(format is "xlsx" or "pdf","Choose Excel or PDF.");await using var c=await store.Open();await using var tx=await c.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead);var p=await Store.One(c,"SELECT * FROM vat_return WHERE company_id=@p0 AND id=@p1",Accounts.Company(h),id);var current=await Compute(c,Accounts.Company(h),p);var s=p.Text("status")=="Filed"?p["snapshot"]!:current;
            var report=new JsonObject{["kind"]="vat-working-paper",["company"]=s["organization"]!.Text("legal_name"),["start"]=p.Text("period_start"),["end"]=p.Text("period_end"),["basis"]=s.Text("basis")+" Status: "+p.Text("status")+". "+(p.Text("status")=="Filed"?"Filed snapshot; acknowledgement "+p.Text("filing_reference")+". ":"")+"Preparation record, not an FTA portal submission or e-invoice transmission.",["generated_at"]=DateTimeOffset.UtcNow.ToString("O"),["rows"]=s["boxes"]!.DeepClone(),["row_count"]=s["boxes"]!.AsArray().Count,["totals"]=new JsonObject{["output_tax"]=s.Decimal("output_tax"),["recoverable_tax"]=s.Decimal("recoverable_tax"),["net_tax"]=s.Decimal("net_tax")}};await tx.CommitAsync();
            if(format=="pdf")return Results.File(await Documents.Generate(root,data,"analytics",report),"application/pdf","VAT-working-paper.pdf");
            using var book=new XLWorkbook();void Sheet(string name,JsonArray rows){var sheet=book.AddWorksheet(name);if(rows.Count==0){sheet.Cell(1,1).Value="No records";return;}var keys=rows[0]!.AsObject().Select(x=>x.Key).Where(k=>!rows.Any(r=>r![k] is JsonObject or JsonArray)).ToArray();for(var k=0;k<keys.Length;k++)sheet.Cell(1,k+1).Value=keys[k];for(var r=0;r<rows.Count;r++)for(var k=0;k<keys.Length;k++){var value=rows[r]![keys[k]];if(value is JsonValue v&&v.TryGetValue<decimal>(out var number))sheet.Cell(r+2,k+1).Value=number;else sheet.Cell(r+2,k+1).Value=value?.ToString()??"";}sheet.Row(1).Style.Font.Bold=true;sheet.SheetView.FreezeRows(1);sheet.Columns().Width=22;}
            Sheet("VAT201 boxes",s["boxes"]!.AsArray());Sheet("Final invoice register",s["invoices"]!.AsArray());Sheet("Credit notes",s["credits"]!.AsArray());Sheet("Reviewed entries",s["entries"]!.AsArray());Sheet("Basis",new JsonArray(report.DeepClone()));using var stream=new MemoryStream();book.SaveAs(stream);return Results.File(stream.ToArray(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","VAT-working-paper.xlsx");
        });
    }
}

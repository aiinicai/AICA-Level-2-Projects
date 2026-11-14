using System.Text.Json.Nodes;
using ClosedXML.Excel;
using Npgsql;
using Sales360.Domain;
namespace Sales360.Api;

public static class Analytics
{
    public static readonly string[] Kinds=["receivables","customer-outstanding","project-outstanding","customer-collections","project-collections","receivable-movement","invoiced-sales","cash-receipts","adjustments","vat-returns-filed"];
    static decimal Sum(IEnumerable<JsonNode?> rows,string key)=>rows.Sum(r=>r.Decimal(key));
    static JsonArray Group(JsonArray rows,string key,string label,string value)
    {
        var result=new JsonArray();foreach(var g in rows.GroupBy(r=>r!.Text(key)))result.Add(new JsonObject{[key]=g.Key,[label]=g.First()!.Text(label),[value]=Sum(g,value),["records"]=g.Count()});return result;
    }
    public static async Task<JsonObject> Build(NpgsqlConnection c,string company,string kind,string start,string end,string? customerId,string? projectId)
    {
        Billing.Require(Kinds.Contains(kind),"Choose a supported report.");var first=DateOnly.ParseExact(start,"yyyy-MM-dd");var last=DateOnly.ParseExact(end,"yyyy-MM-dd");
        Billing.Require(first<=last&&first> DateOnly.MinValue&&last.DayNumber-first.DayNumber<=36600,"Choose a valid period of at most 100 years.");
        if(kind=="vat-returns-filed"){Billing.Require(string.IsNullOrEmpty(customerId)&&string.IsNullOrEmpty(projectId),"VAT returns are company-wide. Clear customer and project filters.");return await Vat.FiledReport(c,company,start,end);}
        var before=first.AddDays(-1);var invoices=await Reports.Invoices(c,company,end);
        bool Match(JsonNode? r)=>(string.IsNullOrEmpty(customerId)||r!.Text("customer_id")==customerId)&&(string.IsNullOrEmpty(projectId)||r!.Text("project_id")==projectId);
        var selected=invoices.Where(Match).ToArray();var detail=new JsonArray();
        foreach(var i in selected)detail.Add(new JsonObject{["reference"]=i!.Text("reference"),["customer_id"]=i.Text("customer_id"),["customer"]=i.Text("customer"),["project_id"]=i.Text("project_id"),["project"]=i.Text("project"),["job"]=i.Text("job"),["issue_date"]=i.Text("issue_date"),["due_date"]=i.Text("due_date"),["invoiced"]=i.Decimal("total"),["balance"]=i.Decimal("balance"),["aging"]=new[]{"Current","1–30 days","31–60 days","61–90 days","91+ days"}[i!.Integer("aging_bucket")]});
        var cash=await Store.Rows(c,"SELECT m.*,cu.name AS customer,r.reference FROM cash_movement m JOIN customer cu ON cu.id=m.customer_id LEFT JOIN receipt r ON r.id=m.id WHERE m.company_id=@p0 AND m.date BETWEEN @p1 AND @p2 ORDER BY m.date,m.id",company,first,last);
        var cashSelected=new JsonArray();foreach(var r in cash.Where(r=>string.IsNullOrEmpty(customerId)||r!.Text("customer_id")==customerId))cashSelected.Add(r!.DeepClone());
        // Project attribution follows allocation effective dates; cash not yet allocated has no project.
        var allocated=await Store.Rows(c,"SELECT a.id,a.customer_id,i.project_id,cu.name AS customer,p.name AS project,p.code AS job,r.reference,a.effective_date AS date,a.amount FROM allocation a JOIN invoice i ON i.id=a.invoice_id JOIN project p ON p.id=i.project_id JOIN customer cu ON cu.id=a.customer_id JOIN receipt r ON r.id=a.receipt_id WHERE a.company_id=@p0 AND a.effective_date BETWEEN @p1 AND @p2 UNION ALL SELECT f.id,f.customer_id,i.project_id,cu.name,p.name,p.code,r.reference,f.effective_date,-a.amount FROM financial_correction f JOIN allocation a ON a.id=f.allocation_id JOIN invoice i ON i.id=a.invoice_id JOIN project p ON p.id=i.project_id JOIN customer cu ON cu.id=a.customer_id JOIN receipt r ON r.id=a.receipt_id WHERE f.company_id=@p0 AND f.kind='Allocation reversal' AND f.effective_date BETWEEN @p1 AND @p2 ORDER BY date,id",company,first,last);
        var projectCash=new JsonArray();foreach(var r in allocated.Where(Match))projectCash.Add(r!.DeepClone());
        JsonArray rows;string basis;
        switch(kind){
            case "receivables":rows=new JsonArray(detail.Where(r=>r.Decimal("balance")!=0).Select(r=>r!.DeepClone()).ToArray());basis="Invoice open balances and due-date ageing as of period end, including invoices before period start; gross AED including VAT.";break;
            case "customer-outstanding":case "project-outstanding":{
                var key=kind=="customer-outstanding"?"customer":"project";rows=Group(detail,key+"_id",key,"balance");basis="Outstanding invoice balances as of period end; unapplied customer cash is reported separately, not subtracted from projects.";break;}
            case "customer-collections":rows=Group(cashSelected,"customer_id","customer","amount");basis="Actual customer cash by receipt/refund/reversal date within the selected period; includes unapplied cash. Project filter is unavailable for this report.";Billing.Require(string.IsNullOrEmpty(projectId),"Use project collections for a project filter.");break;
            case "project-collections":rows=Group(projectCash,"project_id","project","amount");basis="Cash allocated to projects by allocation effective date, net of allocation reversals in this period. Unapplied cash has no project; this differs from receipt-date collections.";break;
            case "cash-receipts":Billing.Require(string.IsNullOrEmpty(projectId),"Cash receipts have no project until allocated; use project collections.");rows=cashSelected;basis="Cash movements within the period, including negative refunds/reversals. Includes unapplied cash.";break;
            case "invoiced-sales":{
                var sales=await Store.Rows(c,"SELECT s.*,cu.name AS customer,p.name AS project,p.code AS job FROM sales_movement s JOIN customer cu ON cu.id=s.customer_id JOIN project p ON p.id=s.project_id WHERE s.company_id=@p0 AND s.date BETWEEN @p1 AND @p2 ORDER BY s.date,p.code",company,first,last);
                rows=new JsonArray(sales.Where(Match).Select(r=>r!.DeepClone()).ToArray());basis="Posted net sales, VAT and gross invoice movements, net of credit notes by effective date; write-offs are not sales credits.";break;}
            case "adjustments":{
                var adjustments=await Store.Rows(c,"SELECT f.reference,f.customer_id,i.project_id,cu.name AS customer,p.name AS project,f.kind,f.effective_date,f.amount,f.reason FROM financial_correction f JOIN customer cu ON cu.id=f.customer_id LEFT JOIN invoice i ON i.id=f.invoice_id LEFT JOIN project p ON p.id=i.project_id WHERE f.company_id=@p0 AND f.effective_date BETWEEN @p1 AND @p2 ORDER BY f.effective_date,f.reference",company,first,last);rows=new JsonArray(adjustments.Where(Match).Select(r=>r!.DeepClone()).ToArray());basis="Posted financial corrections within the period; review kind before summing amounts.";break;}
            default:{
                var opening=(await Reports.Invoices(c,company,before.ToString("yyyy-MM-dd"))).Where(Match).Sum(r=>r.Decimal("balance"));
                var billed=selected.Where(r=>DateOnly.Parse(r!.Text("issue_date"))>=first).Sum(r=>r.Decimal("total"));
                var corrections=await Store.Rows(c,"SELECT f.*,i.project_id FROM financial_correction f JOIN invoice i ON i.id=f.invoice_id WHERE f.company_id=@p0 AND f.kind IN ('Credit note','Write-off') AND f.effective_date BETWEEN @p1 AND @p2",company,first,last);
                var credits=Sum(corrections.Where(Match),"amount");var applied=Sum(projectCash,"amount");var closing=Sum(detail,"balance");
                rows=new JsonArray(new JsonObject{["opening_receivables"]=opening,["gross_invoiced"]=billed,["credits_writeoffs"]=credits,["net_allocations"]=applied,["closing_receivables"]=closing,["reconciliation_difference"]=Billing.Money(opening+billed-credits-applied-closing)});basis="Opening AR + gross invoices − credit notes/write-offs − net cash allocations = closing AR. Receipt-date cash alone does not reduce invoice AR until allocated.";break;}
        }
        var totals=new JsonObject();if(rows.Count>0)foreach(var cell in rows[0]!.AsObject())if(cell.Value is JsonValue v&&v.TryGetValue<decimal>(out _)&&cell.Key!="records")totals[cell.Key]=Sum(rows,cell.Key);
        var org=await Store.One(c,"SELECT name FROM company WHERE id=@p0",company);
        var customerScope=string.IsNullOrEmpty(customerId)?"All customers":(await Store.Rows(c,"SELECT name FROM customer WHERE company_id=@p0 AND id=@p1",company,customerId)).FirstOrDefault()?.Text("name")??customerId;
        var projectScope=string.IsNullOrEmpty(projectId)?"All projects":(await Store.Rows(c,"SELECT code||' - '||name AS name FROM project WHERE company_id=@p0 AND id=@p1",company,projectId)).FirstOrDefault()?.Text("name")??projectId;
        return new JsonObject{["kind"]=kind,["company"]=org.Text("name"),["start"]=start,["end"]=end,["currency"]="AED",["customer_filter"]=customerScope,["project_filter"]=projectScope,["basis"]=basis,["generated_at"]=DateTimeOffset.UtcNow.ToString("O"),["rows"]=rows,["totals"]=totals,["row_count"]=rows.Count};
    }
    public static void Map(RouteGroupBuilder api,Store store,string root,string data)
    {
        api.MapGet("/analytics/catalog",()=>Kinds);
        api.MapGet("/analytics/filters",async(HttpContext h)=>{await using var c=await store.Open();return new{customers=await Store.Rows(c,"SELECT id,name FROM customer WHERE company_id=@p0 ORDER BY name",Accounts.Company(h)),projects=await Store.Rows(c,"SELECT id,name,code,customer_id FROM project WHERE company_id=@p0 ORDER BY code",Accounts.Company(h))};});
        api.MapGet("/analytics/report",async(HttpContext h,string kind,string start,string end,string? customerId,string? projectId,string? format)=>{
            Billing.Require(format is null or "json" or "xlsx" or "pdf","Choose JSON, Excel or PDF.");await using var c=await store.Open();await using var tx=await c.BeginTransactionAsync(System.Data.IsolationLevel.RepeatableRead);
            var report=await Build(c,Accounts.Company(h),kind,start,end,customerId,projectId);await tx.CommitAsync();h.Response.Headers.CacheControl="no-store";
            if(format=="pdf")return Results.File(await Documents.Generate(root,data,"analytics",report),"application/pdf",$"SALES360-{kind}-{end}.pdf");
            if(format=="xlsx"){
                using var book=new XLWorkbook();var meta=book.AddWorksheet("Report basis");int mr=1;foreach(var key in new[]{"company","kind","start","end","currency","customer_filter","project_filter","basis","generated_at","row_count"}){meta.Cell(mr,1).Value=key;meta.Cell(mr++,2).Value=report.Text(key);}meta.Column(2).Width=100;meta.Column(2).Style.Alignment.WrapText=true;meta.Rows().AdjustToContents();
                var sheet=book.AddWorksheet("Data");var rows=report["rows"]!.AsArray();var keys=rows.Count==0?new[]{"No records"}:rows[0]!.AsObject().Select(x=>x.Key).ToArray();
                for(int k=0;k<keys.Length;k++)sheet.Cell(1,k+1).Value=keys[k];for(int r=0;r<rows.Count;r++)for(int k=0;k<keys.Length;k++){var value=rows[r]![keys[k]];if(value is JsonValue v&&v.TryGetValue<decimal>(out var n)){sheet.Cell(r+2,k+1).Value=n;sheet.Cell(r+2,k+1).Style.NumberFormat.Format="#,##0.00";}else sheet.Cell(r+2,k+1).Value=value?.ToString()??"";}
                sheet.Row(1).Style.Font.Bold=true;sheet.SheetView.FreezeRows(1);sheet.Columns().AdjustToContents();foreach(var col in sheet.ColumnsUsed())col.Width=Math.Clamp(col.Width,12,45);var totalSheet=book.AddWorksheet("Totals");var tr=1;foreach(var item in report["totals"]!.AsObject()){totalSheet.Cell(tr,1).Value=item.Key;totalSheet.Cell(tr++,2).Value=item.Value!.GetValue<decimal>();}totalSheet.Columns().AdjustToContents();using var output=new MemoryStream();book.SaveAs(output);return Results.File(output.ToArray(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",$"SALES360-{kind}-{end}.xlsx");
            }
            return Results.Json(report);
        });
    }
}

using System.Text.Json.Nodes;
using Npgsql;
using Sales360.Domain;
namespace Sales360.Api;
public static class Reports
{
    public static async Task<JsonArray> Invoices(NpgsqlConnection c,string company,string asOf)
    {
        var date=DateOnly.ParseExact(asOf,"yyyy-MM-dd");
        var rows=await Store.Rows(c,$"SELECT i.*,cu.name AS customer,p.name AS project,p.code AS job,({Corrections.OpenSql("i","@p1")}) AS balance,coalesce((SELECT sum(amount) FROM financial_correction f WHERE f.invoice_id=i.id AND kind IN ('Credit note','Write-off') AND effective_date<=@p1),0) AS adjustments FROM invoice i JOIN customer cu ON cu.id=i.customer_id JOIN project p ON p.id=i.project_id WHERE i.company_id=@p0 AND i.issue_date<=@p1 ORDER BY i.issue_date DESC,i.reference",company,date);
        foreach(var row in rows){var r=row!;r["aging_bucket"]=Billing.AgingBucket(DateOnly.Parse(r.Text("due_date")),date);r["status"]=r.Decimal("balance")==0?(r.Decimal("adjustments")>0?"Settled":"Paid"):r.Decimal("balance")<r.Decimal("total")?"Partially paid":DateOnly.Parse(r.Text("due_date"))<date?"Overdue":"Open";}return rows;
    }
    public static async Task<object> Dashboard(NpgsqlConnection c,string company,string asOf,string? start,string? end)
    {
        var date=DateOnly.ParseExact(asOf,"yyyy-MM-dd");var first=start==null?new DateOnly(date.Year,1,1):DateOnly.ParseExact(start,"yyyy-MM-dd");var last=end==null?date:DateOnly.ParseExact(end,"yyyy-MM-dd");Billing.Require(first<=last,"Period start must precede end.");
        var invoices=await Invoices(c,company,asOf);var receipts=await Store.Rows(c,"SELECT * FROM cash_movement WHERE company_id=@p0 AND date<=@p1",company,date);
        var sales=await Store.Rows(c,"SELECT category,sum(net) AS amount FROM sales_movement WHERE company_id=@p0 AND date BETWEEN @p1 AND @p2 GROUP BY category",company,first,last);
        var categories=Billing.Categories.Select(category=>new{category,amount=sales.FirstOrDefault(x=>x.Text("category")==category)?.Decimal("amount")??0}).ToArray();
        var previousEnd=first.AddDays(-1);var previousStart=previousEnd.AddDays(-(last.DayNumber-first.DayNumber));var prior=(await Store.One(c,"SELECT coalesce(sum(net),0) AS amount FROM sales_movement WHERE company_id=@p0 AND date BETWEEN @p1 AND @p2",company,previousStart,previousEnd)).Decimal("amount");
        var aging=new decimal[5];foreach(var i in invoices)aging[i!.Integer("aging_bucket")]+=i.Decimal("balance");var gross=invoices.Sum(x=>x.Decimal("balance"));
        var unapplied=(await Store.One(c,$"SELECT coalesce(sum({Corrections.CashSql("r","@p1")}),0) AS amount FROM receipt r WHERE r.company_id=@p0 AND r.receipt_date<=@p1",company,date)).Decimal("amount");
        var trend=await Store.Rows(c,"SELECT to_char(date,'YYYY-MM') AS month,sum(net) AS sales FROM sales_movement WHERE company_id=@p0 AND date BETWEEN @p1 AND @p2 GROUP BY 1 ORDER BY 1",company,first,last);
        var collections=await Store.Rows(c,"SELECT to_char(date,'YYYY-MM') AS month,sum(amount) AS collections FROM cash_movement WHERE company_id=@p0 AND date BETWEEN @p1 AND @p2 GROUP BY 1 ORDER BY 1",company,first,last);
        var months=new List<object>();for(var m=new DateOnly(first.Year,first.Month,1);m<=last;m=m.AddMonths(1)){var key=m.ToString("yyyy-MM");months.Add(new{month=key,sales=trend.FirstOrDefault(x=>x.Text("month")==key)?.Decimal("sales")??0,collections=collections.FirstOrDefault(x=>x.Text("month")==key)?.Decimal("collections")??0});}
        return new{asOf,currency="AED",source="Posted SALES360 ledger",dateBasis="Asia/Dubai business dates; sales net of credits exclude VAT; cash net of refunds/reversals",refreshedAt=DateTimeOffset.UtcNow,period=new{start=first,end=last,previousStart,previousEnd},receivables=gross,unappliedCash=unapplied,netExposure=gross-unapplied,overdue=aging.Skip(1).Sum(),sales=categories.Sum(x=>x.amount),previousSales=prior,salesChange=prior==0?(decimal?)null:Billing.Money((categories.Sum(x=>x.amount)-prior)/prior*100),collectionsMtd=receipts.Where(x=>DateOnly.Parse(x.Text("date"))>=new DateOnly(date.Year,date.Month,1)).Sum(x=>x.Decimal("amount")),collectionsYtd=receipts.Where(x=>DateOnly.Parse(x.Text("date"))>=new DateOnly(date.Year,1,1)).Sum(x=>x.Decimal("amount")),collectionsPeriod=(await Store.One(c,"SELECT coalesce(sum(amount),0) AS amount FROM cash_movement WHERE company_id=@p0 AND date BETWEEN @p1 AND @p2",company,first,last)).Decimal("amount"),categories,aging,trend=months,overdueInvoices=invoices.Where(x=>x.Decimal("balance")>0&&DateOnly.Parse(x.Text("due_date"))<date).Take(8),pipeline=await Store.Rows(c,"SELECT state,count(*) AS count FROM certificate WHERE company_id=@p0 GROUP BY state",company),projectCount=(await Store.One(c,"SELECT count(*) AS count FROM project WHERE company_id=@p0",company)).Integer("count")};
    }
    public static async Task<object> Statement(NpgsqlConnection c,string company,string customer,string asOf)
    {
        var date=DateOnly.ParseExact(asOf,"yyyy-MM-dd");var rows=await Store.Rows(c,"SELECT issue_date AS date,reference,'Invoice' AS type,total AS debit,0::numeric AS credit FROM invoice WHERE company_id=@p0 AND customer_id=@p1 AND issue_date<=@p2 UNION ALL SELECT receipt_date,reference,'Receipt',0::numeric,amount FROM receipt WHERE company_id=@p0 AND customer_id=@p1 AND receipt_date<=@p2 UNION ALL SELECT effective_date,reference,kind,CASE WHEN kind IN ('Refund','Receipt reversal') THEN amount ELSE 0 END,CASE WHEN kind IN ('Credit note','Write-off') THEN amount ELSE 0 END FROM financial_correction WHERE company_id=@p0 AND customer_id=@p1 AND effective_date<=@p2 AND kind<>'Allocation reversal' ORDER BY date,reference",company,customer,date);decimal balance=0;foreach(var row in rows){var r=row!;balance+=r.Decimal("debit")-r.Decimal("credit");r["balance"]=balance;}return new{asOf,currency="AED",basis="Posted invoices, credits, write-offs and net cash through selected date; unapplied cash included",openingBalance=0,closingBalance=balance,rows};
    }
}

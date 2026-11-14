using System.Text.Json.Nodes;
using System.Globalization;
using ClosedXML.Excel;
using System.Text.RegularExpressions;
using Npgsql;
using Sales360.Domain;
namespace Sales360.Api;
public record CustomerField(string Key,string Label,string Type="text");
public static class CustomerMaster
{
    public static readonly CustomerField[] Fields=[
        new("serial_no","Sl. No."),new("legal_entity_name","Legal entity name"),new("registered_address","Registered address","textarea"),new("city","City"),new("emirate","Emirate"),new("country","Country"),new("trade_licence_number","Trade licence number"),new("trade_licence_issuing_authority","Trade licence issuing authority"),new("free_zone_entity","Free zone entity"),new("tin","Tax Identification Number (TIN)"),new("trn","Tax Registration Number (TRN)"),new("peppol_participant_identifier","Peppol participant identifier"),new("e_invoicing_go_live","E-invoicing go-live","date"),new("remarks","Remarks","textarea"),new("vat_registered","VAT registered?"),new("legal_registration_id_type","Legal registration ID type"),new("asp_name","ASP name"),new("asp_onboarding_status","ASP onboarding status"),new("ar_billing_email","AR / billing email","email"),new("ap_accounts_email","AP / accounts email","email"),new("primary_e_invoicing_contact","Primary e-invoicing contact"),new("contact_number","Contact number"),new("supporting_documents_attached","Supporting documents attached?"),new("date_received","Date received","date"),new("validation_status","Validation status")];
    public static JsonObject Normalize(JsonNode source)
    {
        var result=new JsonObject();foreach(var field in Fields){var value=source.Text(field.Key);Billing.Require(value.Length<=(field.Type=="textarea"?4000:400),field.Label+" is too long.");if(field.Type=="date"&&value!="")Billing.Require(DateOnly.TryParseExact(value,"yyyy-MM-dd",out _),field.Label+" must be YYYY-MM-DD.");if(field.Type=="email"&&value!="")Accounts.Email(value);result[field.Key]=value;}
        Billing.Require(result.Text("legal_entity_name").Length>=2,"Legal entity name is required.");var trn=result.Text("trn");Billing.Require(trn==""||Regex.IsMatch(trn,"^[0-9]{15}$"),"TRN must be blank or 15 digits, stored as text. Oversized Excel numbers must be corrected at source.");
        Billing.Require(!result.Text("vat_registered").Equals("Yes",StringComparison.OrdinalIgnoreCase)||trn!="","A VAT-registered customer needs its TRN.");return result;
    }
    public static bool CanWrite(HttpContext h)=>new[]{"Administrator","Super user","Accountant","Finance Administrator"}.Any(h.User.IsInRole);
    public static async Task<JsonObject> Save(NpgsqlConnection c,string company,string actor,JsonObject b,string? id=null)
    {
        var details=Normalize(b["details"]??b);var code=b.Text("code");Billing.Require(code.Length is >0 and <=80,"Customer code is required (up to 80 characters).");var terms=b["terms"]==null?30:b.Integer("terms");Billing.Require(terms is >=0 and <=3650,"Terms must be 0–3650 days.");
        if(id==null){id=Guid.NewGuid().ToString("N");await Store.Exec(c,"INSERT INTO customer(id,company_id,code,name,email,trn,terms,details,revision) VALUES(@p0,@p1,@p2,@p3,@p4,@p5,@p6,@p7::jsonb,1)",id,company,code,details.Text("legal_entity_name"),details.Text("ar_billing_email"),details.Text("trn"),terms,details.ToJsonString());}
        else {var old=await Store.One(c,"SELECT * FROM customer WHERE company_id=@p0 AND id=@p1 FOR UPDATE",company,id);Billing.Require(b.Integer("expected_revision")==old.Integer("revision"),"Customer changed since this form or preview was opened. Reload before saving.");await Store.Exec(c,"UPDATE customer SET code=@p0,name=@p1,email=@p2,trn=@p3,terms=@p4,details=@p5::jsonb,revision=revision+1 WHERE company_id=@p6 AND id=@p7",code,details.Text("legal_entity_name"),details.Text("ar_billing_email"),details.Text("trn"),terms,details.ToJsonString(),company,id);}
        await Store.Audit(c,company,actor,"Customer master saved",id,new{code,details});return await Store.One(c,"SELECT * FROM customer WHERE company_id=@p0 AND id=@p1",company,id);
    }
    static IResult Template(bool statement)
    {
        using var book=new XLWorkbook();var sheet=book.AddWorksheet(statement?"Statement":"Client");
        if(!statement){
            for(var col=0;col<Fields.Length;col++){sheet.Cell(1,col+1).Value=Fields[col].Label;sheet.Column(col+1).Width=26;sheet.Range(2,col+1,1001,col+1).Style.NumberFormat.Format="@";}
            sheet.Row(1).Style.Font.Bold=true;sheet.Row(1).Style.Fill.BackgroundColor=XLColor.LightBlue;sheet.SheetView.FreezeRows(1);
        }else{
            foreach(var entry in new[]{("A1","Company name"),("A2","Company address"),("C3","Customer statement of accounts"),("A4","Project code"),("D4","Customer legal name"),("A5","Project description"),("A6","Customer address"),("F6","Statement date"),("A7","Customer TRN"),("F7","Place of supply")})sheet.Cell(entry.Item1).Value=entry.Item2;
            string[] headers=["Invoice / Certificate No.","Nature of Revenue","Fee Type","Invoice Date","Billing Amount","Collection Date","Collection Amount","Currency","Outstanding"];
            for(var col=0;col<9;col++){sheet.Cell(8,col+1).Value=headers[col];sheet.Column(col+1).Width=25;}
            foreach(var entry in new[]{("K1","Optional customer code"),("K2","Optional billing email"),("K3","Optional credit terms (days)"),("K4","Optional reviewed contract fee"),("K5","Optional project category"),("K6","Optional project location")})sheet.Cell(entry.Item1).Value=entry.Item2;
            sheet.Column(11).Width=32;sheet.Column(12).Width=32;sheet.Range("L1:L6").Style.NumberFormat.Format="@";
            sheet.Row(8).Style.Font.Bold=true;sheet.Row(8).Style.Fill.BackgroundColor=XLColor.LightBlue;sheet.SheetView.FreezeRows(8);
            sheet.Range("A9:C1008").Style.NumberFormat.Format="@";sheet.Cell("B7").Style.NumberFormat.Format="@";
            foreach(var col in new[]{4,6})sheet.Range(9,col,1008,col).Style.DateFormat.Format="yyyy-mm-dd";
            foreach(var col in new[]{5,7,9})sheet.Range(9,col,1008,col).Style.NumberFormat.Format="#,##0.00";
        }
        var guide=book.AddWorksheet("Instructions");guide.Column(1).Width=110;
        var lines=statement?new[]{"Enter company name C1, company address C2, project code B4 and customer legal name E4.","Enter project description B5, customer address B6, statement date G6, TRN as 15-digit text B7, place of supply G7.","One invoice per row, starting row 9. No duplicated invoice references. Dates must be Excel dates or YYYY-MM-DD.","Billing Amount is gross including VAT. Collection Amount is dated paid amount. Outstanding = Billing - Collection.","Currency AED. Fee Type: Design, Supervision, Overtime Claims, Authority Fees or Other Services.", "Version 8: Import customer statement of accounts creates/matches customers and projects after a reviewed preview. Administrator or Finance Administrator access is required to post.","Confirm VAT treatment and reconciliation reference. Repeated payments per invoice require reconciliation before import.","Optional L1 customer code, L2 billing email, L3 credit days, L4 reviewed contract fee, L5 category, L6 project location. New projects need contract review before certificate billing. Copy the statement sheet for additional projects (up to 100 sheets). Do not import the same debt as opening balances. Unchanged invoices are reused; changed payments/amounts require reconciliation."}:new[]{"Keep the Client sheet and all 25 headers unchanged. One legal entity per row, starting row 2.","Legal entity name is required. TRN must be 15 digits if VAT registered. Store registration IDs, TIN, phone and TRN as text.","Dates: YYYY-MM-DD or Excel dates. Blank numbered rows are ignored. Do not use formulas.","Customer codes are generated from legal entity names. Matching existing names update existing master records after review.","Blank cells can overwrite existing values: inspect preview and warnings before approving.","Import data in Customer master; review all captured fields and acknowledge warnings before committing."};
        for(var i=0;i<lines.Length;i++)guide.Cell(i+1,1).Value=lines[i];
        using var output=new MemoryStream();book.SaveAs(output);return Results.File(output.ToArray(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",statement?"SALES360-SOA-import-format.xlsx":"SALES360-Customer-import-format.xlsx");
    }
    public static void Map(RouteGroupBuilder api,Store store,Func<HttpContext,string> company,Func<HttpContext,string> actor)
    {
        api.MapGet("/customer-fields",()=>Fields);
        api.MapGet("/customers/import-template",()=>Template(false));
        api.MapGet("/customers/statement-template",()=>Template(true));
        api.MapGet("/customers/export",async(HttpContext h)=>{
            await using var c=await store.Open();var rows=await Store.Rows(c,"SELECT * FROM customer WHERE company_id=@p0 ORDER BY code",company(h));using var book=new ClosedXML.Excel.XLWorkbook();var sheet=book.AddWorksheet("Client");
            for(int col=0;col<Fields.Length;col++)sheet.Cell(1,col+1).Value=Fields[col].Label;
            for(int i=0;i<rows.Count;i++){
                var row=rows[i]!;var details=row["details"]!.DeepClone().AsObject();details["legal_entity_name"]=row.Text("name");details["trn"]=row.Text("trn");details["ar_billing_email"]=row.Text("email");if(details.Text("serial_no")=="")details["serial_no"]=(i+1).ToString();
                for(int col=0;col<Fields.Length;col++){var field=Fields[col];var cell=sheet.Cell(i+2,col+1);var value=details.Text(field.Key);if(field.Type=="date"&&DateTime.TryParseExact(value,"yyyy-MM-dd",null,DateTimeStyles.None,out var date)){cell.Value=date;cell.Style.DateFormat.Format="yyyy-mm-dd";}else{cell.Value=value;cell.Style.NumberFormat.Format="@";}}
            }
            sheet.Row(1).Style.Font.Bold=true;sheet.SheetView.FreezeRows(1);sheet.Columns().AdjustToContents();foreach(var column in sheet.ColumnsUsed())if(column.Width>45)column.Width=45;
            using var output=new MemoryStream();book.SaveAs(output);return Results.File(output.ToArray(),"application/vnd.openxmlformats-officedocument.spreadsheetml.sheet","Customer-e-invoicing-master.xlsx");
        });
        api.MapPost("/customers/{id}/master",async(HttpContext h,string id,JsonObject b)=>{if(!CanWrite(h))throw new UnauthorizedAccessException("A customer-master duty is required.");return await store.Transaction(company(h),c=>Save(c,company(h),actor(h),b,id));});
        api.MapPost("/customers/master",async(HttpContext h,JsonObject b)=>{if(!CanWrite(h))throw new UnauthorizedAccessException("A customer-master duty is required.");return await store.Transaction(company(h),c=>Save(c,company(h),actor(h),b));});
    }
}

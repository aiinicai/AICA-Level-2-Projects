using ClosedXML.Excel;
using System.Globalization;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Sales360.Domain;
using Npgsql;
namespace Sales360.Api;
public static class WorkbookImports
{
    static string Value(IXLCell cell,bool date=false)
    {
        var value=cell.HasFormula?cell.CachedValue:cell.Value;
        if(value.Type==XLDataType.DateTime)return value.GetDateTime().ToString("yyyy-MM-dd");
        if(date&&value.Type==XLDataType.Number){var n=value.GetNumber();if(n is >=20000 and <=80000)return DateTime.FromOADate(n).ToString("yyyy-MM-dd");}
        return value.ToString(CultureInfo.InvariantCulture).Trim();
    }
    static XLWorkbook ReadWorkbook(Stream stream)
    {
        try{return new XLWorkbook(stream);}catch(Exception e) when(e is not OutOfMemoryException){throw new RuleException("The workbook could not be read. Re-save it as a normal XLSX file using the supplied template; malformed or encrypted workbooks are not supported.");}
    }
    static decimal Amount(string text)=>decimal.TryParse(text,NumberStyles.Number|NumberStyles.AllowExponent,CultureInfo.InvariantCulture,out var n)?Billing.Money(n):throw new RuleException("A financial amount is not a valid number.");
    static JsonObject Master(XLWorkbook book,JsonArray errors,JsonArray warnings)
    {
        Billing.Require(book.TryGetWorksheet("Client",out var sheet),"Customer template must contain the Client sheet.");
        var header=sheet.Row(1).CellsUsed().ToDictionary(x=>Value(x),x=>x.Address.ColumnNumber,StringComparer.OrdinalIgnoreCase);var rows=new JsonArray();var skipped=0;
        foreach(var f in CustomerMaster.Fields)if(!header.ContainsKey(f.Label))errors.Add("Missing customer column: "+f.Label);
        var last=sheet.LastRowUsed()?.RowNumber()??1;Billing.Require(last<=10001,"Import supports up to 10,000 customer rows.");
        for(int r=2;r<=last;r++){
            var details=new JsonObject();foreach(var f in CustomerMaster.Fields){var cell=header.TryGetValue(f.Label,out var col)?sheet.Cell(r,col):null;details[f.Key]=cell==null?"":Value(cell,f.Type=="date");if(cell?.HasFormula==true)errors.Add($"Client row {r}: {f.Label} must contain a value, not a formula.");}
            if(CustomerMaster.Fields.Where(f=>f.Key!="serial_no").All(f=>details.Text(f.Key)=="")){skipped++;continue;}
            try{CustomerMaster.Normalize(details);}catch(RuleException e){errors.Add($"Client row {r}: {e.Message}");}
            foreach(var key in new[]{"tin","trn","trade_licence_number","peppol_participant_identifier"})if(details.Text(key).Contains('E')||details.Text(key).Contains('e')){if(Regex.IsMatch(details.Text(key),@"^[0-9.]+[eE][+-]?[0-9]+$"))errors.Add($"Client row {r}: {key} is scientific notation. Re-enter the identifier as text from the original record.");}
            var name=details.Text("legal_entity_name");var code="CUST-"+Store.Hash(name.ToUpperInvariant())[..12].ToUpperInvariant();rows.Add(new JsonObject{["row"]=r,["code"]=code,["details"]=details});
        }
        if(skipped>0)warnings.Add($"Ignored {skipped} blank/numbered placeholder rows; these are not customers.");
        if(rows.Select(x=>x!["details"]!.Text("legal_entity_name").ToUpperInvariant()).Distinct().Count()!=rows.Count)errors.Add("Duplicate legal entity names in the source. Review distinct registrations before importing.");
        return new JsonObject{["customers"]=rows,["fields"]=new JsonArray(CustomerMaster.Fields.Select(f=>(JsonNode?)JsonValue.Create(f.Label)).ToArray()),["placeholderRowsIgnored"]=skipped};
    }
    static JsonObject StatementSheet(IXLWorksheet sheet,JsonArray errors,JsonArray warnings)
    {
        Billing.Require(Value(sheet.Cell("A8")).StartsWith("Invoice",StringComparison.OrdinalIgnoreCase)&&Value(sheet.Cell("E8"))=="Billing Amount","SOA layout must match the supplied statement format (headers on row 8).");
        var metadata=new JsonObject{["organization_name"]=Value(sheet.Cell("C1")),["organization_address"]=Value(sheet.Cell("C2")),["title"]=Value(sheet.Cell("C3")),["project_no"]=Value(sheet.Cell("B4")),["client_name"]=Value(sheet.Cell("E4")),["project_description"]=Value(sheet.Cell("B5")),["client_address"]=Value(sheet.Cell("B6")),["statement_date"]=Value(sheet.Cell("G6"),true),["client_trn_raw"]=Value(sheet.Cell("B7")),["place_of_supply"]=Value(sheet.Cell("G7")),["sheet_name"]=sheet.Name,["customer_code"]=Value(sheet.Cell("L1")),["billing_email"]=Value(sheet.Cell("L2")),["payment_terms"]=Value(sheet.Cell("L3")),["project_fee"]=Value(sheet.Cell("L4")),["project_category"]=Value(sheet.Cell("L5")),["project_location"]=Value(sheet.Cell("L6"))};
        if(!Regex.IsMatch(metadata.Text("client_trn_raw"),"^[0-9]{15}$"))warnings.Add("Source client TRN is not a valid 15-digit text value. It is preserved as source data and will not overwrite the customer TRN.");
        if(sheet.Cell("G6").HasFormula)warnings.Add("Statement date uses a formula. Preview freezes its saved cached date; it does not recalculate TODAY().");
        var rows=new JsonArray();decimal grossTotal=0,paidTotal=0;var last=sheet.LastRowUsed()?.RowNumber()??8;Billing.Require(last<=10008,"SOA supports up to 10,000 source rows.");
        for(int r=9;r<=last;r++){
            var reference=Value(sheet.Cell(r,1));if(reference=="")continue;
            if(reference.Equals("TOTAL",StringComparison.OrdinalIgnoreCase)){
                try{if(Amount(Value(sheet.Cell(r,5)))!=grossTotal||Amount(Value(sheet.Cell(r,7)))!=paidTotal||Amount(Value(sheet.Cell(r,9)))!=grossTotal-paidTotal)errors.Add("Source total row does not reconcile to the detail rows.");}catch(RuleException e){errors.Add(e.Message);}continue;
            }
            if(!Billing.Categories.Contains(Value(sheet.Cell(r,3)))&&Value(sheet.Cell(r,3))!="Authority")errors.Add($"SOA row {r}: fee type needs an explicit supported service-category mapping.");
            var row=new JsonObject{["row"]=r,["reference"]=reference,["nature_of_revenue"]=Value(sheet.Cell(r,2)),["fee_type"]=Value(sheet.Cell(r,3)),["invoice_date"]=Value(sheet.Cell(r,4),true),["billing_amount"]=Value(sheet.Cell(r,5)),["collection_date"]=Value(sheet.Cell(r,6),true),["collection_amount"]=Value(sheet.Cell(r,7)),["currency"]=Value(sheet.Cell(r,8)),["source_outstanding"]=Value(sheet.Cell(r,9))};
            var raw=new JsonObject();for(int col=1;col<=9;col++){var cell=sheet.Cell(r,col);raw[cell.Address.ToString()!]=new JsonObject{["value"]=Value(cell),["formula"]=cell.HasFormula?cell.FormulaA1:""};}row["source_cells"]=raw;
            try{
                var gross=Amount(row.Text("billing_amount"));var paid=row.Text("collection_amount")==""?0:Amount(row.Text("collection_amount"));Billing.Require(gross>0&&paid>=0&&paid<=gross,"Billing must be positive and collection between zero and billing.");
                Billing.Require(DateOnly.TryParseExact(row.Text("invoice_date"),"yyyy-MM-dd",out var invoiceDate),"Invoice date is missing or invalid.");
                if(paid>0){Billing.Require(DateOnly.TryParseExact(row.Text("collection_date"),"yyyy-MM-dd",out var collectionDate)&&collectionDate>=invoiceDate,"Positive collection needs a valid date on or after its invoice date.");}
                if(row.Text("source_outstanding")!="")Billing.Require(Amount(row.Text("source_outstanding"))==gross-paid,"Saved outstanding does not equal billing minus collection.");
                row["billing_amount"]=gross;row["collection_amount"]=paid;row["outstanding"]=gross-paid;grossTotal+=gross;paidTotal+=paid;
            }catch(RuleException e){errors.Add($"SOA row {r}: {e.Message}");}
            if(row.Text("currency")=="")warnings.Add($"SOA row {r}: blank currency requires an explicit reviewed import currency.");else if(row.Text("currency")!="AED")errors.Add($"SOA row {r}: only AED posting is supported; retain other currencies for manual review.");
            var referenceJob=Regex.Match(reference,@"(?:^|/)([0-9]{3,})(?:/|$)");if(referenceJob.Success&&referenceJob.Groups[1].Value!=metadata.Text("project_no")){metadata["reference_project_mismatch"]=true;warnings.Add($"SOA row {r}: invoice reference project differs from the statement project number. Confirm the target project explicitly.");}
            rows.Add(row);
        }
        if(rows.Count==0)errors.Add("No financial detail rows found.");if(rows.Select(x=>x!.Text("reference")).Distinct().Count()!=rows.Count)errors.Add("Repeated invoice references require a normalized multi-payment reconciliation; do not post this sheet twice.");
        return new JsonObject{["metadata"]=metadata,["rows"]=rows,["controlTotals"]=new JsonObject{["billing"]=grossTotal,["collections"]=paidTotal,["outstanding"]=grossTotal-paidTotal}};
    }
    static JsonObject Statement(XLWorkbook book,JsonArray errors,JsonArray warnings)
    {
        var sheets=book.Worksheets.Where(s=>Value(s.Cell("A8")).StartsWith("Invoice",StringComparison.OrdinalIgnoreCase)&&Value(s.Cell("E8"))=="Billing Amount").ToList();
        Billing.Require(sheets.Count>0&&sheets.Count<=101,"No SOA layout found. Use headers on row 8; up to 101 statement sheets are supported.");
        var statements=new JsonArray();var allRows=new JsonArray();decimal billing=0,collections=0;
        foreach(var sheet in sheets){var part=StatementSheet(sheet,errors,warnings);statements.Add(part);foreach(var row in part["rows"]!.AsArray()){var copy=row!.DeepClone();copy["sheet_name"]=sheet.Name;allRows.Add(copy);}billing+=part["controlTotals"]!.Decimal("billing");collections+=part["controlTotals"]!.Decimal("collections");}
        Billing.Require(allRows.Count<=10000,"A workbook supports up to 10,000 financial rows in total.");
        if(allRows.Select(r=>r!.Text("reference")).Distinct(StringComparer.OrdinalIgnoreCase).Count()!=allRows.Count)errors.Add("Invoice references repeat across sheets. Reconcile them before importing.");
        var metadata=statements[0]!["metadata"]!.DeepClone();metadata["reference_project_mismatch"]=statements.Any(s=>s!["metadata"]?["reference_project_mismatch"]?.GetValue<bool>()==true);
        return new JsonObject{["metadata"]=metadata,["rows"]=allRows,["statements"]=statements,["controlTotals"]=new JsonObject{["billing"]=billing,["collections"]=collections,["outstanding"]=billing-collections}};
    }
    public static async Task<(int Created,int Skipped)> PostRows(NpgsqlConnection c,string company,string actor,string id,JsonNode batch,JsonNode payload,JsonObject project,JsonObject customer,JsonObject b,bool allowExisting)
    {
        int created=0,skipped=0;var rate=b.Decimal("vat_rate");
        foreach(var row in payload["rows"]!.AsArray()){
            var x=row!;var gross=x.Decimal("billing_amount");var net=Billing.Money(gross/(1+rate/100));var vat=gross-net;var date=x.Date("invoice_date");var category=x.Text("fee_type")=="Authority"?"Authority Fees":Billing.Categories.Contains(x.Text("fee_type"))?x.Text("fee_type"):project.Text("category");
            var existing=await Store.Rows(c,"SELECT * FROM invoice WHERE company_id=@p0 AND lower(reference)=lower(@p1)",company,x.Text("reference"));
            if(existing.Count>0){
                Billing.Require(allowExisting&&existing.Count==1,"An invoice reference already exists. Reconcile existing postings; this workbook cannot post it again.");var old=existing[0]!;
                Billing.Require(old.Text("customer_id")==customer.Text("id")&&old.Text("project_id")==project.Text("id")&&old.Decimal("total")==gross&&old.Decimal("net")==net&&old.Decimal("vat")==vat&&DateOnly.Parse(old.Text("issue_date"))==date&&old.Text("category")==category,"Existing invoice "+x.Text("reference")+" has different customer, project, dates, category or amounts. Use reviewed corrections instead of reimporting changed postings.");
                var cash=await Store.One(c,"SELECT coalesce(sum(amount),0) AS paid,count(*) AS count,min(effective_date) AS first_date,max(effective_date) AS last_date FROM allocation a WHERE invoice_id=@p0 AND NOT EXISTS(SELECT 1 FROM financial_correction f WHERE f.allocation_id=a.id AND f.kind='Allocation reversal')",old.Text("id"));
                var corrections=await Store.One(c,"SELECT count(*) AS count FROM financial_correction WHERE invoice_id=@p0 AND kind IN ('Credit note','Write-off')",old.Text("id"));
                Billing.Require(cash.Decimal("paid")==x.Decimal("collection_amount")&&corrections.Integer("count")==0&&(x.Decimal("collection_amount")==0||(DateOnly.Parse(cash.Text("first_date"))==x.Date("collection_date")&&DateOnly.Parse(cash.Text("last_date"))==x.Date("collection_date"))),"Existing invoice "+x.Text("reference")+" has different collections or corrections. Record/reconcile receipt allocations and corrections; cumulative SOA amounts cannot safely create new cash entries.");
                skipped++;continue;
            }
            if(allowExisting)Billing.Require((await Store.One(c,"SELECT count(*) AS count FROM certificate x WHERE company_id=@p0 AND project_id=@p1 AND state<>'Returned' AND NOT EXISTS(SELECT 1 FROM invoice i WHERE i.certificate_id=x.id)",company,project.Text("id"))).Integer("count")==0,"Complete or reconcile pending/unissued certificates before adding historical invoices to this project. Unchanged invoice rows can still be checked safely.");
            var iid=Guid.NewGuid().ToString("N");var evidence=new JsonObject{["import_id"]=id,["source_hash"]=batch.Text("hash"),["source_row"]=x.DeepClone(),["source_metadata"]=payload["metadata"]!.DeepClone(),["review_reference"]=b.Text("review_reference"),["reviewed_vat_rate"]=rate,["target_customer_id"]=customer.Text("id"),["target_project_id"]=project.Text("id"),["mapping_review"]=b.DeepClone()};
            await Store.Exec(c,"INSERT INTO invoice(id,company_id,project_id,customer_id,reference,issue_date,due_date,net,vat,total,category,confirmation,organization_snapshot,source_data) VALUES(@p0,@p1,@p2,@p3,@p4,@p5,@p6,@p7,@p8,@p9,@p10,@p11::jsonb,@p12::jsonb,@p11::jsonb)",iid,company,project.Text("id"),customer.Text("id"),x.Text("reference"),date,date.AddDays(customer.Integer("terms")),net,vat,gross,category,evidence.ToJsonString(),(await Organization.Snapshot(c,company)).ToJsonString());
            if(x.Decimal("collection_amount")>0){var rid=Guid.NewGuid().ToString("N");var amount=x.Decimal("collection_amount");var paid=x.Date("collection_date");await Store.Exec(c,"INSERT INTO receipt(id,company_id,customer_id,reference,receipt_date,amount,method) VALUES(@p0,@p1,@p2,@p3,@p4,@p5,'Reviewed SOA migration')",rid,company,customer.Text("id"),"SOA/"+x.Text("reference")+"/"+paid.ToString("yyyyMMdd"),paid,amount);await Store.Exec(c,"INSERT INTO allocation(id,company_id,customer_id,receipt_id,invoice_id,amount,effective_date) VALUES(@p0,@p1,@p2,@p3,@p4,@p5,@p6)",Guid.NewGuid().ToString("N"),company,customer.Text("id"),rid,iid,amount,paid);}
            created++;
        }
        return (created,skipped);
    }
    public static void Map(RouteGroupBuilder api,Store store,string data,Func<HttpContext,string> company,Func<HttpContext,string> actor)
    {
        api.MapGet("/workbook-imports/{id}",async(HttpContext h,string id)=>{await using var c=await store.Open();return await Store.One(c,"SELECT * FROM workbook_import WHERE company_id=@p0 AND id=@p1",company(h),id);});
        api.MapGet("/workbook-imports",async(HttpContext h)=>{await using var c=await store.Open();return await Store.Rows(c,"SELECT id,kind,filename,status,errors,warnings,created_at FROM workbook_import WHERE company_id=@p0 ORDER BY created_at DESC",company(h));});
        api.MapPost("/workbook-imports/preview",async(HttpContext h)=>{
            if(!CustomerMaster.CanWrite(h))throw new UnauthorizedAccessException();var form=await h.Request.ReadFormAsync();var file=form.Files.GetFile("file")??throw new RuleException("Choose a workbook.");Billing.Require(file.Length>0&&file.Length<=10*1024*1024&&file.FileName.EndsWith(".xlsx",StringComparison.OrdinalIgnoreCase),"Choose an XLSX up to 10 MB.");using var ms=new MemoryStream();await file.CopyToAsync(ms);var bytes=ms.ToArray();var hash=Convert.ToHexString(System.Security.Cryptography.SHA256.HashData(bytes));ms.Position=0;
            try {using(var zip=new System.IO.Compression.ZipArchive(ms,System.IO.Compression.ZipArchiveMode.Read,true)){Billing.Require(zip.Entries.Count<=2000&&zip.Entries.Sum(e=>e.Length)<=50*1024*1024,"Expanded workbook exceeds safe limits.");Billing.Require(!zip.Entries.Any(e=>e.FullName.Contains("externalLinks/",StringComparison.OrdinalIgnoreCase)||e.FullName.Contains("vbaProject",StringComparison.OrdinalIgnoreCase)),"External links and macros are not supported.");}}catch(System.IO.InvalidDataException){throw new RuleException("This file is not a valid XLSX workbook. Use the supplied template and upload a normal .xlsx file.");}ms.Position=0;
            using var book=ReadWorkbook(ms);var kind=book.TryGetWorksheet("Client",out _)?"Customer master":"Statement of account";Billing.Require(form["expected_kind"].ToString()==""||form["expected_kind"].ToString()==kind,"This workbook does not match the selected import type. Choose Customer Statement of Accounts or Customer master to match its layout.");var errors=new JsonArray();var warnings=new JsonArray();var payload=kind=="Customer master"?Master(book,errors,warnings):Statement(book,errors,warnings);
            return await store.Transaction(company(h),async c=>{
                var prior=await Store.Rows(c,"SELECT * FROM workbook_import WHERE company_id=@p0 AND kind=@p1 AND hash=@p2",company(h),kind,hash);if(prior.Count>0&&prior[0]!.Text("status")=="Committed")return prior[0]!;
                if(kind=="Customer master")foreach(var row in payload["customers"]!.AsArray()){
                    var x=row!;var matches=await Store.Rows(c,"SELECT * FROM customer WHERE company_id=@p0 AND (code=@p1 OR lower(name)=lower(@p2))",company(h),x.Text("code"),x["details"]!.Text("legal_entity_name"));
                    if(matches.Count>1)errors.Add($"Customer row {x.Text("row")}: several existing customers match. Resolve them first.");
                    if(matches.Count==1){x["target_id"]=matches[0]!.Text("id");x["expected_revision"]=matches[0]!.Integer("revision");x["code"]=matches[0]!.Text("code");warnings.Add($"Customer row {x.Text("row")}: updates an existing customer; review all fields, including blanks.");}
                }
                if(kind=="Statement of account"){var planErrors=new JsonArray();payload["masterPlan"]=await StatementMasters.Plan(c,company(h),payload,planErrors,warnings);payload["masterPlanErrors"]=planErrors;}
                var folder=Path.Combine(data,"documents","imports",company(h));Directory.CreateDirectory(folder);await File.WriteAllBytesAsync(Path.Combine(folder,hash+".xlsx"),bytes);
                if(prior.Count>0){var oldId=prior[0]!.Text("id");await Store.Exec(c,"UPDATE workbook_import SET payload=@p0::jsonb,errors=@p1::jsonb,warnings=@p2::jsonb WHERE id=@p3",payload.ToJsonString(),errors.ToJsonString(),warnings.ToJsonString(),oldId);return await Store.One(c,"SELECT * FROM workbook_import WHERE id=@p0",oldId);}
                var id=Guid.NewGuid().ToString("N");await Store.Exec(c,"INSERT INTO workbook_import(id,company_id,kind,hash,filename,payload,errors,warnings) VALUES(@p0,@p1,@p2,@p3,@p4,@p5::jsonb,@p6::jsonb,@p7::jsonb)",id,company(h),kind,hash,Path.GetFileName(file.FileName),payload.ToJsonString(),errors.ToJsonString(),warnings.ToJsonString());await Store.Audit(c,company(h),actor(h),"Workbook migration preview",id,new{kind,hash});return await Store.One(c,"SELECT * FROM workbook_import WHERE id=@p0",id);
            });
        }).DisableAntiforgery();
        api.MapPost("/workbook-imports/{id}/commit",async(HttpContext h,string id,JsonObject b)=>{
            if(!CustomerMaster.CanWrite(h))throw new UnauthorizedAccessException();return await store.Transaction(company(h),async c=>{
                var batch=await Store.One(c,"SELECT * FROM workbook_import WHERE company_id=@p0 AND id=@p1 FOR UPDATE",company(h),id);if(batch.Text("status")=="Committed")return new{created=0,message="This exact workbook was already committed.",masters=new JsonObject()};Billing.Require(batch["errors"]!.AsArray().Count==0,"Resolve all preview errors before posting.");Billing.Require(b["acknowledge_warnings"]?.GetValue<bool>()==true,"Review and acknowledge source warnings before importing.");var payload=batch["payload"]!;int created=0;var masters=new JsonObject();
                if(batch.Text("kind")=="Customer master"){
                    Billing.Require(payload["customers"]!.AsArray().Count>0,"This is a blank template; there are no customer records to import.");
                    foreach(var row in payload["customers"]!.AsArray()){var x=row!.AsObject();await CustomerMaster.Save(c,company(h),actor(h),x,x.Text("target_id")==""?null:x.Text("target_id"));created++;}
                }else{
                    if(!h.User.IsInRole("Administrator")&&!h.User.IsInRole("Finance Administrator"))throw new UnauthorizedAccessException("Finance Administrator duty is required to post financial migration.");
                    Billing.Require(b.Text("review_reference").Length>=12,"Record a clear finance review / reconciliation reference (12+ characters).");Billing.Require(b["confirm_posted_invoices"]?.GetValue<bool>()==true,"Confirm these are existing posted invoices, not unapproved certificates or opening-balance summaries.");Billing.Require(payload["metadata"]?["reference_project_mismatch"]?.GetValue<bool>()!=true||b["confirm_project_override"]?.GetValue<bool>()==true,"Explicitly review and approve the mismatch between source project and invoice references.");var rate=b.Decimal("vat_rate");Billing.Require(rate is 0 or 5,"Choose an explicitly reviewed 0% or 5% VAT treatment for this gross-billed source.");Billing.Require(b.Text("currency")=="AED","Explicitly confirm AED as the import currency.");
                    if(b["auto_create_masters"]?.GetValue<bool>()==true){masters=await StatementMasters.Commit(c,company(h),actor(h),id,batch,b);created=masters.Integer("invoices_created");}
                    else {
                        Billing.Require(payload["statements"]==null||payload["statements"]!.AsArray().Count==1,"Use automatic master matching for a multi-statement workbook.");
                    var project=await Store.One(c,"SELECT * FROM project WHERE company_id=@p0 AND id=@p1",company(h),b.Text("project_id"));var customer=await Store.One(c,"SELECT * FROM customer WHERE company_id=@p0 AND id=@p1",company(h),b.Text("customer_id"));Billing.Require(project.Text("customer_id")==customer.Text("id"),"Selected project belongs to a different customer.");
                    Billing.Require(customer.Text("name").Equals(payload["metadata"]!.Text("client_name"),StringComparison.OrdinalIgnoreCase)||b["confirm_customer_override"]?.GetValue<bool>()==true,"Source client name differs from the selected customer. Explicitly confirm the reviewed customer mapping.");
                    Billing.Require(project.Text("code")==payload["metadata"]!.Text("project_no")||b["confirm_project_override"]?.GetValue<bool>()==true,"Source and target project differ. Explicitly confirm the reviewed project override.");
                    created+=(await PostRows(c,company(h),actor(h),id,batch,payload,project,customer,b,false)).Created;
                    }
                    // Control totals and every row are retained with the batch; outstanding is derived, never posted a second time.
                }
                await Store.Exec(c,"UPDATE workbook_import SET status='Committed' WHERE id=@p0",id);await Store.Audit(c,company(h),actor(h),"Reviewed workbook migration committed",id,new{kind=batch.Text("kind"),created,sourceHash=batch.Text("hash"),review=b.Text("review_reference")});return new{created,message="Reviewed workbook committed. Source outstanding and total rows were not posted as extra receivables.",masters};
            });
        });
    }
}

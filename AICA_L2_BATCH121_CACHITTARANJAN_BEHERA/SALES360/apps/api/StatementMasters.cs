using System.Globalization;
using System.Text.Json.Nodes;
using System.Text.RegularExpressions;
using Npgsql;
using Sales360.Domain;
namespace Sales360.Api;
public static class StatementMasters
{
    static string Key(string value)=>Regex.Replace(value.Trim(),@"\s+"," ").ToUpperInvariant();
    static string Trn(JsonNode m)=>Regex.IsMatch(m.Text("client_trn_raw"),"^[0-9]{15}$")?m.Text("client_trn_raw"):"";
    public static JsonNode[] Parts(JsonNode payload)=>payload["statements"] is JsonArray list?list.Select(x=>x!).ToArray():[payload];
    static Task<JsonArray> Customers(NpgsqlConnection c,string company,JsonNode m)=>Store.Rows(c,"SELECT * FROM customer WHERE company_id=@p0 AND ((@p1<>'' AND lower(code)=lower(@p1)) OR (@p2<>'' AND trn=@p2) OR regexp_replace(upper(trim(name)),'[[:space:]]+',' ','g')=@p3) ORDER BY id",company,m.Text("customer_code"),Trn(m),Key(m.Text("client_name")));
    static Task<JsonArray> Projects(NpgsqlConnection c,string company,JsonNode m)=>Store.Rows(c,"SELECT * FROM project WHERE company_id=@p0 AND lower(trim(code))=lower(@p1) ORDER BY id",company,m.Text("project_no"));
    static string Category(JsonNode payload,JsonNode metadata,JsonArray errors)
    {
        var related=Parts(payload).Where(p=>Key(p["metadata"]!.Text("project_no"))==Key(metadata.Text("project_no"))).ToArray();
        var supplied=related.Select(p=>p["metadata"]!.Text("project_category")).Where(v=>v!="").Distinct().ToArray();
        if(supplied.Length>1)errors.Add("Conflicting project categories for "+metadata.Text("project_no")+".");
        if(supplied.Length>0){if(!Billing.Categories.Contains(supplied[0]))errors.Add("Use a supported project category for "+metadata.Text("project_no")+".");else return supplied[0];}
        var categories=related.SelectMany(p=>p["rows"]!.AsArray()).Select(r=>r!.Text("fee_type")=="Authority"?"Authority Fees":r!.Text("fee_type")).Distinct().ToArray();return categories.Length==1&&Billing.Categories.Contains(categories[0])?categories[0]:"Other Services";
    }
    static decimal Fee(JsonNode payload,JsonNode metadata,JsonArray errors)
    {
        var supplied=Parts(payload).Where(p=>Key(p["metadata"]!.Text("project_no"))==Key(metadata.Text("project_no"))).Select(p=>p["metadata"]!.Text("project_fee")).Where(v=>v!="").Distinct().ToArray();decimal result=0;
        foreach(var value in supplied){if(!decimal.TryParse(value,NumberStyles.Number|NumberStyles.AllowExponent,CultureInfo.InvariantCulture,out var parsed)||parsed<=0||parsed>9999999999999999m){errors.Add("Approved contract fee must be positive, or leave it blank for later review: "+metadata.Text("project_no"));continue;}parsed=Billing.Money(parsed);if(result!=0&&result!=parsed)errors.Add("Conflicting contract fees across sheets for "+metadata.Text("project_no")+".");result=parsed;}
        return result;
    }
    public static async Task<JsonArray> Plan(NpgsqlConnection c,string company,JsonNode payload,JsonArray errors,JsonArray warnings)
    {
        var result=new JsonArray();var names=new Dictionary<string,string>();var taxes=new Dictionary<string,string>();var projectOwners=new Dictionary<string,string>();var codeOwners=new Dictionary<string,string>();var nameCodes=new Dictionary<string,string>();
        foreach(var part in Parts(payload)){
            var m=part["metadata"]!;var name=m.Text("client_name");var code=m.Text("project_no");var tax=Trn(m);
            if(projectOwners.TryGetValue(Key(code),out var owner)&&owner!=Key(name))errors.Add("The same project code appears for different customers across sheets: "+code);projectOwners[Key(code)]=Key(name);
            if(m.Text("customer_code")!=""){var customerCode=Key(m.Text("customer_code"));if(codeOwners.TryGetValue(customerCode,out var codeOwner)&&codeOwner!=Key(name))errors.Add("The same customer code is assigned to different legal names across sheets.");if(nameCodes.TryGetValue(Key(name),out var priorCode)&&priorCode!=customerCode)errors.Add("The same legal name has different customer codes across sheets.");codeOwners[customerCode]=Key(name);nameCodes[Key(name)]=customerCode;}
            if(name.Length is <2 or >400)errors.Add(m.Text("sheet_name")+": enter a customer legal name in E4 (2-400 characters).");
            if(code.Length is <1 or >80)errors.Add(m.Text("sheet_name")+": enter a project code in B4 (1-80 characters).");
            if(m.Text("customer_code").Length>80)errors.Add("Customer code in L1 is too long.");
            if(m.Text("project_description").Length>400||m.Text("client_address").Length>4000||m.Text("project_location").Length>400)errors.Add("A statement master description/address exceeds the supported length.");
            if(tax!=""){
                if(names.TryGetValue(Key(name),out var previousTax)&&previousTax!=tax)errors.Add("The same customer name has conflicting TRNs across sheets: "+name);names[Key(name)]=tax;
                if(taxes.TryGetValue(tax,out var previousName)&&previousName!=Key(name))errors.Add("Different customer names share a TRN across sheets. Review the legal entity mapping.");taxes[tax]=Key(name);
            }
            if(m.Text("billing_email")!="")try{Accounts.Email(m.Text("billing_email"));}catch(RuleException e){errors.Add(m.Text("sheet_name")+": "+e.Message);}
            var terms=30;if(m.Text("payment_terms")!=""&&(!int.TryParse(m.Text("payment_terms"),out terms)||terms is <0 or >3650)){errors.Add("Payment terms in L3 must be 0-3650 days.");terms=30;}
            var customers=await Customers(c,company,m);var projects=await Projects(c,company,m);var customer=customers.Count==1?customers[0]:null;var project=projects.Count==1?projects[0]:null;
            if(customers.Count>1)errors.Add(m.Text("sheet_name")+": multiple customers match code, TRN or name. Resolve master duplicates before automatic import.");
            if(projects.Count>1)errors.Add(m.Text("sheet_name")+": project code matches several records. Resolve duplicate codes before importing.");
            if(customer!=null&&tax!=""&&customer.Text("trn")!=""&&customer.Text("trn")!=tax)errors.Add("Customer TRN conflicts with the matching master: "+name);
            if(customer!=null&&Key(customer.Text("name"))!=Key(name))errors.Add("Customer code/TRN points to a different legal name. Use reviewed manual mapping or correct E4.");
            if(project!=null&&(customer==null||project.Text("customer_id")!=customer.Text("id")))errors.Add("Project "+code+" belongs to another customer. Correct the workbook or use reviewed manual mapping.");
            var fee=Fee(payload,m,errors);var category=Category(payload,m,errors);
            if(project==null)warnings.Add("Project "+code+" will be created with Needs contract review status. Confirm its contract fee and category in Projects before preparing new certificates.");
            if(project!=null&&fee>0&&project.Decimal("fee")>0&&fee!=project.Decimal("fee"))warnings.Add("Project "+code+": source fee differs from the existing contract fee. The existing fee will be preserved; review any variation separately.");
            if(customer!=null)warnings.Add("Customer "+customer.Text("code")+": matching record will be reused. Missing fields will be filled; existing nonblank fields are preserved unless replacement is explicitly selected.");
            result.Add(new JsonObject{["sheet_name"]=m.Text("sheet_name"),["customer_name"]=name,["customer_code"]=customer?.Text("code")??(m.Text("customer_code")!=""?m.Text("customer_code"):"CUST-"+Store.Hash(Key(name))[..12].ToUpperInvariant()),["customer_id"]=customer?.Text("id")??"",["customer_revision"]=customer?.Integer("revision")??0,["customer_action"]=customer==null?"Create customer":"Update missing fields",["project_code"]=code,["project_name"]=m.Text("project_description")!=""?m.Text("project_description"):code,["project_id"]=project?.Text("id")??"",["project_version"]=project?.Integer("version")??0,["project_action"]=project==null?"Create project - contract review required":"Link / update missing details",["project_category"]=category,["source_contract_fee"]=fee,["existing_contract_fee"]=project?.Decimal("fee")??0,["payment_terms"]=terms,["source_address"]=m.Text("client_address"),["source_trn"]=tax,["source_email"]=m.Text("billing_email")});
        }
        return result;
    }
    public static async Task<JsonObject> Commit(NpgsqlConnection c,string company,string actor,string id,JsonNode batch,JsonObject b)
    {
        var payload=batch["payload"]!;Billing.Require(b["confirm_master_plan"]?.GetValue<bool>()==true,"Review and confirm the customer/project master plan.");
        var errors=new JsonArray();var warnings=new JsonArray();var current=await Plan(c,company,payload,errors,warnings);Billing.Require(errors.Count==0,"Customer/project matching is ambiguous or changed. Refresh the workbook preview and resolve the matching errors.");
        Billing.Require(payload["masterPlan"]!=null&&JsonNode.DeepEquals(payload["masterPlan"],current),"Customer/project masters changed since preview. Preview the same workbook again before committing.");
        var overwrite=b["replace_provided_master_fields"]?.GetValue<bool>()==true;var newCustomers=new HashSet<string>();var updatedCustomers=new HashSet<string>();var newProjects=new HashSet<string>();var updatedProjects=new HashSet<string>();int invoices=0,skipped=0;
        var parts=Parts(payload);
        for(var i=0;i<parts.Length;i++){
            var part=parts[i];var m=part["metadata"]!;var plan=current[i]!;var found=await Customers(c,company,m);Billing.Require(found.Count<=1,"Customer matching became ambiguous.");JsonObject customer;
            var supplied=new JsonObject{["legal_entity_name"]=m.Text("client_name"),["registered_address"]=m.Text("client_address"),["trn"]=Trn(m),["ar_billing_email"]=m.Text("billing_email"),["validation_status"]="Pending"};
            if(found.Count==0){customer=await CustomerMaster.Save(c,company,actor,new JsonObject{["code"]=plan.Text("customer_code"),["terms"]=plan.Integer("payment_terms"),["details"]=supplied});newCustomers.Add(customer.Text("id"));}
            else{
                customer=found[0]!.AsObject();var details=customer["details"]!.DeepClone().AsObject();details["legal_entity_name"]=customer.Text("name");if(details.Text("trn")=="")details["trn"]=customer.Text("trn");if(details.Text("ar_billing_email")=="")details["ar_billing_email"]=customer.Text("email");var changed=false;
                foreach(var key in new[]{"registered_address","trn","ar_billing_email","validation_status"}){var value=supplied.Text(key);if(value!=""&&value!=details.Text(key)&&(details.Text(key)==""||(overwrite&&key!="validation_status"))){details[key]=value;changed=true;}}
                var terms=customer.Integer("terms");if(overwrite&&m.Text("payment_terms")!=""&&terms!=plan.Integer("payment_terms")){terms=plan.Integer("payment_terms");changed=true;}
                if(changed){customer=await CustomerMaster.Save(c,company,actor,new JsonObject{["code"]=customer.Text("code"),["terms"]=terms,["expected_revision"]=customer.Integer("revision"),["details"]=details},customer.Text("id"));updatedCustomers.Add(customer.Text("id"));}
            }
            var existing=await Projects(c,company,m);Billing.Require(existing.Count<=1,"Project matching became ambiguous.");JsonObject project;
            if(existing.Count==0){
                var projectId=Guid.NewGuid().ToString("N");await Store.Exec(c,"INSERT INTO project(id,company_id,customer_id,code,name,category,fee,status,location,stages) VALUES(@p0,@p1,@p2,@p3,@p4,@p5,@p6,'Needs contract review',@p7,@p8::jsonb)",projectId,company,customer.Text("id"),m.Text("project_no"),plan.Text("project_name"),plan.Text("project_category"),plan.Decimal("source_contract_fee"),m.Text("project_location"),Seed.Stages());project=await Store.One(c,"SELECT * FROM project WHERE id=@p0",projectId);newProjects.Add(projectId);await Store.Audit(c,company,actor,"SOA project created",projectId,new{importId=id,fee=project.Decimal("fee"),status=project.Text("status"),contractReviewRequired=true});
            }else{
                project=existing[0]!.AsObject();Billing.Require(project.Text("customer_id")==customer.Text("id"),"Project belongs to a different customer.");var name=project.Text("name");var location=project.Text("location");var fee=project.Decimal("fee");var category=project.Text("category");
                if(m.Text("project_description")!=""&&(name==""||name==project.Text("code")||overwrite))name=m.Text("project_description");if(m.Text("project_location")!=""&&(location==""||overwrite))location=m.Text("project_location");if(fee==0&&plan.Decimal("source_contract_fee")>0)fee=plan.Decimal("source_contract_fee");
                if(name!=project.Text("name")||location!=project.Text("location")||fee!=project.Decimal("fee")){var before=project.DeepClone();await Store.Exec(c,"UPDATE project SET name=@p0,location=@p1,fee=@p2,version=version+1 WHERE id=@p3",name,location,fee,project.Text("id"));project=await Store.One(c,"SELECT * FROM project WHERE id=@p0",project.Text("id"));updatedProjects.Add(project.Text("id"));await Store.Audit(c,company,actor,"SOA project details updated",project.Text("id"),new{importId=id,before,after=project});}
            }
            var posted=await WorkbookImports.PostRows(c,company,actor,id,batch,part,project,customer,b,true);invoices+=posted.Created;skipped+=posted.Skipped;if(posted.Created>0){await Store.Exec(c,"UPDATE project SET status='Needs contract review',opening_assessments='[]',opening_net=0,opening_review_reference='',version=version+1 WHERE id=@p0",project.Text("id"));await Store.Audit(c,company,actor,"SOA project opening review required",project.Text("id"),new{importId=id,newInvoices=posted.Created});}
        }
        return new JsonObject{["customers_created"]=newCustomers.Count,["customers_updated"]=updatedCustomers.Except(newCustomers).Count(),["projects_created"]=newProjects.Count,["projects_updated"]=updatedProjects.Except(newProjects).Count(),["invoices_created"]=invoices,["invoices_unchanged"]=skipped};
    }
}

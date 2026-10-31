using System.Text.Json.Nodes;
using System.Xml;
using System.Xml.Linq;
using System.Text;
using Sales360.Domain;
namespace Sales360.Api;
public static class SupportTools
{
    public static void Map(RouteGroupBuilder api,Store store,string root,string data)
    {
        api.MapGet("/support/diagnostics",async(HttpContext h)=>{
            Accounts.Administrator(h);var checks=new List<object>();await using var c=await store.Open();
            checks.Add(new{name="Database",status="OK",advice="Connection successful. Never delete database files to repair a startup error."});
            foreach(var file in new[]{"host/Sales360.Api.exe","apps/web/dist/index.html","scripts/render_pdf.py","runtime/python/python.exe"})checks.Add(new{name=file,status=File.Exists(Path.Combine(root,file))?"OK":"Missing",advice="If missing, stop SALES360 and rerun the same installer in the same program folder. Keep your separate data folder."});
            foreach(var folder in new[]{"keys","documents","generated","identity-mail"})checks.Add(new{name=folder,status=Directory.Exists(Path.Combine(data,folder))?"Present":"Created when required",advice="Do not remove protected keys or originals. Use Backup-SALES360.bat after stopping the application."});
            var negative=(await Store.One(c,$"SELECT count(*) AS count FROM invoice i WHERE company_id=@p0 AND ({Corrections.OpenSql("i","'9999-12-31'::date")})<0",Accounts.Company(h))).Integer("count");
            checks.Add(new{name="Receivables integrity",status=negative==0?"OK":"Review needed",advice=negative==0?"No negative invoice balances found.":"Ask Finance to reconcile allocations and corrections; automatic ledger changes are disabled."});
            return new{version="0.6.0",checks,repairScope="Repair creates missing transient folders only. It never changes financial records, authentication keys or original documents.",startupAdvice="If the program cannot open: run Repair-SALES360.bat, read the local logs, stop conflicting instances, and rerun the installer if files are missing. Restore a verified backup to a new folder if data is damaged."};
        });
        api.MapPost("/support/repair",async(HttpContext h)=>{Accounts.Administrator(h);foreach(var folder in new[]{"generated","identity-mail"})Directory.CreateDirectory(Path.Combine(data,folder));await store.Transaction(Accounts.Company(h),async c=>{await Store.Audit(c,Accounts.Company(h),Accounts.Actor(h),"Safe repair performed","support",new{folders=new[]{"generated","identity-mail"},financialDataChanged=false});return 0;});return new{message="Transient folders checked and restored if missing. Refresh the page. If a problem remains, follow the diagnostics advice or rerun the installer after stopping SALES360."};});
        api.MapPost("/utility/tally/test",async(HttpContext h,JsonObject b)=>{
            Accounts.Administrator(h);var port=b.Integer("port");Billing.Require(port is >=1024 and <=65000,"Enter a local Tally port between 1024 and 65000.");
            // Fixed loopback, fixed read-only XML, no redirects or user-supplied URLs/payloads.
            using var client=new HttpClient(new HttpClientHandler{AllowAutoRedirect=false,UseProxy=false}){Timeout=TimeSpan.FromSeconds(5)};
            try{
                using var request=new HttpRequestMessage(HttpMethod.Post,$"http://127.0.0.1:{port}"){Content=new StringContent("<ENVELOPE><HEADER><VERSION>1</VERSION><TALLYREQUEST>Export</TALLYREQUEST><TYPE>Collection</TYPE><ID>List of Companies</ID></HEADER><BODY><DESC><STATICVARIABLES><SVEXPORTFORMAT>$$SysName:XML</SVEXPORTFORMAT></STATICVARIABLES></DESC></BODY></ENVELOPE>",Encoding.UTF8,"text/xml")};
                using var timeout=new CancellationTokenSource(TimeSpan.FromSeconds(5));using var response=await client.SendAsync(request,HttpCompletionOption.ResponseHeadersRead,timeout.Token);Billing.Require(response.IsSuccessStatusCode,"The local service rejected the Tally request. Check the configured Tally port.");
                await using var stream=await response.Content.ReadAsStreamAsync(timeout.Token);using var limited=new MemoryStream();var buffer=new byte[8192];int n;while((n=await stream.ReadAsync(buffer,timeout.Token))>0){Billing.Require(limited.Length+n<=2*1024*1024,"Tally response too large.");limited.Write(buffer,0,n);}limited.Position=0;
                using var reader=XmlReader.Create(limited,new XmlReaderSettings{DtdProcessing=DtdProcessing.Prohibit,XmlResolver=null,MaxCharactersInDocument=2*1024*1024});var xml=XDocument.Load(reader);Billing.Require(xml.Root?.Name.LocalName=="ENVELOPE","The service did not return a Tally XML envelope.");
                Billing.Require(!xml.Descendants().Any(x=>x.Name.LocalName is "LINEERROR" or "ERROR"),"Tally returned an error. Load a company and confirm XML integration is enabled.");
                var companies=xml.Descendants().Where(x=>x.Name.LocalName=="COMPANY").Select(x=>x.Attribute("NAME")?.Value??x.Element("NAME")?.Value??"").Where(x=>x!="").Distinct().ToArray();
                Billing.Require(companies.Length>0,"Tally responded, but no company was returned. Load a company and confirm access.");return Results.Ok(new{message="Local Tally connection verified. Read-only company query; no vouchers posted.",companies});
            }catch(HttpRequestException){return Results.Json(new{error="Tally is unavailable on this PC/port. Start Tally, load a company and enable its HTTP/XML server (usually port 9000)."},statusCode:409);}catch(TaskCanceledException){return Results.Json(new{error="Local Tally query timed out. Check Tally and its port."},statusCode:409);}catch(XmlException){return Results.Json(new{error="Local service returned invalid XML. Confirm this is the Tally port."},statusCode:409);}
        });
        api.MapGet("/utility/tally/customers.xml",async(HttpContext h)=>{
            Accounts.Administrator(h);await using var c=await store.Open();var customers=await Store.Rows(c,"SELECT code,name,trn,email FROM customer WHERE company_id=@p0 ORDER BY code",Accounts.Company(h));
            Billing.Require(customers.Select(r=>r!.Text("name").Trim().ToUpperInvariant()).Distinct().Count()==customers.Count,"Duplicate customer legal names need reviewed Tally ledger mapping before XML export. Export the full Excel master for reconciliation.");
            var messages=customers.Select(r=>new XElement("TALLYMESSAGE",new XElement("LEDGER",new XAttribute("NAME",r!.Text("name")),new XAttribute("ACTION","Create"),new XElement("NAME",r.Text("name")),new XElement("PARENT","Sundry Debtors"),new XElement("ISBILLWISEON","Yes"),new XElement("EMAIL",r.Text("email")))));
            var xml=new XDocument(new XElement("ENVELOPE",new XElement("HEADER",new XElement("TALLYREQUEST","Import Data")),new XElement("BODY",new XElement("IMPORTDATA",new XElement("REQUESTDESC",new XElement("REPORTNAME","All Masters")),new XElement("REQUESTDATA",messages)))));
            return Results.File(Encoding.UTF8.GetBytes(xml.ToString()),"application/xml","SALES360-Tally-customer-masters-review.xml");
        });
    }
}

using System.Net;
using System.Net.Http.Headers;
using System.Text.Json;
using Microsoft.AspNetCore.DataProtection;
using Sales360.Domain;

namespace Sales360.Api;

public sealed class IdentityMail : BackgroundService
{
    readonly Store store;readonly IDataProtector protector;readonly string directory;readonly HttpClient http=new(){Timeout=TimeSpan.FromSeconds(25)};readonly string mode;
    public string SignupCompany{get;}
    public string BaseUrl{get;}
    public bool Enabled{get;}
    public bool IsOffline=>mode=="Offline";
    public string MailboxDirectory=>directory;
    public string PublicStatus=>IsOffline?"Offline local mailbox (no internet required)":!Enabled?"Microsoft 365 not configured":mode=="Pickup"?"Local test mailbox (no email sent)":"Microsoft 365 / Outlook";
    public IdentityMail(Store store,IDataProtectionProvider protection,IWebHostEnvironment environment,string data)
    {
        this.store=store;protector=protection.CreateProtector("SALES360.IdentityMail.v1");directory=Path.Combine(data,"identity-mail");
        mode=Environment.GetEnvironmentVariable("SALES360_MAIL_MODE")??(environment.IsDevelopment()?"Pickup":"Graph");
        Billing.Require(mode is "Graph" or "Pickup" or "Offline","SALES360_MAIL_MODE must be Graph, Pickup or Offline.");Billing.Require(mode!="Pickup"||environment.IsDevelopment(),"Local mail pickup is allowed only in Development.");
        Enabled=mode is "Pickup" or "Offline"||new[]{"SALES360_GRAPH_TENANT_ID","SALES360_GRAPH_CLIENT_ID","SALES360_GRAPH_CLIENT_SECRET","SALES360_MAIL_FROM","SALES360_PUBLIC_URL"}.All(x=>!string.IsNullOrWhiteSpace(Environment.GetEnvironmentVariable(x)));
        SignupCompany=Environment.GetEnvironmentVariable("SALES360_SIGNUP_COMPANY")??(Environment.GetEnvironmentVariable("SALES360_SEED")=="1"?"demo":"");
        BaseUrl=(Environment.GetEnvironmentVariable("SALES360_PUBLIC_URL")??"http://127.0.0.1:5080").TrimEnd('/');
        Billing.Require(Uri.TryCreate(BaseUrl,UriKind.Absolute,out var url)&&url.UserInfo==""&&url.Query==""&&url.Fragment==""&&url.AbsolutePath=="/"&&(url.Scheme=="https"||(environment.IsDevelopment()||IsOffline)&&url.Scheme=="http"&&url.IsLoopback),"SALES360_PUBLIC_URL must be a trusted HTTPS origin (loopback HTTP is allowed for a local offline installation).");
        if(mode=="Graph"&&Enabled){Billing.Require(Guid.TryParse(Environment.GetEnvironmentVariable("SALES360_GRAPH_TENANT_ID"),out _)&&Guid.TryParse(Environment.GetEnvironmentVariable("SALES360_GRAPH_CLIENT_ID"),out _),"Microsoft tenant and client IDs must be GUIDs.");Accounts.Email(Environment.GetEnvironmentVariable("SALES360_MAIL_FROM")!);}
    }
    public string Protect(string payload)=>protector.Protect(payload);
    protected override async Task ExecuteAsync(CancellationToken stoppingToken)
    {
        if(!Enabled)return;
        // An interrupted send may already have reached the provider: never blindly replay it.
        while(!stoppingToken.IsCancellationRequested)
        {
            try {await Deliver(stoppingToken);}catch(OperationCanceledException) when(stoppingToken.IsCancellationRequested){break;}catch{Console.Error.WriteLine("Identity mail worker failed; check database and protected mail configuration. No credentials or link tokens are logged.");}
            try{await Task.Delay(1000,stoppingToken);}catch(OperationCanceledException){break;}
        }
    }
    async Task Deliver(CancellationToken cancellation)
    {
        await using var c=await store.Open();await Store.Exec(c,"UPDATE identity_mail SET state='Uncertain',error_code='Interrupted send; operator reconciliation required',updated_at=now() WHERE state='Sending' AND updated_at<now()-interval '2 minutes'");var rows=await Store.Rows(c,"SELECT * FROM identity_mail WHERE state='Pending' AND attempts<5 AND updated_at<=now() ORDER BY created_at LIMIT 1");if(rows.Count==0)return;var row=rows[0]!;var id=row.Text("id");
        IdentityMessage message;
        try{message=JsonSerializer.Deserialize<IdentityMessage>(protector.Unprotect(row.Text("encrypted_payload")))!;}catch{await Store.Exec(c,"UPDATE identity_mail SET state='Failed',error_code='Protected payload unavailable',updated_at=now() WHERE id=@p0",id);return;}
        string? accessToken=null;
        if(mode=="Graph")
        {
            try{
                using var tokenResponse=await http.PostAsync("https://login.microsoftonline.com/"+Environment.GetEnvironmentVariable("SALES360_GRAPH_TENANT_ID")+"/oauth2/v2.0/token",new FormUrlEncodedContent(new Dictionary<string,string>{{"client_id",Environment.GetEnvironmentVariable("SALES360_GRAPH_CLIENT_ID")!},{"client_secret",Environment.GetEnvironmentVariable("SALES360_GRAPH_CLIENT_SECRET")!},{"scope","https://graph.microsoft.com/.default"},{"grant_type","client_credentials"}}),cancellation);
                if(!tokenResponse.IsSuccessStatusCode){await Retry(c,id,"Microsoft token request rejected");return;}using var json=JsonDocument.Parse(await tokenResponse.Content.ReadAsStringAsync(cancellation));accessToken=json.RootElement.GetProperty("access_token").GetString();
            }catch(OperationCanceledException) when(cancellation.IsCancellationRequested){throw;}catch{await Retry(c,id,"Microsoft authentication unavailable");return;}
        }
        var claimed=await Store.Exec(c,"UPDATE identity_mail SET state='Sending',attempts=attempts+1,updated_at=now() WHERE id=@p0 AND state='Pending'",id);if(claimed==0)return;
        try
        {
            if(mode is "Pickup" or "Offline"){
                Directory.CreateDirectory(directory);await File.WriteAllTextAsync(Path.Combine(directory,id+".eml"),$"From: SALES360 <no-reply@sales360.example.invalid>\r\nTo: {message.To}\r\nSubject: {message.Subject}\r\nDate: {DateTimeOffset.UtcNow:R}\r\nMessage-ID: <{id}@sales360.local>\r\nMIME-Version: 1.0\r\nContent-Type: text/plain; charset=utf-8\r\nContent-Transfer-Encoding: 8bit\r\n\r\n{message.Body}",cancellation);
                await Store.Exec(c,"UPDATE identity_mail SET state='Local mailbox',encrypted_payload='',provider_reference=@p0,updated_at=now() WHERE id=@p1",id+".eml",id);return;
            }
            var sender=Accounts.Email(Environment.GetEnvironmentVariable("SALES360_MAIL_FROM")!);using var request=new HttpRequestMessage(HttpMethod.Post,"https://graph.microsoft.com/v1.0/users/"+Uri.EscapeDataString(sender)+"/sendMail");request.Headers.Authorization=new AuthenticationHeaderValue("Bearer",accessToken);request.Headers.Add("client-request-id",id);request.Content=JsonContent.Create(new{message=new{subject=message.Subject,body=new{contentType="Text",content=message.Body},toRecipients=new[]{new{emailAddress=new{address=message.To}}}},saveToSentItems=true});
            using var response=await http.SendAsync(request,cancellation);
            if(response.StatusCode==HttpStatusCode.Accepted){await Store.Exec(c,"UPDATE identity_mail SET state='Accepted by Microsoft',encrypted_payload='',provider_reference=@p0,updated_at=now() WHERE id=@p1",response.Headers.TryGetValues("request-id",out var ids)?ids.First():id,id);return;}
            if((int)response.StatusCode==429){await Retry(c,id,"Microsoft throttled request",false);return;}
            await Store.Exec(c,"UPDATE identity_mail SET state=@p0,error_code=@p1,updated_at=now() WHERE id=@p2",(int)response.StatusCode>=500?"Uncertain":"Failed","Graph HTTP "+(int)response.StatusCode,id);
        }
        catch{await Store.Exec(c,"UPDATE identity_mail SET state='Uncertain',error_code='Send outcome unknown; reconcile before any retry',updated_at=now() WHERE id=@p0",id);}
    }
    static Task<int> Retry(Npgsql.NpgsqlConnection c,string id,string reason,bool increment=true)=>Store.Exec(c,"UPDATE identity_mail SET state=CASE WHEN attempts+@p2>=5 THEN 'Failed' ELSE 'Pending' END,attempts=attempts+@p2,error_code=@p0,updated_at=now()+interval '2 minutes' WHERE id=@p1",reason,id,increment?1:0);
    public override void Dispose(){http.Dispose();base.Dispose();}
}

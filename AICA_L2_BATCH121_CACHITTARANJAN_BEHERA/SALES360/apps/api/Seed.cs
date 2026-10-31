using System.Text.Json;
using Sales360.Domain;
namespace Sales360.Api;
public static class Seed
{
    public static string Stages()=>JsonSerializer.Serialize(new[]{new Stage("Advance Payment",10,0,0,0),new Stage("Concept Design",10,0,0,0),new Stage("Schematic Design",25,0,0,0),new Stage("Detailed Design",35,0,0,0),new Stage("Tender Documents",10,0,0,0),new Stage("Authorities Preliminary Approval",5,0,0,0),new Stage("Authorities Final Approval",5,0,0,0)});
    public static async Task Run(Store store,string data)
    {
        await store.Transaction("demo",async c=>{
            if((await Store.Rows(c,"SELECT id FROM company WHERE id='demo'")).Count>0)return 0;
            await Store.Exec(c,"INSERT INTO company(id,name) VALUES('demo','Meridian Engineering · Demonstration'); INSERT INTO numbering(company_id) VALUES('demo')");
            var credentials=new List<string>{"SALES360 local synthetic demonstration only. Generated once. Keep private.","Username | Password | Role"};
            foreach(var (id,role,name) in new[]{("preparer","Accountant","Amina Hassan"),("reviewer1","Reviewer 1","Omar Khalid"),("reviewer2","Reviewer 2","Leila Mansour"),("approver","Approver","Rashid Saleh"),("finance","Finance Administrator","Sara Ahmed"),("admin","System Administrator","System Administrator"),("auditor","Auditor","Independent Auditor")}) {
                var password=Convert.ToBase64String(System.Security.Cryptography.RandomNumberGenerator.GetBytes(18));credentials.Add($"{id} | {password} | {role}");await Store.Exec(c,"INSERT INTO app_user(id,company_id,name,role,password_hash,access_role) VALUES(@p0,'demo',@p1,@p2,@p3,@p4)",id,name,role,Store.Password(password),role=="System Administrator"?"Administrator":role=="Finance Administrator"?"Super user":"User");
            }
            await File.WriteAllLinesAsync(Path.Combine(data,"demo-access.txt"),credentials);
            string[] names=["Al Noor Development","Crescent Properties","Harbour Urban Group","Dune Estates","Palm Gate Holdings","Oasis Communities","Northline Developers","Safa Living","Atlas Investments","Coastal Assets","Al Waha Group","Summit Real Estate"];
            for(var i=0;i<names.Length;i++)await Store.Exec(c,"INSERT INTO customer(id,company_id,code,name,email) VALUES(@p0,'demo',@p1,@p2,@p3)","c"+i,"CUS-"+(i+1).ToString("D3"),names[i],"billing"+i+"@example.invalid");
            string[] types=["Residences","Commercial Tower","Community Centre","Waterfront Villas","Business Park","Cultural District","Mixed Use Development","Urban Masterplan"];
            for(var i=0;i<1000;i++) {var id="p"+i;var code=i==0?"729":(1000+i).ToString();var name=i==0?"Al Noor Waterfront Residences":names[i%12].Split(' ')[0]+" "+types[i%8]+" · "+(i/8+1).ToString("D2");await Store.Exec(c,"INSERT INTO project(id,company_id,customer_id,code,name,category,fee,location,stages) VALUES(@p0,'demo',@p1,@p2,@p3,@p4,@p5,@p6,@p7::jsonb)",id,"c"+(i%12),code,name,Billing.Categories[i%5],i==0?3800000m:500000m+i*17500,"Dubai, UAE",Stages());}
            // Three immutable previously certified claims matching the supplied regression fixture.
            var dates=new[]{new DateOnly(2025,4,28),new DateOnly(2025,11,28),new DateOnly(2026,2,10)};var amounts=new[]{380000m,380000m,190000m};decimal cumulative=0;
            for(var i=0;i<3;i++) {var lines=JsonSerializer.Deserialize<List<Stage>>(Stages())!;lines[0]=lines[0] with{Claimed=100,Assessed=100,Previous=i==0?0:100};if(i>=1)lines[1]=lines[1] with{Claimed=100,Assessed=100,Previous=i==1?0:100};if(i>=2)lines[5]=lines[5] with{Claimed=100,Assessed=100,Previous=0};cumulative+=amounts[i];var json=JsonSerializer.Serialize(lines);
                await Store.Exec(c,"INSERT INTO certificate(id,company_id,project_id,customer_id,reference,state,prepared_by,claim_date,due_date,fee,stages,cumulative,previous,settlement,snapshot_hash,approvals) VALUES(@p0,'demo','p0','c0',@p1,'Approved','preparer',@p2,@p3,3800000,@p4::jsonb,@p5,@p6,@p7,@p8,'[]')","history"+i,"DES/729/0"+(i+1),dates[i],dates[i].AddDays(30),json,cumulative,cumulative-amounts[i],amounts[i],Store.Hash(json));
            }
            for(var i=0;i<60;i++) {var p=i%40;var net=50000m+i*3350;var issue=new DateOnly(2026,1,10).AddDays(i*4);await Store.Exec(c,"INSERT INTO invoice(id,company_id,project_id,customer_id,reference,issue_date,due_date,net,vat,total,category,confirmation) VALUES(@p0,'demo',@p1,@p2,@p3,@p4,@p5,@p6,@p7,@p8,@p9,'{\"fixture\":true}')","i"+i,"p"+p,"c"+(p%12),"DEMO/2026/"+(i+1).ToString("D4"),issue,issue.AddDays(30),net,Billing.Money(net*.05m),net+Billing.Money(net*.05m),Billing.Categories[p%5]);
                if(i%3!=0) {var amount=Billing.Money((net+net*.05m)*(i%3==1?1m:.45m));await Store.Exec(c,"INSERT INTO receipt(id,company_id,customer_id,reference,receipt_date,amount,method) VALUES(@p0,'demo',@p1,@p2,@p3,@p4,'Bank transfer')","r"+i,"c"+(p%12),"BANK/DEMO/"+i,issue.AddDays(20),amount);await Store.Exec(c,"INSERT INTO allocation(id,company_id,customer_id,receipt_id,invoice_id,amount,effective_date) VALUES(@p0,'demo',@p1,@p2,@p3,@p4,@p5)","a"+i,"c"+(p%12),"r"+i,"i"+i,amount,issue.AddDays(20));}
            }
            await Store.Audit(c,"demo","system","Synthetic dataset created","demo",new{projects=1000,invoices=60,production=false});return 0;
        });
    }
}

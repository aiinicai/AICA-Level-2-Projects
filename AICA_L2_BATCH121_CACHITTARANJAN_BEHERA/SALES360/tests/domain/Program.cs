using Sales360.Domain;
using System.Text.Json;
var results=new List<object>();var failed=0;
void Test(string name,Action fn){try{fn();Console.WriteLine("PASS "+name);results.Add(new{name,passed=true});}catch(Exception e){failed++;Console.WriteLine("FAIL "+name+": "+e.Message);results.Add(new{name,passed=false,error=e.Message});}}
void Eq<T>(T actual,T expected){if(!EqualityComparer<T>.Default.Equals(actual,expected))throw new Exception($"Expected {expected}, got {actual}");}
void Reject(Action fn){try{fn();}catch(RuleException){return;}throw new Exception("Expected financial rule rejection");}
Stage[] fixture=[new("Advance Payment",10,100,100,100),new("Concept Design",10,100,100,100),new("Schematic Design",25,100,100,0),new("Detailed Design",35,0,0,0),new("Tender Documents",10,0,0,0),new("Authorities Preliminary Approval",5,100,100,100),new("Authorities Final Approval",5,0,0,0)];
Test("AC-08 reference cumulative, previous, settlement",()=>{var a=Billing.Assess(3800000,fixture);Eq(a.Cumulative,1900000m);Eq(a.Previous,950000m);Eq(a.Settlement,950000m);});
Test("AC-08 exact amount in words",()=>Eq(Billing.Words(950000),"AED Nine Hundred Fifty Thousand only."));
Test("AC-22 decimal fils and rounding",()=>{Eq(Billing.Words(125.25m),"AED One Hundred Twenty Five and Twenty Five Fils only.");Eq(Billing.Money(1.005m),1.01m);});
Test("AC-05 approval order",()=>{Eq(Billing.NextApproval("Submitted"),"Reviewer 1");Eq(Billing.NextApproval("Reviewed 1"),"Reviewer 2");Eq(Billing.NextApproval("Reviewed 2"),"Approver");Reject(()=>Billing.NextApproval("Draft"));});
Test("AC-06 no assessment reductions",()=>{var f=fixture.ToArray();f[0]=f[0] with{Assessed=50};Reject(()=>Billing.Assess(3800000,f));});
Test("AC-06 no overclaim or negative completion",()=>{var f=fixture.ToArray();f[1]=f[1] with{Claimed=101};Reject(()=>Billing.Assess(3800000,f));f[1]=f[1] with{Claimed=-1};Reject(()=>Billing.Assess(3800000,f));});
Test("AC-06 approved amount cannot exceed claimed",()=>{var f=fixture.ToArray();f[2]=f[2] with{Claimed=20};Reject(()=>Billing.Assess(3800000,f));});
Test("AC-06 contract allocations total 100",()=>{var f=fixture.ToArray();f[0]=f[0] with{Allocation=20};Reject(()=>Billing.Assess(3800000,f));});
Test("AC-11 allocations cannot overapply cash or AR",()=>{Reject(()=>Billing.Allocate(100,200,101));Reject(()=>Billing.Allocate(200,100,101));Reject(()=>Billing.Allocate(100,100,0));Billing.Allocate(100,100,100);});
Test("AC-12 aging boundaries and leap day",()=>{var d=new DateOnly(2024,2,29);Eq(Billing.AgingBucket(d,d),0);foreach(var (days,bucket) in new[]{(1,1),(30,1),(31,2),(60,2),(61,3),(90,3),(91,4)})Eq(Billing.AgingBucket(d,d.AddDays(days)),bucket);});
Test("AC-13 exact five service categories",()=>Eq(string.Join(";",Billing.Categories),"Design;Supervision;Overtime Claims;Authority Fees;Other Services"));
Directory.CreateDirectory("test-results");File.WriteAllText("test-results/domain.json",JsonSerializer.Serialize(new{at=DateTimeOffset.UtcNow,failed,results},new JsonSerializerOptions{WriteIndented=true}));return failed>0?1:0;

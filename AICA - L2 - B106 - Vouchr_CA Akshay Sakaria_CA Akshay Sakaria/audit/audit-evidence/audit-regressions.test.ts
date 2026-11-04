import { describe, it, expect, vi } from 'vitest';
import type { State } from '../data/store';
import type { Expense, Payment } from '../data/types';
const harness = vi.hoisted(() => ({ state: null as unknown as State, pending: [] as ((s:State)=>State)[] }));
vi.mock('react', () => ({
 createContext:()=>({Provider:'provider'}), useContext:()=>null,
 useState:()=>[harness.state,(fn:(s:State)=>State)=>harness.pending.push(fn)],
 useEffect:()=>{},useCallback:(fn:unknown)=>fn,useMemo:(fn:()=>unknown)=>fn()
}));
import { StoreProvider } from '../data/store';
import { outstanding } from './alerts';
import { previewApply, suggestAdvanceTds } from './tdsAdvance';
import { suggestTds } from './rules';
import { carryForward } from './fyClose';
import { docFolder } from './storage';
import { reconcile } from './reco';
import { parseEInvoiceQr } from './einvoiceQr';
const expense=(patch:Partial<Expense>={}):Expense=>({id:'e1',clientId:'c1',vendorId:'v1',vendorName:'Vendor',invoiceNo:'B1',invoiceDate:'2026-11-03',fyLabel:'2026-27',entrySource:'manual',grossAmount:1000,discount:0,taxableValue:1000,cgst:0,sgst:0,igst:0,totalAmount:1000,tdsAmount:0,rcmApplicable:false,rcmTax:0,status:'submitted',isBackdated:false,createdBy:'u1',createdAt:'2026-11-03T00:00:00Z',...patch});
const payment=(patch:Partial<Payment>={}):Payment=>({id:'p1',clientId:'c1',vendorId:'v1',vendorName:'Vendor',mode:'cash',paidOn:'2026-11-03',amount:1000,allocations:[],isBackdated:false,createdBy:'u1',createdAt:'2026-11-03T00:00:00Z',...patch});
function store(e=expense(),p:Payment[]=[]){
 harness.state={clients:[{id:'c1',name:'Audit',brandColor:'#123456',tallyMode:'none',backdateWindowDays:0,bankAccounts:[],cashLedger:'Cash',defaultCreditDays:30,cashLimitPerDay:10000,noteAboveAmount:25000,costCentres:[]}],users:[{id:'u1',name:'Admin',role:'client_admin',clientId:'c1'}],vendors:[{id:'v1',clientId:'c1',name:'Vendor',gstRegistered:false}],expenses:[e],payments:p,challans:[],recoRuns:[],heads:[],tdsRates:[],monthLocks:[],audit:[],events:[],jobs:[],providers:[],sources:[],findings:[],currentUserId:'u1',lang:'en',consents:[],privacyRequests:[],firm:{name:'Audit'},vendorNotes:[],itcReversals:[],fyCloses:[]};
 harness.pending=[];
 return StoreProvider({children:null}).props.value;
}
function flush(){for(const fn of harness.pending)harness.state=fn(harness.state);harness.pending=[];return harness.state;}
describe('Audit reproductions — assertions describe the observed defect',()=>{
 it('bank-style batch accepts two payments beyond the bill balance',()=>{const s=store();for(let i=0;i<2;i++)s.recordPayment({vendorId:'v1',mode:'cash',paidOn:'2026-11-03',amount:700,allocations:[{expenseId:'e1',amount:700}]});const st=flush();expect(outstanding(st.expenses[0],st.payments)).toBe(-400);});
 it('split payment partially persists when a later line fails',()=>{const s=store();s.recordPayment({vendorId:'v1',mode:'cash',paidOn:'2026-11-03',amount:500,allocations:[]});expect(()=>s.recordPayment({vendorId:'v1',mode:'cash',paidOn:'2099-01-01',amount:500,allocations:[]})).toThrow();expect(flush().payments.length).toBe(1);});
 it('duplicate allocation entries in one payment overpay the bill',()=>{const s=store();s.recordPayment({vendorId:'v1',mode:'cash',paidOn:'2026-11-03',amount:1400,allocations:[{expenseId:'e1',amount:700},{expenseId:'e1',amount:700}]});const st=flush();expect(outstanding(st.expenses[0],st.payments)).toBe(-400);});
 it('applying advances ignores linked credit note value',()=>{const e=expense({noteAdjust:-200});const p=payment();expect(previewApply(e,[],p,1000).after).toBe(0);const s=store(e,[p]);s.applyAdvance('p1','e1',1000);const st=flush();expect(outstanding(st.expenses[0],st.payments)).toBe(-200);});
 it('year close uses payments after the closing date',()=>{const e=expense({invoiceDate:'2027-03-20'});const p=payment({paidOn:'2027-04-10',allocations:[{expenseId:e.id,amount:1000}]});expect(carryForward('2026-27',{expenses:[e],payments:[p],vendorNotes:[]})).toEqual([]);});
 it('expired tax master is still selected by fallback',()=>{const head={id:'h1',name:'Services',tallyLedger:'Services',keywords:[],sacHsnPrefixes:[],defaultTdsCode:'PROF'};const r={code:'PROF',description:'Fees',ratePct:10,effectiveFrom:'2026-04-01',effectiveTo:'2026-09-30',verified:true,sourceNote:''};expect(suggestTds(head,{pan:'AAAPS1234Q'},1000,0,[r],0,'2026-11-03').amount).toBe(100);});
 it('TDS advance threshold includes future FY payments',()=>{const vendor={id:'v1',clientId:'c1',name:'Vendor',gstRegistered:false,pan:'AAAPS1234Q'};const r={code:'PROF',description:'Fees',ratePct:10,thresholdAggregate:50000,effectiveFrom:'2026-04-01',verified:true,sourceNote:''};const future=payment({paidOn:'2027-06-01',tdsOnAdvance:{code:'PROF',ratePct:10,amount:6000,base:60000}});expect(suggestAdvanceTds(vendor,[],[future],[r],1000,'2026-11-03','2026-27','PROF').applies).toBe(true);});
 it('different Hindi client names resolve to the same Drive folder',()=>{expect(docFolder('राम ट्रेडर्स','2026-27','Bills')).toBe(docFolder('श्याम एजेंसी','2026-27','Bills'));});
 it('GST reconciliation includes unsubmitted drafts',()=>{const e=expense({status:'draft',taxableValue:1000,cgst:90,sgst:90,totalAmount:1180});expect(reconcile([e],()=> 'GSTIN',[{supplierGstin:'GSTIN',invoiceNo:'B1',taxableValue:1000,cgst:90,sgst:90,igst:0,cess:0}])[0].status).toBe('matched');});
 it('a signed-QR-shaped credit note is parsed as an expense invoice',()=>{const payload={data:JSON.stringify({SellerGstin:'27AAAPS1234Q1Z1',BuyerGstin:'07OTHER0000X1Z0',DocNo:'CN-1',DocTyp:'CRN',DocDt:'03/11/2026',TotInvVal:1000})};const qr='header.'+Buffer.from(JSON.stringify(payload)).toString('base64url')+'.sig';expect(parseEInvoiceQr(qr)?.docNo).toBe('CN-1');});
});

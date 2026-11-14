import React,{useEffect,useState} from 'react';
type Row=Record<string,any>;
async function call(body?:Row){const response=await fetch('/api/organization',{method:body?'POST':'GET',headers:{'Content-Type':'application/json','X-Sales360-Request':'1'},body:body?JSON.stringify(body):undefined});const result=await response.json();if(!response.ok)throw Error(result.error||'Company settings could not be saved.');return result;}
export function OrganizationSettings({onSaved}:{onSaved:(name:string)=>void}){
 const [record,setRecord]=useState<Row|null>(null),[form,setForm]=useState<Row>({}),[busy,setBusy]=useState(false),[error,setError]=useState(''),[message,setMessage]=useState('');
 const apply=(value:Row)=>{setRecord(value);setForm({legal_name:value.name,invoice_prefix:'INV',review_status:'Draft',period_start:'',period_end:'',...value.profile});};
 const load=async()=>{setBusy(true);setError('');setMessage('');try{apply(await call());}catch(e:any){setError(e.message);}finally{setBusy(false);}};
 useEffect(()=>{load();},[]);
 const save=async(e:React.FormEvent)=>{e.preventDefault();setBusy(true);setError('');setMessage('');try{const value=await call({...form,expected_revision:record?.revision});apply(value);onSaved(value.name);setMessage('Company settings saved. New invoices retain a snapshot of these details; existing posted invoices are unchanged.');}catch(e:any){setError(e.message);}finally{setBusy(false);}};
 const field=(key:string,value:string)=>{setForm(f=>({...f,[key]:value}));setMessage('');};
 const input=(label:string,key:string,required=false)=><label className="field">{label}<input required={required} maxLength={key==='invoice_prefix'?20:200} value={form[key]||''} onChange={e=>field(key,e.target.value)}/></label>;
 const area=(label:string,key:string)=><label className="field">{label}<textarea rows={4} maxLength={key.endsWith('policy')?4000:2000} value={form[key]||''} onChange={e=>field(key,e.target.value)}/></label>;
 return <section className="panel organization-settings"><div className="panel-heading"><div><h2>Company & finance settings</h2><p>Editable legal details and your manually approved policies</p></div><button className="secondary" disabled={busy} onClick={load}>Reload settings</button></div>
 <div className="callout">Enter the real details when ready. Policy text records your decisions and review evidence; it does not automatically calculate advance or retention deductions or certify tax compliance. Keep the status Draft until your finance reviewer approves it.</div>
 {error&&<div role="alert" className="alert error">{error}</div>}{message&&<div role="status" className="alert success">{message}</div>}
 {record&&<form onSubmit={save}><fieldset disabled={busy}><div className="organization-grid">
 {['period_start','period_end'].map(key=><label className="field" key={key}>{key==='period_start'?'Accounting period start':'Accounting period end'}<input required type="date" value={form[key]||''} onChange={e=>field(key,e.target.value)}/></label>)}<p className="muted">Reporting period configuration; historical transactions remain available. This does not close or lock prior periods.</p>{input('Legal / company name','legal_name',true)}{input('TRN (15 digits, if registered)','trn')}
 {area('Registered address','registered_address')}{area('Bank / payment details','bank_details')}
 {input('Invoice number prefix','invoice_prefix',true)}<label className="field">Policy review status<select value={form.review_status} onChange={e=>field('review_status',e.target.value)}><option>Draft</option><option>Reviewed</option></select></label>
 {input('Finance reviewer / approver','finance_approver')}{input('Approval / review reference','approval_reference')}
 {area('VAT policy / treatment instructions','vat_policy')}{area('Advance policy / treatment instructions','advance_policy')}{area('Retention policy / treatment instructions','retention_policy')}
 </div><p className="muted">AED · Asia/Dubai · Revision {record.revision}{record.updated_at?' · Last saved '+new Date(record.updated_at).toLocaleString():''}</p><button className="primary" type="submit">{busy?'Saving…':'Save company settings'}</button></fieldset></form>}
 </section>;
}

import { createFileRoute } from '@tanstack/react-router';
import { useQuery } from '@tanstack/react-query';
import { supabase } from '@/integrations/supabase/client';
import { PageHeader } from '@/components/procurement/PageHeader';
import { StatusBadge } from '@/components/procurement/StatusBadge';
import { ExportFiles } from '@/components/procurement/ExportFiles';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
import { Table, TableBody, TableCell, TableHead, TableHeader, TableRow } from '@/components/ui/table';
import { useAuth } from '@/hooks/useAuth';
import { money, shortDate } from '@/lib/procurement';
export const Route = createFileRoute('/_authenticated/supplier-portal')({
  head: () => ({meta: [{title: "Supplier portal — Easy AI Procura"}, {name: "description", content: "Supplier portal for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Supplier portal — Easy AI Procura"}, {property: "og:description", content: "Supplier portal for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),component: SupplierPortal});
function SupplierPortal() {
 const { user } = useAuth();
 const {data, isLoading, error} = useQuery({queryKey:['supplier-portal',user?.id], queryFn: async () => {
  if(!user) throw new Error('Sign in required');
  const account = await supabase.from('supplier_accounts').select('supplier_id,contact_name,suppliers(supplier_name,status)').eq('user_id',user.id).maybeSingle();
  if(account.error) throw account.error;
  if(!account.data || account.data.suppliers?.status !== 'ACTIVE') return null;
  const id = account.data.supplier_id;
  const [lpo,grn,inv] = await Promise.all([
   supabase.from('lpo_header').select('id,lpo_number,lpo_date,status,total_value,delivery_location,lpo_lines(quantity_ordered,unit_price,items(item_code,item_description,unit))').eq('supplier_id',id).order('lpo_date',{ascending:false}),
   supabase.from('grn_header').select('id,grn_number,grn_date,status,receipt_status,delivery_note_no,grn_lines(qty_ordered,qty_received,item_condition,items(item_code,item_description,unit))').eq('supplier_id',id).order('grn_date',{ascending:false}),
   supabase.from('invoices').select('id,internal_number,invoice_number,invoice_date,status,total_value,invoice_lines(quantity,invoice_price,items(item_code,item_description,unit))').eq('supplier_id',id).order('invoice_date',{ascending:false}),
  ]);
  for(const result of [lpo,grn,inv]) if(result.error) throw result.error;
  return {account:account.data,lpo:lpo.data ?? [],grn:grn.data ?? [],inv:inv.data ?? []};
 }});
 if(isLoading) return <p>Loading supplier records…</p>;
 if(error) return <p className="text-destructive">{error.message}</p>;
 if(!data) return <div><PageHeader title="Supplier portal"/><p className="text-muted-foreground">Your supplier access is awaiting administrator approval, or your supplier record is inactive.</p></div>;
 return <div><PageHeader title={data.account.suppliers?.supplier_name ?? 'Supplier portal'} subtitle={data.account.contact_name}/>
 <Tabs defaultValue="lpo"><TabsList><TabsTrigger value="lpo">LPOs ({data.lpo.length})</TabsTrigger><TabsTrigger value="grn">GRNs ({data.grn.length})</TabsTrigger><TabsTrigger value="inv">Invoices ({data.inv.length})</TabsTrigger></TabsList>
 <TabsContent value="lpo"><Table><TableHeader><TableRow><TableHead>LPO</TableHead><TableHead>Date</TableHead><TableHead>Status</TableHead><TableHead>Value</TableHead></TableRow></TableHeader><TableBody>{data.lpo.map(h => <TableRow key={h.id}><TableCell><details><summary className="cursor-pointer font-medium text-primary">{h.lpo_number}</summary><p className="mt-2">{h.delivery_location}</p>{h.lpo_lines.map((l,i) => <p key={i} className="mt-2 text-sm">{l.items?.item_code} · {l.items?.item_description} · {l.quantity_ordered} {l.items?.unit} × {money(l.unit_price)}</p>)}</details></TableCell><TableCell>{shortDate(h.lpo_date)}</TableCell><TableCell><StatusBadge status={h.status}/></TableCell><TableCell>{money(h.total_value)}</TableCell></TableRow>)}</TableBody></Table>{!data.lpo.length ? <p className="py-6 text-muted-foreground">No pending or approved orders.</p> : null}</TabsContent>
 <TabsContent value="grn"><ExportFiles filename="supplier-grns" rows={data.grn.flatMap(h=>h.grn_lines.map(l=>({grn_number:h.grn_number,date:h.grn_date,status:h.status,item_code:l.items?.item_code,description:l.items?.item_description,unit:l.items?.unit,ordered:l.qty_ordered,received:l.qty_received,condition:l.item_condition})))}/><Table><TableHeader><TableRow><TableHead>GRN</TableHead><TableHead>Date</TableHead><TableHead>Receipt</TableHead><TableHead>Status</TableHead></TableRow></TableHeader><TableBody>{data.grn.map(h=><TableRow key={h.id}><TableCell><details><summary className="cursor-pointer text-primary">{h.grn_number}</summary>{h.grn_lines.map((l,i)=><p key={i} className="mt-2 text-sm">{l.items?.item_code} · {l.items?.item_description} · {l.qty_received}/{l.qty_ordered} {l.items?.unit} · {l.item_condition}</p>)}</details></TableCell><TableCell>{shortDate(h.grn_date)}</TableCell><TableCell><StatusBadge status={h.receipt_status}/></TableCell><TableCell><StatusBadge status={h.status}/></TableCell></TableRow>)}</TableBody></Table></TabsContent>
 <TabsContent value="inv"><Table><TableHeader><TableRow><TableHead>Invoice</TableHead><TableHead>Date</TableHead><TableHead>Status</TableHead><TableHead>Total</TableHead></TableRow></TableHeader><TableBody>{data.inv.map(h=><TableRow key={h.id}><TableCell><details><summary className="cursor-pointer text-primary">{h.invoice_number} · {h.internal_number}</summary>{h.invoice_lines.map((l,i)=><p key={i} className="mt-2 text-sm">{l.items?.item_code} · {l.items?.item_description} · {l.quantity} {l.items?.unit} × {money(l.invoice_price)}</p>)}</details></TableCell><TableCell>{shortDate(h.invoice_date)}</TableCell><TableCell><StatusBadge status={h.status}/></TableCell><TableCell>{money(h.total_value)}</TableCell></TableRow>)}</TableBody></Table></TabsContent>
 </Tabs></div>;
}

import { createFileRoute, Link, useNavigate } from '@tanstack/react-router';
import { useState } from 'react';
import { toast } from 'sonner';
import { supabase } from '@/integrations/supabase/client';
import { Button } from '@/components/ui/button';
import { Input } from '@/components/ui/input';
import { Label } from '@/components/ui/label';
import { Tabs, TabsList, TabsTrigger, TabsContent } from '@/components/ui/tabs';
export const Route = createFileRoute('/supplier-login')({
  head: () => ({meta: [{title: "Supplier login — Easy AI Procura"}, {name: "description", content: "Supplier login for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:title", content: "Supplier login — Easy AI Procura"}, {property: "og:description", content: "Supplier login for purchase orders, goods receipt and supplier invoice control in Easy AI Procura."}, {property: "og:type", content: "website"}, {name: "twitter:card", content: "summary_large_image"}]}),component: SupplierLogin});
function SupplierLogin() {
 const navigate=useNavigate(); const [email,setEmail]=useState(''); const [password,setPassword]=useState(''); const [name,setName]=useState(''); const [busy,setBusy]=useState(false);
 async function submit(register:boolean) {
  setBusy(true);
  try {
   if(register) {
    const {data,error}=await supabase.auth.signUp({email,password,options:{data:{full_name:name,account_type:'supplier'},emailRedirectTo:window.location.origin+'/supplier-login'}});
    if(error) throw error;
    if(data.user && data.user.identities?.length===0) throw new Error('Email already registered. Sign in or reset your password.');
    toast.success('Registration received. Confirm your email, then ask your purchaser to approve supplier access.');
    if(data.session) void navigate({to:'/supplier-portal'});
   } else {
    const {error}=await supabase.auth.signInWithPassword({email,password}); if(error) throw error;
    void navigate({to:'/supplier-portal'});
   }
  } catch(e) {toast.error(e instanceof Error?e.message:'Sign in failed');} finally{setBusy(false);}
 }
 return <div className="mx-auto max-w-md px-4 py-16"><Link to="/" className="text-primary">Easy AI Procura</Link><h1 className="my-6 text-2xl font-semibold">Supplier login</h1>
 <Tabs defaultValue="signin"><TabsList><TabsTrigger value="signin">Sign in</TabsTrigger><TabsTrigger value="register">Register contact</TabsTrigger></TabsList>{['signin','register'].map(mode=><TabsContent key={mode} value={mode}><form className="space-y-4" onSubmit={e=>{e.preventDefault();void submit(mode==='register');}}>
 {mode==='register'?<div><Label htmlFor="supplier-name">Contact name</Label><Input id="supplier-name" required value={name} onChange={e=>setName(e.target.value)}/></div>:null}
 <div><Label htmlFor={mode+'-email'}>Email</Label><Input id={mode+'-email'} type="email" required value={email} onChange={e=>setEmail(e.target.value)}/></div>
 <div><Label htmlFor={mode+'-password'}>Password</Label><Input id={mode+'-password'} type="password" required minLength={6} value={password} onChange={e=>setPassword(e.target.value)}/></div>
 <Button type="submit" disabled={busy}>{busy?'Please wait…':mode==='register'?'Register contact':'Sign in'}</Button>
 <Button type="button" variant="ghost" disabled={busy} onClick={()=>{
 if(!email){toast.error('Enter your email first');return;}
 void supabase.auth.resetPasswordForEmail(email,{redirectTo:window.location.origin+'/reset-password'}).then(({error})=>error?toast.error(error.message):toast.success('Password reset email requested'));
 }}>Forgot password?</Button>
 </form></TabsContent>)}</Tabs></div>;
}

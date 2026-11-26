import { useEffect, useState } from "react";
import { Link } from "@tanstack/react-router";
import { Users, FileCheck2, Clock, UserCheck, Plus, ArrowRight, Activity as ActivityIcon, Briefcase } from "lucide-react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useAuth } from "@/contexts/AuthContext";
import { useTeam } from "@/hooks/useTeam";
import { Badge, Button, Card, CardHeader, EmptyState, PageHeader, Spinner, StatCard } from "@/components/ui";
import { ACTION_LABEL, ENGAGEMENT_STATUS, canEdit } from "@/lib/db";
import { formatDateTime } from "@/lib/format";

interface Dash { clients: number; engagements: number; draft: number; in_review: number; final: number; my_open: number; members: number }

export default function Dashboard() {
  const { firm, role } = useFirm();
  const { profile, user } = useAuth();
  const { nameOf, members } = useTeam();
  const [d, setD] = useState<Dash | null>(null);
  const [recent, setRecent] = useState<any[]>([]);
  const [activity, setActivity] = useState<any[]>([]);
  const [mine, setMine] = useState<any[]>([]);

  useEffect(() => {
    if (!firm) return;
    (async () => {
      const [a, b, c, m] = await Promise.all([
        supabase.rpc("firm_dashboard", { p_firm: firm.id }),
        supabase.from("engagements").select("id, assessment_year, status, updated_at, updated_by, assigned_to, clients(name)").eq("firm_id", firm.id).order("updated_at", { ascending: false }).limit(6),
        supabase.from("activity_log").select("*").eq("firm_id", firm.id).order("created_at", { ascending: false }).limit(8),
        supabase.from("engagements").select("id, assessment_year, status, clients(name)").eq("firm_id", firm.id).eq("assigned_to", user?.id ?? "").neq("status", "final").limit(6),
      ]);
      setD(a.data as unknown as Dash);
      setRecent(b.data ?? []);
      setActivity(c.data ?? []);
      setMine(m.data ?? []);
    })();
  }, [firm, user]);

  const hello = new Date().getHours() < 12 ? "Good morning" : new Date().getHours() < 17 ? "Good afternoon" : "Good evening";

  return (
    <>
      <PageHeader
        title={`${hello}, ${(profile?.full_name || "").split(" ")[0] || "there"}`}
        subtitle={firm?.name}
        actions={canEdit(role) && <Link to="/app/clients" search={{ new: "1" }}><Button icon={<Plus className="h-4 w-4" />}>Add client</Button></Link>}
      />
      {!d ? <div className="flex justify-center py-10"><Spinner /></div> : (
        <div className="grid grid-cols-2 gap-3 lg:grid-cols-4">
          <StatCard label="Active clients" value={d.clients} tone="navy" sub={`${d.engagements} assessment years`} />
          <StatCard label="Draft" value={d.draft} sub="Work in progress" />
          <StatCard label="In review" value={d.in_review} tone={d.in_review ? "warn" : "default"} sub="Awaiting partner review" />
          <StatCard label="Final" value={d.final} tone="good" sub="Locked & ready" />
        </div>
      )}

      <div className="mt-6 grid gap-6 lg:grid-cols-3">
        <Card className="lg:col-span-2">
          <CardHeader title="Recently updated" subtitle="Assessment years across your firm" action={<Link to="/app/clients" className="text-sm font-medium text-navy-700 hover:underline">All clients</Link>} />
          {recent.length === 0 ? (
            <EmptyState icon={<Users className="h-7 w-7" />} title="No clients yet" text="Add your first client, create an assessment year and bring data from Tally or upload a file to prepare Clause 44 and Clause 31."
              action={canEdit(role) && <Link to="/app/clients" search={{ new: "1" }}><Button icon={<Plus className="h-4 w-4" />}>Add first client</Button></Link>} />
          ) : (
            <ul className="divide-y divide-slate-100">
              {recent.map((e) => (
                <li key={e.id}>
                  <Link to="/app/engagements/$engagementId" params={{ engagementId: e.id }} className="flex items-center gap-4 px-5 py-3.5 hover:bg-slate-50">
                    <div className="rounded-lg bg-navy-50 p-2 text-navy-700"><Briefcase className="h-5 w-5" /></div>
                    <div className="min-w-0 flex-1">
                      <div className="truncate font-medium">{e.clients?.name}</div>
                      <div className="text-xs text-slate-500">AY {e.assessment_year} · edited by {nameOf(e.updated_by)} · {formatDateTime(e.updated_at)}</div>
                    </div>
                    <Badge className={ENGAGEMENT_STATUS[e.status]?.cls}>{ENGAGEMENT_STATUS[e.status]?.label}</Badge>
                    <ArrowRight className="hidden h-4 w-4 text-slate-400 sm:block" />
                  </Link>
                </li>
              ))}
            </ul>
          )}
        </Card>

        <div className="space-y-6">
          <Card>
            <CardHeader title={<span className="flex items-center gap-2"><UserCheck className="h-4 w-4" />Assigned to me</span>} />
            {mine.length === 0 ? <p className="px-5 py-6 text-sm text-slate-500">Nothing pending. 🎉</p> : (
              <ul className="divide-y divide-slate-100">
                {mine.map((e) => (
                  <li key={e.id}><Link to="/app/engagements/$engagementId" params={{ engagementId: e.id }} className="flex items-center justify-between px-5 py-3 text-sm hover:bg-slate-50">
                    <span className="truncate">{e.clients?.name} · {e.assessment_year}</span>
                    <Badge className={ENGAGEMENT_STATUS[e.status]?.cls}>{ENGAGEMENT_STATUS[e.status]?.label}</Badge>
                  </Link></li>
                ))}
              </ul>
            )}
          </Card>
          <Card>
            <CardHeader title={<span className="flex items-center gap-2"><ActivityIcon className="h-4 w-4" />Team activity</span>} action={<Link to="/app/activity" className="text-sm font-medium text-navy-700 hover:underline">View all</Link>} />
            {activity.length === 0 ? <p className="px-5 py-6 text-sm text-slate-500">No activity yet.</p> : (
              <ul className="space-y-3 px-5 py-4">
                {activity.map((a) => (
                  <li key={a.id} className="text-sm">
                    <span className="font-medium">{nameOf(a.user_id)}</span> <span className="text-slate-600">{ACTION_LABEL[a.action] ?? a.action}</span>
                    {a.details?.name && <span className="text-slate-600"> · {a.details.name}</span>}
                    <div className="text-xs text-slate-400">{formatDateTime(a.created_at)}</div>
                  </li>
                ))}
              </ul>
            )}
          </Card>
          <Card className="p-5">
            <div className="flex items-center gap-3">
              <Clock className="h-5 w-5 text-navy-700" />
              <div className="text-sm"><b>{members.length}</b> team member{members.length === 1 ? "" : "s"} · <Link to="/app/team" className="font-medium text-navy-700 hover:underline">Manage team</Link></div>
            </div>
            <div className="mt-3 flex items-center gap-3">
              <FileCheck2 className="h-5 w-5 text-navy-700" />
              <div className="text-sm text-slate-600">Tip: Mark a year <b>Final</b> to lock it after partner review.</div>
            </div>
          </Card>
        </div>
      </div>
    </>
  );
}

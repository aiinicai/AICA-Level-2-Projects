import { useEffect, useState } from "react";
import { supabase } from "@/integrations/supabase/client";
import { useFirm } from "@/contexts/FirmContext";
import { useTeam } from "@/hooks/useTeam";
import { Avatar, Button, Card, PageHeader, Select, Spinner } from "@/components/ui";
import { ACTION_LABEL } from "@/lib/db";
import { formatDateTime } from "@/lib/format";

const PAGE = 50;

export default function ActivityPage() {
  const { firm } = useFirm();
  const { members, nameOf } = useTeam();
  const [list, setList] = useState<any[]>([]);
  const [who, setWho] = useState("");
  const [page, setPage] = useState(0);
  const [more, setMore] = useState(false);
  const [loading, setLoading] = useState(true);

  useEffect(() => { setPage(0); setList([]); }, [who, firm?.id]);
  useEffect(() => {
    if (!firm) return;
    setLoading(true);
    let q = supabase.from("activity_log").select("*").eq("firm_id", firm.id).order("created_at", { ascending: false }).range(page * PAGE, page * PAGE + PAGE - 1);
    if (who) q = q.eq("user_id", who);
    q.then(({ data }) => { setList((l) => (page === 0 ? data ?? [] : [...l, ...(data ?? [])])); setMore((data?.length ?? 0) === PAGE); setLoading(false); });
  }, [firm?.id, who, page]);

  const describe = (a: any) => {
    const d = a.details ?? {};
    const bits = [d.name, d.file && `${d.file}${d.rows ? ` (${d.rows} rows)` : ""}`, d.head && `head "${d.head}"`, d.email, d.role, d.reason && `“${d.reason}”`, d.format && String(d.format).toUpperCase(), d.count && `${d.count} items`].filter(Boolean);
    return bits.join(" · ");
  };

  return (
    <>
      <PageHeader title="Activity log" subtitle="Everything your team did, newest first"
        actions={<Select value={who} onChange={(e) => setWho(e.target.value)} className="w-56"><option value="">All members</option>{members.map((m) => <option key={m.user_id} value={m.user_id}>{m.full_name || m.email}</option>)}</Select>} />
      <Card>
        <ul className="divide-y divide-slate-100">
          {list.map((a) => (
            <li key={a.id} className="flex gap-3 px-5 py-3">
              <Avatar name={nameOf(a.user_id)} />
              <div className="text-sm">
                <b>{nameOf(a.user_id)}</b> {ACTION_LABEL[a.action] ?? a.action}
                {describe(a) && <span className="text-slate-600"> · {describe(a)}</span>}
                <div className="text-xs text-slate-500">{formatDateTime(a.created_at)}</div>
              </div>
            </li>
          ))}
        </ul>
        {loading && <div className="flex justify-center py-6"><Spinner /></div>}
        {!loading && !list.length && <p className="px-5 py-8 text-center text-sm text-slate-500">No activity yet.</p>}
        {more && !loading && <div className="border-t border-slate-100 p-3 text-center"><Button variant="ghost" onClick={() => setPage((p) => p + 1)}>Load more</Button></div>}
      </Card>
    </>
  );
}

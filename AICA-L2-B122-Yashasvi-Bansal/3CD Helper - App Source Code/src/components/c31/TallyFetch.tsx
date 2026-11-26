// "Tally से लाएँ" – bring Clause 31 data straight from TallyPrime through the Tally Connector extension.
import { useEffect, useState } from "react";
import { Database, Download, RefreshCw } from "lucide-react";
import { Alert, Button, Card, Input, Select, Spinner, cn } from "@/components/ui";
import { callConnector, connectorVersion, fyOfAy, groupTree, matchCompany, versionAtLeast, GROUPS_VERSION, LOAN_ROOTS, type GroupNode, type TallyCompany, type TallyCounts, type TallyGroup, type TallyMode } from "@/lib/tallyConnector";
import { safeFileName } from "@/lib/export";
import { errMsg } from "@/lib/db";

interface Props {
  ay: string; clientName: string; onFile: (file: File, preset: TallyMode) => void;
  /** Choices offered; Clause 44 needs only the Day Book. */
  modes?: TallyMode[];
}
const MODE_TEXT: Record<TallyMode, [string, string]> = {
  daybook: ["Day Book – everything", "All vouchers come; you tick the loan ledgers next"],
  loans: ["Only loan groups", "You tick the groups (Loans (Liability) and its sub-groups by default); only their ledgers and vouchers leave Tally"],
};

export function TallyFetch({ ay, clientName, onFile, modes = ["daybook", "loans"] }: Props) {
  const [version, setVersion] = useState<string | null>(null);
  const [url, setUrl] = useState("http://localhost:9000");
  const [companies, setCompanies] = useState<TallyCompany[] | null>(null);
  const [company, setCompany] = useState("");
  const fy = fyOfAy(ay);
  const [from, setFrom] = useState(fy.from);
  const [to, setTo] = useState(fy.to);
  const [mode, setMode] = useState<TallyMode>(modes[0]);
  const [busy, setBusy] = useState("");
  const [tree, setTree] = useState<{ company: string; roots: { root: string; nodes: GroupNode[] }[] } | null>(null);
  const [picked, setPicked] = useState<Set<string>>(new Set());
  const [err, setErr] = useState("");

  // the content script marks the page at load; look again shortly in case it was slow
  useEffect(() => {
    const look = () => setVersion(connectorVersion());
    look();
    const t = setTimeout(look, 800);
    return () => clearTimeout(t);
  }, []);
  useEffect(() => {
    if (!version) return;
    callConnector<{ tallyUrl: string }>("ping").then((r) => setUrl(r.result.tallyUrl)).catch(() => {});
  }, [version]);

  const connect = async () => {
    setErr(""); setBusy("Connecting to Tally…");
    try {
      const r = await callConnector<{ tallyUrl: string; companies: TallyCompany[] }>("companies", { tallyUrl: url });
      setUrl(r.result.tallyUrl);
      setCompanies(r.result.companies);
      setCompany(matchCompany(r.result.companies, clientName));
      if (!r.result.companies.length) setErr("Tally is connected, but no company is open. Open the client's company in Tally and connect again.");
    } catch (e) { setErr(errMsg(e)); }
    setBusy("");
  };

  const canGroups = versionAtLeast(version, GROUPS_VERSION);
  // the group list of the chosen company, read when "Only loan groups" is chosen
  useEffect(() => {
    if (mode !== "loans" || !company || !canGroups || tree?.company === company) return;
    let live = true;
    setErr(""); setBusy("Reading ledger groups…");
    callConnector<{ groups: TallyGroup[] }>("groups", { tallyUrl: url, company }).then((r) => {
      if (!live) return;
      const roots = LOAN_ROOTS.map(([root]) => ({ root, nodes: groupTree(r.result.groups, root) })).filter((x) => x.nodes.length);
      setTree({ company, roots });
      const on = new Set<string>();
      roots.forEach((x) => { if (LOAN_ROOTS.find(([n]) => n === x.root)?.[1]) x.nodes.forEach((n) => on.add(n.name)); });
      setPicked(on);
    }).catch((e) => live && setErr(errMsg(e))).finally(() => live && setBusy(""));
    return () => { live = false; };
  }, [mode, company, canGroups]);

  /** Ticking a group ticks (or unticks) its sub-groups too. */
  const pick = (nodes: GroupNode[], i: number) => {
    const on = !picked.has(nodes[i].name);
    const next = new Set(picked);
    for (let j = i; j < nodes.length && (j === i || nodes[j].depth > nodes[i].depth); j++) { if (on) next.add(nodes[j].name); else next.delete(nodes[j].name); }
    setPicked(next);
  };

  const fetchData = async () => {
    setErr(""); setBusy("Starting…");
    try {
      const groups = mode === "loans" ? Array.from(picked) : undefined;
      const r = await callConnector<{ counts: TallyCounts }>("fetch", { tallyUrl: url, company, from, to, mode: mode === "loans" ? "groups" : "daybook", groups }, (t) => setBusy(t));
      const name = `Tally_${safeFileName(company)}_${from}_to_${to}_${mode === "loans" ? "LoanGroups" : "DayBook"}.xml`;
      onFile(new File([r.data], name, { type: "text/xml" }), mode);
    } catch (e) { setErr(errMsg(e)); }
    setBusy("");
  };

  if (!version) return (
    <Card className="p-5">
      <div className="flex items-start gap-3">
        <Database className="mt-0.5 h-5 w-5 shrink-0 text-navy-600" />
        <div className="text-sm">
          <div className="font-semibold">Tally से लाएँ – bring data directly from TallyPrime</div>
          <p className="mt-1 text-slate-600">Install the free <b>3CD Helper – Tally Connector</b> in Chrome or Edge on the computer where TallyPrime runs (one time):</p>
          <ol className="mt-2 list-decimal space-y-1 pl-5 text-slate-600">
            <li><a href="/tally-connector.zip" download className="font-medium text-navy-700 underline">Download the connector</a> and unzip it.</li>
            <li>Open <code className="rounded bg-slate-100 px-1">chrome://extensions</code>, turn on <b>Developer mode</b>, click <b>Load unpacked</b> and choose the unzipped folder.</li>
            <li>In TallyPrime: F1 Help → Settings → Connectivity → "TallyPrime acts as" <b>Server</b> (or Both), port <b>9000</b>.</li>
            <li>Refresh this page.</li>
          </ol>
          <Button variant="outline" size="sm" className="mt-3" icon={<RefreshCw className="h-4 w-4" />} onClick={() => setVersion(connectorVersion())}>Check again</Button>
        </div>
      </div>
    </Card>
  );

  return (
    <Card className="p-5">
      <div className="mb-3 flex flex-wrap items-center justify-between gap-2">
        <div className="flex items-center gap-2 font-semibold"><Database className="h-5 w-5 text-navy-600" />Tally से लाएँ</div>
        <span className="text-xs text-slate-500">Tally Connector {version}</span>
      </div>

      {!companies ? (
        <div className="flex flex-wrap items-end gap-2">
          <label className="text-sm text-slate-600">Tally address
            <Input className="mt-1 w-56" value={url} onChange={(e) => setUrl(e.target.value)} disabled={!!busy} />
          </label>
          <Button icon={busy ? undefined : <Database className="h-4 w-4" />} loading={!!busy} onClick={connect}>Connect to Tally</Button>
        </div>
      ) : (
        <div className="space-y-3">
          <div className="grid gap-3 sm:grid-cols-3">
            <label className="text-sm text-slate-600 sm:col-span-1">Company in Tally
              <Select className="mt-1 w-full" value={company} onChange={(e) => setCompany(e.target.value)} disabled={!!busy}>
                {companies.map((c) => <option key={c.name} value={c.name}>{c.name}</option>)}
              </Select>
            </label>
            <label className="text-sm text-slate-600">From<Input type="date" className="mt-1" value={from} onChange={(e) => setFrom(e.target.value)} disabled={!!busy} /></label>
            <label className="text-sm text-slate-600">To<Input type="date" className="mt-1" value={to} onChange={(e) => setTo(e.target.value)} disabled={!!busy} /></label>
          </div>
          {(() => { const bf = companies.find((c) => c.name === company)?.booksFrom; return bf && from && bf < from ? (
            <Alert tone="warn">Books of this company in Tally begin on {new Date(bf).toLocaleDateString("en-IN")}, before this period. Loan opening balances come from the ledger masters as on that date – check them in Clause 31 → Parties &amp; opening balances after bringing the data.</Alert>) : null; })()}
          {modes.length > 1 ? <div className="grid gap-2 sm:grid-cols-2">
            {modes.map((k) => [k, ...MODE_TEXT[k]] as [TallyMode, string, string]).map(([k, t, d]) => (
              <button key={k} type="button" disabled={!!busy} onClick={() => setMode(k)} className={cn("rounded-xl border p-3 text-left", mode === k ? "border-navy-900 bg-navy-50 ring-1 ring-navy-900" : "border-slate-200 hover:border-navy-300")}>
                <div className="text-sm font-semibold">{t}</div><div className="text-xs text-slate-500">{d}</div>
              </button>
            ))}
          </div> : <p className="text-xs text-slate-500">The Day Book of the period comes from Tally with its ledger masters; you choose the expense and Fixed Asset ledgers next.</p>}
          {mode === "loans" && !canGroups && <Alert tone="warn">Choosing loan groups needs Tally Connector {GROUPS_VERSION} or later (installed: {version}). <a href="/tally-connector.zip" download className="font-medium underline">Download the new connector</a>, remove the old one in chrome://extensions and load the new folder – or use the Day Book for now.</Alert>}
          {mode === "loans" && canGroups && tree?.company === company && (
            <div className="rounded-xl border border-slate-200 p-3">
              <div className="mb-2 text-xs font-semibold uppercase tracking-wide text-slate-500">Groups to bring</div>
              {tree.roots.length === 0 && <p className="text-sm text-slate-500">No loan groups found in this company. Use the Day Book.</p>}
              <div className="grid gap-x-6 gap-y-1 sm:grid-cols-2">
                {tree.roots.map((x) => (
                  <div key={x.root}>
                    {x.nodes.map((n, i) => (
                      <label key={n.name} className="flex cursor-pointer items-center gap-2 py-0.5 text-sm" style={{ paddingLeft: n.depth * 18 }}>
                        <input type="checkbox" className="h-4 w-4 accent-navy-900" checked={picked.has(n.name)} disabled={!!busy} onChange={() => pick(x.nodes, i)} />
                        <span className={n.depth === 0 ? "font-semibold" : ""}>{n.name}</span>
                        <span className="text-xs text-slate-400">{n.total} ledger{n.total === 1 ? "" : "s"}</span>
                      </label>
                    ))}
                  </div>
                ))}
              </div>
            </div>
          )}
          <div className="flex flex-wrap items-center gap-3">
            <Button icon={busy ? undefined : <Download className="h-4 w-4" />} loading={!!busy} disabled={!company || !from || !to || (mode === "loans" && (!canGroups || !picked.size))} onClick={fetchData}>Bring data</Button>
            <Button variant="ghost" size="sm" disabled={!!busy} onClick={() => { setCompanies(null); setTree(null); setErr(""); }}>Change Tally / company list</Button>
            {busy && <span className="inline-flex items-center gap-2 text-sm text-slate-600"><Spinner className="h-4 w-4" />{busy}</span>}
          </div>
        </div>
      )}
      {err && <Alert tone="error" className="mt-3">{err}</Alert>}
    </Card>
  );
}

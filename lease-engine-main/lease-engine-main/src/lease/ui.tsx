// @ts-nocheck
import { useState } from "react";
import { toNum, fmtMon, money, H } from "./core";

/* ------------------------------------------------- 6. UI PRIMITIVES */
export var inputCls = "w-full rounded-lg border border-slate-300 bg-white px-3 py-2 text-sm text-slate-900 shadow-sm outline-none transition focus:border-indigo-500 focus:ring-2 focus:ring-indigo-100";
export var miniCls = "num w-full rounded-md border border-slate-300 bg-white px-2 py-1 text-right text-xs outline-none focus:border-indigo-500";

export function Field(props) {
  return (
    <label className="block">
      <span className="flex items-center justify-between gap-2">
        <span className="text-[10.5px] font-semibold uppercase tracking-wider text-slate-500">{props.label}</span>
        {props.tag ? <span className="rounded bg-slate-100 px-1.5 py-0.5 text-[9px] font-bold text-slate-500">{props.tag}</span> : null}
      </span>
      <span className="mt-1.5 block">{props.children}</span>
      {props.error ? <span className="mt-1 block text-[11px] font-medium text-rose-600">{props.error}</span>
        : (props.hint ? <span className="mt-1 block text-[10.5px] leading-snug text-slate-400">{props.hint}</span> : null)}
    </label>
  );
}
export function Section(props) {
  var st = useState(!!props.open), open = st[0], setOpen = st[1];
  return (
    <div className="border-b border-slate-100 last:border-0">
      <button type="button" onClick={function () { setOpen(!open); }}
        className="flex w-full items-center justify-between px-5 py-3 text-left transition hover:bg-slate-50">
        <span className="flex items-center gap-2">
          <span className="text-xs font-bold text-slate-700">{props.title}</span>
          {props.badge ? <span className="rounded-full bg-indigo-50 px-2 py-0.5 text-[9px] font-bold uppercase tracking-wide text-indigo-600">{props.badge}</span> : null}
        </span>
        <span className={"text-slate-400 transition " + (open ? "rotate-180" : "")}>{"\u25BE"}</span>
      </button>
      {open ? <div className="space-y-3.5 px-5 pb-5 pt-1">{props.children}</div> : null}
    </div>
  );
}
export var TONES = { indigo: "from-indigo-600 to-indigo-500", emerald: "from-emerald-600 to-emerald-500",
  amber: "from-amber-500 to-amber-400", rose: "from-rose-600 to-rose-500",
  sky: "from-sky-600 to-sky-500", violet: "from-violet-600 to-violet-500",
  slate: "from-slate-700 to-slate-600" };
export function Card(props) {
  return (
    <div className="relative overflow-hidden rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className={"absolute inset-x-0 top-0 h-1 bg-gradient-to-r " + (TONES[props.tone] || TONES.slate)} />
      <p className="text-[10.5px] font-semibold uppercase tracking-wider text-slate-500">{props.label}</p>
      <p className="num mt-2 text-[22px] font-bold leading-tight text-slate-900">
        {props.symbol ? <span className="mr-1 text-sm font-medium text-slate-400">{props.symbol}</span> : null}
        {props.value}
      </p>
      {props.sub ? <p className="mt-1 text-[10.5px] leading-snug text-slate-500">{props.sub}</p> : null}
      {props.foot ? <p className="mt-2 border-t border-slate-100 pt-2 text-[10.5px] font-semibold text-slate-600">{props.foot}</p> : null}
    </div>
  );
}
export function JE(props) {
  var lines = (props.lines || []).filter(function (l) { return Math.abs(toNum(l.dr) + toNum(l.cr)) > 0.005; });
  var dr = lines.reduce(function (s, l) { return s + toNum(l.dr); }, 0);
  var cr = lines.reduce(function (s, l) { return s + toNum(l.cr); }, 0);
  var bal = Math.abs(dr - cr) < 0.05;
  var tg = { slate: "bg-slate-100 text-slate-600", indigo: "bg-indigo-50 text-indigo-600",
    amber: "bg-amber-50 text-amber-700", emerald: "bg-emerald-50 text-emerald-700",
    violet: "bg-violet-50 text-violet-700" };
  return (
    <div className="overflow-hidden rounded-xl border border-slate-200 bg-white shadow-sm">
      <div className="flex flex-wrap items-center justify-between gap-2 border-b border-slate-100 px-4 py-3">
        <h4 className="text-xs font-bold text-slate-800">{props.title}</h4>
        <span className={"rounded-full px-2.5 py-1 text-[9.5px] font-bold uppercase tracking-wide " + (tg[props.tone] || tg.slate)}>{props.tag}</span>
      </div>
      <table className="w-full text-xs">
        <thead>
          <tr className="text-[9.5px] uppercase tracking-wider text-slate-500">
            <th className="px-4 py-2 text-left font-bold">Particulars</th>
            <th className="px-3 py-2 text-right font-bold">Debit ({props.symbol})</th>
            <th className="px-4 py-2 text-right font-bold">Credit ({props.symbol})</th>
          </tr>
        </thead>
        <tbody className="divide-y divide-slate-50">
          {lines.map(function (l, x) {
            return (
              <tr key={x}>
                <td className={"px-4 py-2 " + (l.cr ? "pl-10 text-slate-600" : "font-semibold text-slate-800")}>
                  {(l.cr ? "To " : "Dr. ") + l.acc}
                </td>
                <td className="num px-3 py-2 text-right">{l.dr ? money(l.dr) : "\u2014"}</td>
                <td className="num px-4 py-2 text-right">{l.cr ? money(l.cr) : "\u2014"}</td>
              </tr>
            );
          })}
          <tr className={"font-bold " + (bal ? "bg-slate-50 text-slate-900" : "bg-rose-50 text-rose-700")}>
            <td className="px-4 py-2 text-[10px] uppercase tracking-wider">{bal ? "Total" : "Total, out of balance"}</td>
            <td className="num px-3 py-2 text-right">{money(dr)}</td>
            <td className="num px-4 py-2 text-right">{money(cr)}</td>
          </tr>
        </tbody>
      </table>
      {props.narration ? <p className="border-t border-slate-100 px-4 py-2.5 text-[10.5px] italic leading-snug text-slate-500">({props.narration})</p> : null}
    </div>
  );
}
export function Th(props) {
  var al = props.right ? "text-right" : (props.center ? "text-center" : "text-left");
  return <th className={"px-3 py-3 text-[9.5px] font-bold uppercase tracking-wider " + al}>{props.children}</th>;
}
export function Td(props) {
  var al = props.right ? "text-right num" : (props.center ? "text-center" : "");
  return <td className={"px-3 py-2 " + al + " " + (props.cls || "")}>{props.children}</td>;
}

/* Chart with an optional deferred tax series */
export function TrendChart(props) {
  var rows = props.rows;
  if (!rows || rows.length < 2) return null;
  var showDt = !!props.showDt;
  var W = 900, H = 210, PL = 6, PR = 6, PT = 12, PB = 24, max = 1, min = 0;
  rows.forEach(function (r) {
    max = Math.max(max, r.close, r.nbv, showDt && r.dt ? r.dt.close : 0);
    min = Math.min(min, showDt && r.dt ? r.dt.close : 0);
  });
  var span = max - min || 1;
  function X(k) { return PL + ((k - 1) / (rows.length - 1)) * (W - PL - PR); }
  function Y(v) { return H - PB - ((v - min) / span) * (H - PT - PB); }
  function path(get) {
    return rows.map(function (r, x) { return (x ? "L" : "M") + X(r.k).toFixed(1) + "," + Y(get(r)).toFixed(1); }).join(" ");
  }
  var pLiab = path(function (r) { return r.close; });
  var area = pLiab + " L" + X(rows.length).toFixed(1) + "," + Y(min) + " L" + X(1).toFixed(1) + "," + Y(min) + " Z";
  var every = Math.max(1, Math.ceil(rows.length / 9));
  var ticks = rows.filter(function (r, x) { return x === 0 || x === rows.length - 1 || x % every === 0; });
  return (
    <div className="rounded-xl border border-slate-200 bg-white p-4 shadow-sm">
      <div className="mb-2 flex flex-wrap items-center justify-between gap-2">
        <h3 className="text-xs font-bold text-slate-800">Liability Run-off, ROU Net Block{showDt ? " and Net Deferred Tax Asset" : ""}</h3>
        <div className="flex flex-wrap gap-4 text-[10.5px] font-semibold">
          <span className="flex items-center gap-1.5 text-emerald-600"><span className="h-2 w-4 rounded bg-emerald-500" />Lease liability</span>
          <span className="flex items-center gap-1.5 text-indigo-600"><span className="h-2 w-4 rounded bg-indigo-500" />ROU asset</span>
          {showDt ? <span className="flex items-center gap-1.5 text-violet-600"><span className="h-2 w-4 rounded bg-violet-500" />Net deferred tax</span> : null}
        </div>
      </div>
      <svg viewBox={"0 0 " + W + " " + H} style={{ width: "100%", height: 210 }} preserveAspectRatio="none">
        <defs>
          <linearGradient id="grad1" x1="0" y1="0" x2="0" y2="1">
            <stop offset="0%" stopColor="#10b981" stopOpacity="0.22" />
            <stop offset="100%" stopColor="#10b981" stopOpacity="0.02" />
          </linearGradient>
        </defs>
        {[0, 0.25, 0.5, 0.75, 1].map(function (fr) {
          return <line key={fr} x1={PL} x2={W - PR} y1={Y(min + span * fr)} y2={Y(min + span * fr)} stroke="#e2e8f0" strokeDasharray="3 4" />;
        })}
        {min < 0 ? <line x1={PL} x2={W - PR} y1={Y(0)} y2={Y(0)} stroke="#94a3b8" strokeWidth="1" /> : null}
        <path d={area} fill="url(#grad1)" />
        <path d={pLiab} fill="none" stroke="#059669" strokeWidth="2.2" />
        <path d={path(function (r) { return r.nbv; })} fill="none" stroke="#4f46e5" strokeWidth="2.2" strokeDasharray="5 3" />
        {showDt ? <path d={path(function (r) { return r.dt ? r.dt.close : 0; })} fill="none" stroke="#7c3aed" strokeWidth="2" strokeDasharray="2 3" /> : null}
        {ticks.map(function (r) {
          return <text key={r.k} x={X(r.k)} y={H - 7} textAnchor="middle" fontSize="9" fill="#94a3b8">{fmtMon(r.pStart)}</text>;
        })}
      </svg>
      {showDt ? (
        <p className="mt-1 text-center text-[10px] leading-snug text-slate-400">
          The deferred tax line tracks the gap between the two balances multiplied by the enacted tax rate. It builds while
          depreciation plus interest exceeds the contractual rent, then unwinds to nil.
        </p>
      ) : null}
    </div>
  );
}


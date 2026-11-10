import { useMemo } from 'react';
import { Bar, BarChart, Cell, Legend, Pie, PieChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from 'recharts';
import { useApp } from '../ctx';
import { headsTotal, itc, summarise, type Heads } from '../lib/engine';
import { amt, money, pct, short } from '../lib/format';
import { downloadWorkbook, stamp } from '../lib/excel';
import { table4Rows } from '../lib/exports';
import { Card, Empty, ExportBtn, Grid, Notice, PageHead, Stat } from '../components/ui';
import { useDevice } from '../device';

export default function DashboardTab() {
  const { ds, recon, goto, blocked, eng } = useApp();
  const phone = useDevice().type === 'phone';
  const c = recon.counts;
  const t = recon.t4;
  const matched = c.exact + c.tol;
  const itc2b = ds.g2b.reduce((a, r) => a + itc(r), 0);
  const itcBooks = ds.bks.reduce((a, r) => a + itc(r), 0);
  const missBooksItc = headsTotal(t.missBooks);
  const miss2bItc = headsTotal(t.miss2b);
  const blockedActive = blocked.filter((b) => b.active);

  const pie = [
    { name: 'Matched (exact)', value: c.exact, color: '#059669' },
    { name: `Within ₹${eng.tolerance}`, value: c.tol, color: '#34d399' },
    { name: 'Smart matched', value: c.smart, color: '#7c3aed' },
    { name: 'ITC mismatch', value: c.mismatch, color: '#f97316' },
    { name: 'Missing in books', value: c.missBooks, color: '#dc2626' },
    { name: 'Missing in 2B', value: c.miss2b, color: '#be185d' },
  ].filter((x) => x.value > 0);

  const top = useMemo(
    () =>
      summarise(recon.lines, 'gstin')
        .slice(0, 12)
        .map((s) => ({ name: (s.name || s.label).slice(0, 18), g2b: Math.round(s.itc2b), books: Math.round(s.itcBooks) })),
    [recon.lines]
  );

  if (!ds.g2b.length || !ds.bks.length)
    return (
      <>
        <PageHead title="Compliance Dashboard" />
        <Card>
          <Empty title="Load both the GSTR-2B and the purchase register">
            The dashboard fills in as soon as both files are imported in{' '}
            <button className="underline text-teal-700" onClick={() => goto('imp')}>
              Import & Settings
            </button>
            .
          </Empty>
        </Card>
      </>
    );

  const row = (label: string, h: Heads, action: string, tone = '', paren = false) =>
    phone ? (
      // Phone: one card per Table 4 line instead of a six-column table
      <tr className={tone}>
        <td colSpan={6} className="wrap" style={{ maxWidth: 'none' }}>
          <p className="font-semibold text-slate-800">{label}</p>
          <div className="grid grid-cols-4 gap-1 mt-1.5 text-[0.72rem]">
            {(['igst', 'cgst', 'sgst'] as const).map((k) => (
              <span key={k}>
                <span className="block text-slate-400 uppercase text-[0.6rem]">{k}</span>
                <span className="nums">{amt(h[k])}</span>
              </span>
            ))}
            <span>
              <span className="block text-slate-400 uppercase text-[0.6rem]">Total</span>
              <b className="nums">{paren ? `(${amt(headsTotal(h))})` : amt(headsTotal(h))}</b>
            </span>
          </div>
          <p className="text-[0.7rem] text-slate-500 mt-1">{action}</p>
        </td>
      </tr>
    ) : (
    <tr className={tone}>
      <td className="wrap font-medium">{label}</td>
      <td className="num">{amt(h.igst)}</td>
      <td className="num">{amt(h.cgst)}</td>
      <td className="num">{amt(h.sgst)}</td>
      <td className="num font-bold">{paren ? `(${amt(headsTotal(h))})` : amt(headsTotal(h))}</td>
      <td className="wrap text-[0.7rem] text-slate-500">{action}</td>
    </tr>
    );

  return (
    <div className="flex flex-col gap-4">
      <PageHead
        title="Compliance Dashboard"
        sub="Every invoice is counted once, in its final status after the primary match and the three smart passes."
        right={<ExportBtn label="Table 4 Excel" onClick={() => downloadWorkbook(`GSTR3B_Table4_${stamp()}`, [{ name: 'GSTR-3B Table 4', rows: table4Rows(t) }])} />}
      />
      <Grid cols={6}>
        <Stat label="Matched" value={matched} sub={`${pct(matched, c.total)}% of ${c.total} lines`} tone="green" onClick={() => goto('recon')} />
        <Stat label="Smart matched" value={c.smart} sub="review, then claim" tone="violet" onClick={() => goto('smart')} />
        <Stat label="ITC mismatch" value={c.mismatch} sub={`beyond ₹${eng.tolerance}`} tone="orange" onClick={() => goto('recon')} />
        <Stat label="Missing in books" value={c.missBooks} sub={short(missBooksItc)} tone="red" onClick={() => goto('recon')} />
        <Stat label="Missing in 2B" value={c.miss2b} sub={`${short(miss2bItc)} at risk`} tone="red" onClick={() => goto('follow')} />
        <Stat label="Blocked 17(5)" value={blockedActive.length} sub={short(blockedActive.reduce((a, b) => a + b.igst + b.cgst + b.sgst, 0))} tone="slate" onClick={() => goto('blocked')} />
      </Grid>

      {(ds.g2b_excl.length > 0 || ds.bks_excl.length > 0) && (
        <Notice tone="warn">
          {ds.g2b_excl.length + ds.bks_excl.length} rows were left out at import because the GSTIN or invoice no. was missing. See <b>Excluded rows</b> in the Reconciliation Ledger.
        </Notice>
      )}

      <div className="grid grid-cols-1 lg:grid-cols-2 gap-3">
        <Card title="Status of all invoices">
          <div style={{ height: phone ? 300 : 240 }}>
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pie} dataKey="value" nameKey="name" innerRadius={phone ? 50 : 55} outerRadius={phone ? 78 : 85} paddingAngle={2}>
                  {pie.map((p) => (
                    <Cell key={p.name} fill={p.color} />
                  ))}
                </Pie>
                <Tooltip formatter={(v) => [`${v} invoices`, '']} />
                {phone ? (
                  <Legend layout="horizontal" align="center" verticalAlign="bottom" iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 11 }} />
                ) : (
                  <Legend layout="vertical" align="right" verticalAlign="middle" iconType="circle" iconSize={9} wrapperStyle={{ fontSize: 11 }} />
                )}
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card title="ITC position">
          <table className="tbl">
            <tbody>
              <tr>
                <td>ITC as per GSTR-2B</td>
                <td className="num font-semibold">{money(itc2b)}</td>
              </tr>
              <tr>
                <td>ITC as per purchase register</td>
                <td className="num font-semibold">{money(itcBooks)}</td>
              </tr>
              <tr>
                <td>In 2B, not in books</td>
                <td className="num text-red-600">{money(missBooksItc)}</td>
              </tr>
              <tr>
                <td>In books, not in 2B (do not claim yet)</td>
                <td className="num text-red-600">{money(miss2bItc)}</td>
              </tr>
              <tr>
                <td>Under review (mismatch + smart matched)</td>
                <td className="num text-orange-600">{money(headsTotal(t.review))}</td>
              </tr>
              <tr>
                <td>Reverse-charge ITC 4(A)(3)</td>
                <td className="num text-violet-700">{money(headsTotal(t.rcm))}</td>
              </tr>
              <tr>
                <td>Credit / debit notes in 2B (net)</td>
                <td className="num text-sky-700">{money(headsTotal(t.cdn))}</td>
              </tr>
              <tr className="bg-teal-50">
                <td className="font-bold text-teal-900">Net ITC 4(C)</td>
                <td className="num font-bold text-teal-800">{money(headsTotal(t.net))}</td>
              </tr>
            </tbody>
          </table>
        </Card>
      </div>

      <Card title="Top suppliers by ITC (GSTR-2B vs books)">
        <div style={{ height: 260 }}>
          <ResponsiveContainer width="100%" height="100%">
            <BarChart data={phone ? top.slice(0, 6) : top} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
              <XAxis dataKey="name" tick={{ fontSize: 9 }} interval={0} angle={-30} textAnchor="end" height={64} />
              <YAxis tick={{ fontSize: 9 }} width={64} tickFormatter={(v: number) => (v >= 1e5 ? `${(v / 1e5).toFixed(1)}L` : String(v))} />
              <Tooltip formatter={(v) => money(Number(v))} />
              <Legend wrapperStyle={{ fontSize: 11 }} />
              <Bar dataKey="g2b" name="GSTR-2B ITC" fill="#0d9488" radius={[2, 2, 0, 0]} />
              <Bar dataKey="books" name="Books ITC" fill="#d97706" radius={[2, 2, 0, 0]} />
            </BarChart>
          </ResponsiveContainer>
        </div>
      </Card>

      <Card title="GSTR-3B Table 4 — suggested figures" pad={false}>
        <div className="tbl-wrap">
          <table className="tbl">
            <thead className={phone ? 'hidden' : undefined}>
              <tr>
                <th>Table 4</th>
                <th className="num">IGST</th>
                <th className="num">CGST</th>
                <th className="num">SGST/UTGST</th>
                <th className="num">Total</th>
                <th>What to do</th>
              </tr>
            </thead>
            <tbody>
              {row('4(A)(3) Inward supplies liable to reverse charge', t.rcm, 'Claim after paying the RCM tax in Table 3.1(d).')}
              {row('4(A)(5) All other ITC — matched invoices', t.eligible, 'Claim. Invoice matches GSTR-2B (exact or within tolerance).')}
              {row('4(B)(1) Reversal — Section 17(5) blocked', t.blocked, 'Reverse the blocked credit included in 4(A)(5).', 'bg-red-50/40', true)}
              {row('4(C) Net ITC available', t.net, '4(A)(3) + 4(A)(5) − 4(B)(1).', 'bg-teal-50 font-bold')}
            </tbody>
            <tbody>
              <tr>
                <td colSpan={6} className="bg-slate-50 text-[0.68rem] font-semibold text-slate-500 uppercase tracking-wide">
                  Not included above — decide before filing
                </td>
              </tr>
              {row('ITC mismatch and smart matches', t.review, 'Check the difference; claim the lower of books and 2B once satisfied.')}
              {row('In GSTR-2B, not in books', t.missBooks, 'Book the purchase if it is yours, then claim.')}
              {row('In books, not in GSTR-2B', t.miss2b, 'Do not claim. Ask the supplier to report it in GSTR-1 (Section 16(2)(aa)).')}
              {row('Credit / debit notes in GSTR-2B (net)', t.cdn, 'Reduce ITC by credit notes after review.')}
            </tbody>
          </table>
        </div>
      </Card>
    </div>
  );
}

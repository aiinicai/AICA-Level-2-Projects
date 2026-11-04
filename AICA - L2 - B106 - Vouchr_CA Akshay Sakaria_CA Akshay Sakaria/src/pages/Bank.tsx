import { useMemo, useRef, useState } from 'react';
import { DpdpNote } from '../ui/DpdpNote';
import { useStore } from '../data/store';
import { useTr } from '../i18n';
import { applyMapping, guessMapping, mappingFromNames, matchBankRows, namesFromMapping, readStatementFile, type BankMapping, type BankMatch } from '../lib/bank';
import { outstanding } from '../lib/alerts';
import { fmtDate, fyLabel } from '../lib/dates';
import { docName, saveDocument } from '../lib/storage';
import { fmtInr, round2 } from '../lib/money';
import { Empty, PageHead, useAttempt, useToast } from '../ui/common';
import { Icon } from '../ui/Icon';
import { modeLabel } from '../ui/PaymentLines';
import { runAi, useAiStatus, type AiResult, type Fact } from '../lib/ai';
import { AiOff, Doubts, FactTag } from '../ui/AiBits';

export function Bank() {
  const st = useStore();
  const { scoped, client } = st;
  const tr = useTr();
  const toast = useToast();
  const attempt = useAttempt();
  const ref = useRef<HTMLInputElement>(null);
  const banks = client?.bankAccounts.filter((a) => a.kind === 'bank' && a.active !== false) ?? [];
  const [account, setAccount] = useState(banks[0]?.id ?? '');
  const sourceFor = (mode: string) => mode === 'upi' ? client?.bankAccounts.find((a) => a.kind === 'upi' && a.linkedBankId === account)?.id ?? account : account;
  const [matches, setMatches] = useState<BankMatch[]>([]);
  const [chosen, setChosen] = useState<Record<number, boolean>>({});
  const [vendorPick, setVendorPick] = useState<Record<number, string>>({});
  // D — AI vendor suggestions for rows the rules could not match (only from our vendor list, with a quote from the narration)
  const ai = useAiStatus();
  const [aiBusy, setAiBusy] = useState(false);
  const [aiErr, setAiErr] = useState<string>();
  const [aiRes, setAiRes] = useState<AiResult<{ matches: { row_id: string; vendor: Fact<string> }[] }>>();
  const aiFor = (i: number) => aiRes?.result.matches.find((m) => m.row_id === String(i))?.vendor;
  async function suggestVendors() {
    const rows = matches.map((m, i) => ({ m, i })).filter(({ m }) => !m.vendor && !alreadyIn(m)).slice(0, 60)
      .map(({ m, i }) => ({ id: String(i), narration: m.row.narration, amount: m.row.debit, date: m.row.date }));
    if (!rows.length) return;
    setAiBusy(true); setAiErr(undefined);
    try {
      const r = await runAi<{ matches: { row_id: string; vendor: Fact<string> }[] }>('bank_match', st.me!.role, { clientId: client?.id, vendors: scoped.vendors.map((v) => ({ name: v.name })), rows });
      setAiRes(r);
      // only checked suggestions pre-select the vendor; the row stays unticked until a person ticks it
      const picks = { ...vendorPick };
      for (const m of r.result.matches) if (m.vendor.certainty === 'certain') { const v = scoped.vendors.find((x) => x.name === m.vendor.value); if (v) picks[Number(m.row_id)] = v.id; }
      setVendorPick(picks);
    } catch (e) { setAiErr((e as Error).message); } finally { setAiBusy(false); }
  }

  const openBills = useMemo(() => scoped.expenses.filter((e) => e.status !== 'rejected' && e.status !== 'draft')
    .map((e) => ({ expense: e, due: outstanding(e, scoped.payments) })).filter((b) => b.due > 0), [scoped]);
  // a debit already recorded (same date, amount and account) must not be imported twice
  const alreadyIn = (m: BankMatch) => scoped.payments.some((p) => p.paidOn === m.row.date && Math.abs(p.amount - m.row.debit) < 0.01 && (p.ref && m.row.ref ? p.ref === m.row.ref : true));

  const [mapper, setMapper] = useState<{ rows: string[][]; file: File; m: BankMapping }>();
  const acct = client?.bankAccounts.find((a) => a.id === account);

  async function onFile(f?: File) {
    if (!f) return;
    try {
      const table = await readStatementFile(f);
      // this bank's saved columns first, then recognition by name; otherwise the person picks the columns once
      const m = (acct?.statementColumns && mappingFromNames(table, acct.statementColumns)) || guessMapping(table);
      if (!m) {
        const hr = Math.max(0, table.findIndex((r) => r.filter((c) => c.trim()).length >= 3));
        setMapper({ rows: table, file: f, m: { headerRow: hr, date: -1, narration: -1 } });
        return;
      }
      await processRows(applyMapping(table, m), f);
    } catch (err) {
      toast(tr('Could not read this statement. Upload the CSV or Excel (.xlsx) file from your bank.') + ` (${(err as Error).message})`, true);
    }
  }

  function saveColumns(rows: string[][], m: BankMapping) {
    if (!client || !acct) return;
    st.updateClient({ ...client, bankAccounts: client.bankAccounts.map((a) => (a.id === acct.id ? { ...a, statementColumns: namesFromMapping(rows, m) } : a)) });
  }

  async function processRows(rows: ReturnType<typeof applyMapping>, f: File) {
    if (client && rows.length) {
      const last = rows[rows.length - 1].date;
      saveDocument({ clientId: client.id, clientName: client.name, fy: fyLabel(last), kind: 'Bank Statements', file: f, name: docName(last, banks.find((b) => b.id === account)?.name ?? 'bank', 'statement', f.name) })
        .catch((err) => st.logEvent('error', 'drive_upload', 'File could not be saved: {err}', { err: (err as Error).message }));
    }
    const m = matchBankRows(rows, scoped.vendors, openBills);
    setMatches(m);
    setChosen(Object.fromEntries(m.map((x, i) => [i, x.confidence === 'high' && !alreadyIn(x)])));
    setVendorPick({});
    toast(tr('{n} payments found in the statement', { n: m.length }));
  }

  function importChosen() {
    let n = 0;
    const ok = attempt(() => {
      matches.forEach((m, i) => {
        if (!chosen[i]) return;
        const vendorId = m.vendor?.id ?? vendorPick[i];
        if (!vendorId) return;
        const allocations = m.vendor ? m.bills.map((b) => ({ expenseId: b.expense.id, amount: b.amount })) : [];
        st.recordPayment({ vendorId, mode: m.row.mode, accountId: m.row.mode === 'cash' ? undefined : sourceFor(m.row.mode), ref: m.row.ref ?? m.row.narration.slice(0, 30), paidOn: m.row.date, amount: m.row.debit, allocations, source: 'bank_import' });
        n++;
      });
    });
    if (ok) { toast(tr('{n} payments recorded', { n })); setMatches([]); }
  }

  const count = Object.values(chosen).filter(Boolean).length;
  return (
    <div className="content stack">
      <PageHead title={tr('Bank statement')} sub={tr('Match bank debits to unpaid bills in one go')}>
        {banks.length > 0 && (
          <select className="input sm" style={{ width: 'auto' }} value={account} onChange={(e) => setAccount(e.target.value)} aria-label={tr('Statement of account')}>
            {banks.map((a) => <option key={a.id} value={a.id}>{a.name}</option>)}
          </select>
        )}
        <button className="btn primary" onClick={() => ref.current?.click()}><Icon name="upload" size={16} /> {tr('Upload statement')}</button>
        {acct?.statementColumns && <button className="btn sm" onClick={() => attempt(() => { if (client) st.updateClient({ ...client, bankAccounts: client.bankAccounts.map((a) => (a.id === acct.id ? { ...a, statementColumns: undefined } : a)) }); }, 'Columns will be asked again')}>{tr('Change columns')}</button>}
      </PageHead>
      <input ref={ref} type="file" accept=".csv,text/csv,.xlsx,application/vnd.openxmlformats-officedocument.spreadsheetml.sheet" hidden data-testid="bank-file" onChange={(e) => { onFile(e.target.files?.[0]); e.target.value = ''; }} />
      {mapper && <ColumnMapper rows={mapper.rows} initial={mapper.m} onCancel={() => setMapper(undefined)}
        onUse={async (m) => { saveColumns(mapper.rows, m); const f = mapper.file; setMapper(undefined); await processRows(applyMapping(mapper.rows, m), f); }} />}
      <div className="hint">{tr('Download the statement from net banking as CSV. We read Date, Narration, Reference and Withdrawal columns — on your device.')}</div>

      {matches.length === 0 ? <div className="card"><Empty>{tr('No statement loaded.')}</Empty></div> : (
        <>
          <div className="row wrap">
            <button className="btn sm" disabled={!ai.enabled || aiBusy || !matches.some((m) => !m.vendor && !alreadyIn(m))} onClick={suggestVendors}>{aiBusy ? tr('Matching…') : tr('Suggest vendors with AI')}</button>
            {!ai.enabled ? <AiOff reason={ai.reason} /> : <DpdpNote kind="ai" />}
          </div>
          {aiErr && <div className="banner danger small">{tr(aiErr)}</div>}
          {aiRes && <Doubts doubts={aiRes.doubts} />}
          <div className="card table-wrap">
            <table className="t num cards-sm">
              <thead><tr><th /><th>{tr('Date')}</th><th>{tr('Narration')}</th><th className="right">{tr('Amount')}</th><th>{tr('Suggested match')}</th></tr></thead>
              <tbody>{matches.map((m, i) => {
                const dup = alreadyIn(m);
                return (
                  <tr key={i} style={{ opacity: dup ? 0.55 : 1 }}>
                    <td><input type="checkbox" disabled={dup} checked={!!chosen[i]} onChange={(e) => setChosen({ ...chosen, [i]: e.target.checked })} aria-label={tr('Import this payment')} /></td>
                    <td className="nowrap">{fmtDate(m.row.date)}<div className="tiny muted">{tr(modeLabel(m.row.mode))}</div></td>
                    <td className="small" style={{ maxWidth: 260 }}>{m.row.narration}</td>
                    <td className="right">{fmtInr(m.row.debit)}</td>
                    <td className="small">
                      {dup ? <span className="badge">{tr('Already recorded')}</span> : m.vendor ? (
                        <>
                          <b>{m.vendor.name}</b> <span className={`badge ${m.confidence === 'high' ? 'ok' : 'warn'}`}>{tr(m.confidence === 'high' ? 'Sure' : 'Check')}</span>
                          <div className="tiny muted">{m.bills.map((b) => `${b.expense.invoiceNo ?? '—'} ${fmtInr(b.amount)}`).join(', ') || tr('as advance')}{round2(m.row.debit - m.bills.reduce((x, b) => x + b.amount, 0)) > 0 && m.bills.length ? ` + ${tr('advance')}` : ''}</div>
                        </>
                      ) : (
                        <select className="input sm" value={vendorPick[i] ?? ''} onChange={(e) => { setVendorPick({ ...vendorPick, [i]: e.target.value }); setChosen({ ...chosen, [i]: !!e.target.value }); }} aria-label={tr('Vendor')}>
                          <option value="">{tr('Not a vendor payment / skip')}</option>
                          {scoped.vendors.map((v) => <option key={v.id} value={v.id}>{v.name} ({tr('as advance')})</option>)}
                        </select>
                      )}
                      {!dup && !m.vendor && aiFor(i) && aiFor(i)!.value !== null && (
                        <div className="row tiny" style={{ gap: 6, marginTop: 4 }}>{tr('AI')}: {String(aiFor(i)!.value)} <FactTag f={aiFor(i)} /></div>
                      )}
                    </td>
                  </tr>
                );
              })}</tbody>
            </table>
          </div>
          <div className="row between wrap">
            <span className="hint">{tr('Ticked rows will be recorded as payments. Rows matched only by amount are not ticked — check them first.')}</span>
            <button className="btn primary" disabled={!count} onClick={importChosen}>{tr('Record {n} payments', { n: count })}</button>
          </div>
        </>
      )}
    </div>
  );
}

/** One-time column choice for a bank whose statement columns are not recognised. Remembered for that bank account. */
function ColumnMapper({ rows, initial, onUse, onCancel }: { rows: string[][]; initial: BankMapping; onUse: (m: BankMapping) => void; onCancel: () => void }) {
  const tr = useTr();
  const [m, setM] = useState<BankMapping>(initial);
  const [style, setStyle] = useState<'two' | 'drcr' | 'sign'>('two');
  const header = rows[m.headerRow] ?? [];
  const pick = (key: keyof BankMapping, label: string, optional = false) => (
    <div className="field"><label htmlFor={`bm-${key}`} className={optional ? '' : 'req'}>{tr(label)}</label>
      <select id={`bm-${key}`} className="input sm" value={(m[key] as number | undefined) ?? -1} onChange={(e) => setM({ ...m, [key]: Number(e.target.value) < 0 ? undefined : Number(e.target.value) })}>
        <option value={-1}>{optional ? tr('None') : tr('Choose')}</option>
        {header.map((h, i) => <option key={i} value={i}>{h || `${tr('Column')} ${i + 1}`}</option>)}
      </select></div>
  );
  const final: BankMapping = style === 'two' ? { ...m, amount: undefined, drCr: undefined, minusIsDebit: undefined }
    : style === 'drcr' ? { ...m, debit: undefined, credit: undefined, minusIsDebit: undefined } : { ...m, debit: undefined, credit: undefined, drCr: undefined, minusIsDebit: true };
  const ready = final.date >= 0 && final.narration >= 0 && (style === 'two' ? (final.debit ?? -1) >= 0 : (final.amount ?? -1) >= 0) && (style !== 'drcr' || (final.drCr ?? -1) >= 0);
  const preview = ready ? applyMapping(rows, final).slice(0, 5) : [];
  return (
    <div className="card pad stack" style={{ borderColor: 'var(--brand)' }}>
      <h2>{tr('Which column is which?')}</h2>
      <div className="small">{tr('The columns of this statement were not recognised. Choose them once — they are remembered for this bank account.')}</div>
      <div className="field" style={{ maxWidth: 220 }}><label htmlFor="bm-hr">{tr('Header row')}</label>
        <select id="bm-hr" className="input sm" value={m.headerRow} onChange={(e) => setM({ headerRow: Number(e.target.value), date: -1, narration: -1 })}>
          {rows.slice(0, 30).map((r, i) => <option key={i} value={i}>{i + 1}: {r.filter(Boolean).slice(0, 4).join(' | ').slice(0, 60)}</option>)}
        </select></div>
      <div className="chips" role="radiogroup" aria-label={tr('How amounts are shown')}>
        {([['two', 'Separate Debit and Credit columns'], ['drcr', 'One Amount column + a Dr/Cr column'], ['sign', 'One Amount column, minus = money paid out']] as const).map(([k, l]) => (
          <button key={k} role="radio" aria-checked={style === k} className={`chip ${style === k ? 'on' : ''}`} onClick={() => setStyle(k)}>{tr(l)}</button>
        ))}
      </div>
      <div className="row wrap" style={{ alignItems: 'flex-start' }}>
        {pick('date', 'Date')}{pick('narration', 'Narration / description')}{pick('ref', 'Reference / cheque no.', true)}
        {style === 'two' ? <>{pick('debit', 'Debit / withdrawal')}{pick('credit', 'Credit / deposit', true)}</> : pick('amount', 'Amount')}
        {style === 'drcr' && pick('drCr', 'Dr / Cr column')}
      </div>
      {preview.length > 0 && (
        <div className="table-wrap"><table className="t num small">
          <thead><tr><th>{tr('Date')}</th><th>{tr('Narration')}</th><th className="right">{tr('Paid out')}</th><th className="right">{tr('Received')}</th></tr></thead>
          <tbody>{preview.map((r, i) => <tr key={i}><td>{fmtDate(r.date)}</td><td className="ellipsis" style={{ maxWidth: 260 }}>{r.narration}</td><td className="right">{r.debit ? fmtInr(r.debit) : ''}</td><td className="right">{r.credit ? fmtInr(r.credit) : ''}</td></tr>)}</tbody>
        </table></div>
      )}
      {ready && preview.length === 0 && <div className="hint err">{tr('No rows with a date were found with these columns.')}</div>}
      <div className="row" style={{ justifyContent: 'flex-end' }}>
        <button className="btn" onClick={onCancel}>{tr('Cancel')}</button>
        <button className="btn primary" disabled={!ready || preview.length === 0} onClick={() => onUse(final)}>{tr('Use these columns')}</button>
      </div>
    </div>
  );
}

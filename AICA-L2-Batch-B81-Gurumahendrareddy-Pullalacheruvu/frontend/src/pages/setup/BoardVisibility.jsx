// Setup › Board visibility. What the board sees, decided here.
import React, { useEffect, useState } from 'react'
import { api } from '../../lib/api'
import { useApp, useEndpoint } from '../../lib/store'
import { ts } from '../../lib/format'
import { Card, Empty, ErrorNote, Icon, Loading, Table, TD, TH } from '../../components/ui'

export default function BoardVisibility() {
  const { notify } = useApp()
  const { data, loading, error, reload } = useEndpoint('/api/setup/board-visibility')
  const [draft, setDraft] = useState(null)
  const [busy, setBusy] = useState(false)
  const [preview, setPreview] = useState(null)

  useEffect(() => {
    if (data) setDraft(Object.fromEntries(data.rules.map((r) => [r.key, r.visible])))
  }, [data])

  if (loading && !data) return <Loading rows={4} />
  if (error) return <ErrorNote error={error} onRetry={reload} />
  if (!data || !draft) return null

  const dirty = data.rules.some((r) => draft[r.key] !== r.visible)

  async function save() {
    setBusy(true)
    try {
      const r = await api.put('/api/setup/board-visibility',
        data.rules.map((x) => ({ rule_key: x.key, visible: draft[x.key] })))
      notify(r.message)
      reload()
    } catch (e) { notify(e.message, 'error') }
    setBusy(false)
  }

  async function showPreview() {
    try { setPreview(await api.get('/api/setup/board-visibility/preview')) }
    catch (e) { notify(e.message, 'error') }
  }

  return (
    <div className="space-y-5">
      <Card title="The rule this screen obeys" sub="Not a setting — a design decision.">
        <p className="text-[13px] text-ink leading-relaxed">{data.principle}</p>
        <p className="basis mt-2.5">
          {data.board_accounts} board account(s) are affected by what you set here.
          {data.pseudonyms_allocated > 0 &&
            ` ${data.pseudonyms_allocated} stand-in name(s) have been allocated — "Client A" is the same company on every screen and in every pack.`}
        </p>
      </Card>

      <Card
        title="What the board can see"
        sub="Everything not listed here is visible to the board already, including every headline figure."
        right={
          <div className="flex gap-2">
            <button onClick={showPreview}
                    className="rounded-lg border border-line px-3 py-1.5 text-[12.5px]
                               hover:bg-paper inline-flex items-center gap-1.5">
              <Icon name="eye" size={14} /> Preview
            </button>
            <button onClick={save} disabled={!dirty || busy || !data.editable}
                    className="rounded-lg bg-navy-700 text-white px-3.5 py-1.5 text-[12.5px]
                               font-medium hover:bg-navy-800 disabled:opacity-40">
              {busy ? 'Saving…' : 'Save'}
            </button>
          </div>
        }>
        {!data.editable && (
          <p className="mb-4 text-[12.5px] text-ink-muted">
            Only an Admin or the CFO can change these. You are seeing what is set.
          </p>
        )}

        <div className="space-y-2.5">
          {data.rules.map((r) => (
            <div key={r.key}
                 className="rounded-xl border border-line p-3.5 flex items-start gap-3.5">
              <button
                role="switch"
                aria-checked={draft[r.key]}
                disabled={!data.editable}
                onClick={() => setDraft({ ...draft, [r.key]: !draft[r.key] })}
                className={`mt-0.5 w-9 h-5 rounded-full shrink-0 transition relative
                            disabled:opacity-40 disabled:cursor-not-allowed
                            ${draft[r.key] ? 'bg-navy-700' : 'bg-line'}`}>
                <span className={`absolute top-0.5 w-4 h-4 rounded-full bg-white transition-all
                                  ${draft[r.key] ? 'left-[18px]' : 'left-0.5'}`} />
              </button>

              <div className="flex-1 min-w-0">
                <div className="flex items-center gap-2 flex-wrap">
                  <span className="text-[13.5px] font-medium text-ink">{r.label}</span>
                  <span className={`text-[11px] px-1.5 py-0.5 rounded-full
                                    ${draft[r.key] ? 'bg-status-green/10 text-status-green'
                                                   : 'bg-grey/10 text-ink-muted'}`}>
                    {draft[r.key] ? 'visible' : 'hidden'}
                  </span>
                  {draft[r.key] !== r.default && (
                    <span className="text-[11px] text-ink-faint">
                      (default: {r.default ? 'visible' : 'hidden'})
                    </span>
                  )}
                </div>
                <p className="text-[12.5px] text-ink-muted mt-1">{r.description}</p>
                {r.always_visible && (
                  <p className="basis mt-1.5">
                    <span className="font-medium text-ink-muted">Shown regardless: </span>
                    {r.always_visible}
                  </p>
                )}
                {r.set_by && (
                  <p className="basis mt-1">Set by {r.set_by}, {ts(r.set_at)}.</p>
                )}
              </div>
            </div>
          ))}
        </div>
      </Card>

      {preview && (
        <Card title="What a board member would see"
              sub="Money Coming In, top five by value, with the policy above applied."
              right={
                <button onClick={() => setPreview(null)}
                        className="text-[12.5px] text-ink-muted hover:text-ink">Close</button>
              }>
          {!preview.as_the_board_sees_it?.receivables?.length
            ? <Empty>No open invoices to preview.</Empty>
            : (
              <>
                <Table>
                  <thead>
                    <tr><TH left>Customer</TH><TH left>Invoice</TH><TH>Outstanding</TH>
                        <TH>Due</TH><TH>Can drill in?</TH></tr>
                  </thead>
                  <tbody>
                    {preview.as_the_board_sees_it.receivables.map((r, i) => (
                      <tr key={i}>
                        <TD left>{r.customer}</TD>
                        <TD left>{r.invoice_no}</TD>
                        <TD>{Number(r.outstanding).toLocaleString('en-IN')}</TD>
                        <TD>{r.due_date || '—'}</TD>
                        <TD>{r.trace ? 'yes' : 'no'}</TD>
                      </tr>
                    ))}
                  </tbody>
                </Table>
                {!!preview.restricted_labels?.length && (
                  <p className="basis mt-3">
                    Withheld on this screen: {preview.restricted_labels.join(', ')}. The
                    board's screen says so in those places rather than leaving them blank.
                  </p>
                )}
              </>
            )}
        </Card>
      )}
    </div>
  )
}

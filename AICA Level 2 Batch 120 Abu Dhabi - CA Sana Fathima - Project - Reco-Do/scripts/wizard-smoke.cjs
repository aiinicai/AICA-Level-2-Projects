// Drives the built app through the reconciliation wizard with the bundled sample files and saves screenshots.
// Usage (bash): npx electron-vite build && env -u ELECTRON_RUN_AS_NODE npx electron scripts/wizard-smoke.cjs
// It runs the real main process (out/main/index.js) with a throw-away user-data folder, moves the window
// off screen, clicks through Upload → Map & rules → Reconcile → Smart Recon → Review for Bank and General (HR),
// checks the tier counts and writes PNGs to docs/screenshots/. It then works on two Bank reconciliations at once
// (New reconciliation, the In progress menu, a reload of the app, resuming both). It also clicks Export Excel and Export PDF for the
// Bank sample and checks the saved files, then times a 50,000-row Bank reconciliation through the UI using two
// generated workbooks in the system temp folder. Exit code 1 on any failure.
// Set RECODO_SMOKE_SKIP_LARGE=1 to skip the 50,000-row run.
const { app, BrowserWindow } = require('electron')
const { join } = require('path')
const { mkdirSync, mkdtempSync, readdirSync, readFileSync, statSync, writeFileSync, rmSync } = require('fs')
const { tmpdir } = require('os')

const ROOT = join(__dirname, '..')
const OUT = join(ROOT, 'docs', 'screenshots')
const USER_DATA = mkdtempSync(join(tmpdir(), 'reco-do-smoke-'))
// Smoke-only hooks in the main process (src/main/smoke.ts): Save dialogs write here, Open dialogs return the
// generated 50,000-row files. The main process reads them at call time; they are inert in packaged builds.
const SAVE_DIR = join(USER_DATA, 'saved')
const LARGE_DIR = join(USER_DATA, 'large')
const LARGE_ROWS = 50000
const LARGE_FILES = [join(LARGE_DIR, 'Bank_Statement_50k.xlsx'), join(LARGE_DIR, 'GL_Cash_50k.xlsx')]
const RUN_LARGE = process.env.RECODO_SMOKE_SKIP_LARGE !== '1'
mkdirSync(SAVE_DIR, { recursive: true })
process.env.RECODO_SMOKE_SAVE_DIR = SAVE_DIR
if (RUN_LARGE) process.env.RECODO_SMOKE_OPEN_FILES = JSON.stringify(LARGE_FILES)

// A clean database for the run.
app.setPath('userData', USER_DATA)

const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const failures = []
const consoleErrors = []

function check(label, actual, expected) {
  const ok = JSON.stringify(actual) === JSON.stringify(expected)
  console.log(`${ok ? 'PASS' : 'FAIL'} ${label}: ${JSON.stringify(actual)}${ok ? '' : ` (expected ${JSON.stringify(expected)})`}`)
  if (!ok) failures.push(label)
}

// Helpers injected into the page. Radix menus open on pointerdown and tabs switch on mousedown.
const PAGE_HELPERS = `
  window.__smoke = {
    q: (sel) => document.querySelector(sel),
    click: (sel) => { const el = document.querySelector(sel); if (!el) throw new Error('missing ' + sel); el.click(); return true },
    press: (sel) => {
      const el = document.querySelector(sel); if (!el) throw new Error('missing ' + sel)
      el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0, pointerType: 'mouse' }))
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 0 }))
      return true
    },
    text: () => document.body.innerText,
    kpi: (id) => { const el = document.querySelector('[data-testid="kpi-' + id + '"] [data-kpi-value]'); return el ? el.textContent : null },
    scrollTop: () => { const m = document.getElementById('main'); if (m) m.scrollTop = 0; return true },
    clickText: (text, scope) => {
      const root = scope ? document.querySelector(scope) : document
      const el = Array.from(root.querySelectorAll('button')).find((b) => b.textContent.trim() === text && !b.disabled)
      if (!el) throw new Error('no button ' + text); el.click(); return true
    },
    closeToasts: () => { document.querySelectorAll('ol li button[aria-label="Close"]').forEach((b) => b.click()); return true },
    overflow: () => {
      const m = document.getElementById('main'); if (!m || m.scrollWidth <= m.clientWidth + 1) return null
      // Content edge: overflow past it pushes the right padding out and makes the page scroll sideways.
      const edge = m.getBoundingClientRect().left + m.clientWidth - parseFloat(getComputedStyle(m).paddingRight)
      const out = ['scrollWidth=' + m.scrollWidth + ' clientWidth=' + m.clientWidth]
      m.querySelectorAll('*').forEach((el) => {
        const r = el.getBoundingClientRect()
        if (r.right > edge + 1 && !Array.from(el.children).some((c) => c.getBoundingClientRect().right > edge + 1)) {
          out.push(el.tagName.toLowerCase() + '.' + String(el.className).slice(0, 60) + ' right=' + Math.round(r.right))
        }
      })
      const fixers = []
      const walk = (el, depth) => {
        if (depth > 9) return
        const prev = el.style.display
        el.style.display = 'none'
        const fixed = m.scrollWidth <= m.clientWidth + 1
        el.style.display = prev
        if (!fixed) return
        let childFixed = false
        for (const c of el.children) { if (walk(c, depth + 1)) childFixed = true }
        if (!childFixed) fixers.push(el.tagName.toLowerCase() + '.' + String(el.className).slice(0, 80))
        return true
      }
      for (const c of m.children) walk(c, 0)
      return out.concat(fixers.slice(0, 6))
    }
  }; true`

async function js(win, code) {
  return win.webContents.executeJavaScript(code, true)
}

async function waitFor(win, code, label, timeout = 20000) {
  const start = Date.now()
  for (;;) {
    try {
      if (await js(win, code)) return
    } catch {
      // page not ready yet
    }
    if (Date.now() - start > timeout) throw new Error(`Timed out waiting for ${label}`)
    await wait(150)
  }
}

async function shot(win, file, dir = OUT) {
  await js(win, 'window.__smoke.closeToasts()')
  await wait(350)
  await js(win, 'window.__smoke.scrollTop()')
  const over = await js(win, 'window.__smoke.overflow()')
  if (over) {
    failures.push(`${file}: page scrolls sideways`)
    console.log(`FAIL ${file}: page scrolls sideways; widest elements: ${over.join(' | ')}`)
  }
  // An off-screen window only repaints on request: force a fresh frame, then capture it.
  let image
  for (let attempt = 0; attempt < 4 && !image; attempt++) {
    try {
      win.webContents.invalidate()
      await wait(400)
      await win.webContents.capturePage()
      win.webContents.invalidate()
      await wait(400)
      image = await win.webContents.capturePage()
    } catch {
      // The compositor can be briefly unavailable right after a reload; try again.
      await wait(800)
    }
  }
  if (!image) throw new Error(`Could not capture ${file}`)
  writeFileSync(join(dir, file), image.toPNG())
  console.log('saved', file)
}

async function open(win, route) {
  await js(win, `location.hash = '#${route}'; true`)
  await wait(400)
  await js(win, PAGE_HELPERS)
}

async function kpis(win) {
  return js(
    win,
    `(() => ['matched','doubtful','likely','unmatched','ai'].map((id) => window.__smoke.kpi(id)))()`
  )
}

async function runBank(win) {
  await open(win, '/module/bank')
  await waitFor(win, `!!window.__smoke.q('[data-testid="try-samples"]')`, 'sample button')
  await js(win, `window.__smoke.click('[data-testid="try-samples"]')`)
  await waitFor(win, `window.__smoke.text().includes('Both files read')`, 'bank files read')
  await waitFor(win, `!window.__smoke.q('[data-testid="to-map"]').disabled`, 'continue enabled')
  await shot(win, '10-bank-upload.png')

  await js(win, `window.__smoke.click('[data-testid="to-map"]')`)
  await waitFor(win, `(() => { const b = window.__smoke.q('[data-testid="run-recon"]'); return b && !b.disabled })()`, 'run enabled')
  await wait(600)
  await shot(win, '11-bank-map.png')

  // Count Web Workers and their load errors, to prove the engine ran off the UI thread under the CSP.
  await js(
    win,
    `(() => { const W = window.Worker; window.__workers = { made: 0, errors: 0 }; window.Worker = function (...a) { const w = new W(...a); window.__workers.made++; w.addEventListener('error', () => window.__workers.errors++); return w }; return true })()`
  )
  await js(win, `window.__smoke.click('[data-testid="run-recon"]')`)
  await waitFor(win, `!!window.__smoke.q('[data-testid="to-smart"]')`, 'reconcile finished', 60000)
  check('Reconcile ran in a Web Worker without errors (made, errors)', await js(win, `[window.__workers.made, window.__workers.errors]`), [1, 0])
  await shot(win, '14-bank-reconcile.png')

  await js(win, `window.__smoke.click('[data-testid="to-smart"]')`)
  await waitFor(win, `window.__smoke.text().includes('Smart Reconciliation')`, 'smart recon panel')
  await wait(500)
  await shot(win, '15-bank-smart-recon.png')

  await js(win, `window.__smoke.click('[data-testid="to-review"]')`)
  await waitFor(win, `!!window.__smoke.q('[data-testid="kpi-matched"]')`, 'results')
  await wait(600)
  check('Bank KPIs (matched, doubtful, likely, unmatched A/B, AI)', await kpis(win), ['255', '16', '1', '29 / 19', '0'])
  await shot(win, '12-bank-results.png')

  // Side panel: Smart Recon and the reconciliation statement.
  await js(win, `window.__smoke.click('[data-testid="toggle-panel"]')`)
  await waitFor(win, `window.__smoke.text().includes('Unexplained difference')`, 'statement card')
  await shot(win, '19-bank-results-panel.png')
  await js(win, `window.__smoke.click('[data-testid="toggle-panel"]')`)

  // A review decision: Accept the first Doubtful pair. The first decision asks for the preparer name.
  await js(win, `window.__smoke.click('button[aria-label="Accept"]')`)
  await waitFor(win, `!!document.querySelector('[role="dialog"] input')`, 'preparer dialog')
  await js(
    win,
    `(() => { const i = document.querySelector('[role="dialog"] input'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(i, 'Sana Fathima'); i.dispatchEvent(new Event('input', { bubbles: true })); return true })()`
  )
  await wait(200)
  await js(win, `document.querySelector('[role="dialog"] button[type="submit"]').click(); true`)
  await waitFor(win, `window.__smoke.kpi('matched') === '256'`, 'accepted pair in Matched')
  check('After accepting one Doubtful pair (matched, doubtful)', [await js(win, `window.__smoke.kpi('matched')`), await js(win, `window.__smoke.kpi('doubtful')`)], ['256', '15'])
  await js(win, `window.__smoke.click('button[aria-label="Open audit trail"]')`)
  await waitFor(win, `window.__smoke.text().includes('Audit trail') && window.__smoke.text().includes('Sana Fathima')`, 'audit entry')
  await shot(win, '20-bank-audit-trail.png')
  await js(win, `document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); true`)
  await wait(300)
  const saved = await js(
    win,
    `new Promise((res) => { const r = indexedDB.open('reco-do'); r.onsuccess = () => { const t = r.result.transaction('sessions').objectStore('sessions').getAll(); t.onsuccess = () => res(t.result.map((x) => x.audit.length)); t.onerror = () => res(null) }; r.onerror = () => res(null) })`
  )
  check('Session saved to IndexedDB with the decision in its audit trail', saved, [1])

  // Unmatched tab with a manual-match selection, to show the action bar.
  await js(win, `window.__smoke.press('[role="tab"][id$="unmatchedA"]')`)
  await wait(500)
  await shot(win, '16-bank-unmatched.png')

  await checkExports(win)
}

/** Newest non-empty file in the smoke Save folder with this extension. */
async function savedFile(ext, timeout = 60000) {
  const start = Date.now()
  for (;;) {
    const hits = readdirSync(SAVE_DIR)
      .filter((f) => f.toLowerCase().endsWith(ext))
      .map((f) => ({ f, ...statSync(join(SAVE_DIR, f)) }))
      .sort((a, b) => b.mtimeMs - a.mtimeMs)
    if (hits.length && hits[0].size > 0) return join(SAVE_DIR, hits[0].f)
    if (Date.now() - start > timeout) throw new Error(`No ${ext} file was saved`)
    await wait(200)
  }
}

const baseName = (p) => p.split(/[\\/]/).pop()

async function checkExports(win) {
  // Excel: the real button and Save path (answered by the smoke hook), then re-open the file with ExcelJS.
  await js(win, `window.__smoke.closeToasts()`)
  await js(win, `window.__smoke.click('[data-testid="export-xlsx"]')`)
  await waitFor(win, `window.__smoke.text().includes('Excel workbook saved')`, 'Excel saved toast', 60000)
  const xlsxPath = await savedFile('.xlsx')
  const ExcelJS = require('exceljs')
  const wb = new ExcelJS.Workbook()
  await wb.xlsx.load(readFileSync(xlsxPath))
  const names = wb.worksheets.map((w) => w.name)
  console.log(`Excel export: ${baseName(xlsxPath)} (${statSync(xlsxPath).size.toLocaleString('en-US')} bytes), sheets ${JSON.stringify(names)}`)
  check('Excel export: fixed sheets in order', names.filter((n) => !n.startsWith('To Reconcile')), [
    'Summary',
    'Reconciliation Statement',
    'Matched (100%)',
    'Doubtful & Likely',
    'AI Assisted',
    'Audit Log'
  ])
  check('Excel export: one To Reconcile sheet per side, after Matched', [names[3]?.startsWith('To Reconcile'), names[4]?.startsWith('To Reconcile')], [true, true])
  check('Excel export: Matched sheet holds the 256 matched pairs', (wb.getWorksheet('Matched (100%)')?.actualRowCount ?? 0) > 256, true)

  // PDF: printToPDF in the main process, then the Save path (answered by the smoke hook).
  await js(win, `window.__smoke.closeToasts()`)
  await waitFor(win, `!window.__smoke.q('[data-testid="export-pdf"]').disabled`, 'PDF button enabled')
  await js(win, `window.__smoke.click('[data-testid="export-pdf"]')`)
  await waitFor(win, `window.__smoke.text().includes('PDF summary saved')`, 'PDF saved toast', 60000)
  const pdfPath = await savedFile('.pdf')
  const pdf = readFileSync(pdfPath)
  console.log(`PDF export: ${baseName(pdfPath)} (${pdf.length.toLocaleString('en-US')} bytes)`)
  check('PDF export is non-empty and starts with %PDF', pdf.length > 1000 && pdf.subarray(0, 4).toString('latin1') === '%PDF', true)
}

/** Two 50,000-row workbooks shaped like the Bank samples: about 96% match, the rest is open on one side. */
function writeLargeFiles() {
  const XLSX = require('xlsx')
  mkdirSync(LARGE_DIR, { recursive: true })
  let seed = 12345
  const rnd = () => (seed = (seed * 1103515245 + 12345) % 2147483648) / 2147483648
  const bank = [['Txn Date', 'Value Date', 'Description', 'Reference No', 'Debit', 'Credit', 'Balance']]
  const gl = [['Posting Date', 'Doc No', 'Voucher Type', 'Remarks', 'Party', 'Debit', 'Credit', 'Cheque No']]
  let balance = 1000000
  for (let i = 0; i < LARGE_ROWS; i++) {
    const day = new Date(2026, 0, 1 + Math.floor((i / LARGE_ROWS) * 270))
    const amount = Math.round((50 + rnd() * 50000) * 100) / 100
    const outflow = rnd() < 0.5
    const ref = `FT26${String(i).padStart(7, '0')}`
    const party = `Supplier ${String(i % 997).padStart(3, '0')} LLC`
    balance = Math.round((balance + (outflow ? -amount : amount)) * 100) / 100
    if (i % 50 !== 7) bank.push([day, day, `${outflow ? 'FT OUT' : 'FT IN'} ${ref} ${party}`, ref, outflow ? amount : null, outflow ? null : amount, balance])
    if (i % 50 !== 21) {
      const glDay = i % 9 === 0 ? new Date(day.getTime() + 86400000) : day
      gl.push([glDay, `${outflow ? 'BP' : 'BR'}-${i}`, outflow ? 'Bank Payment' : 'Bank Receipt', `${outflow ? 'Payment to' : 'Receipt from'} ${party}`, party, outflow ? null : amount, outflow ? amount : null, ref])
    }
  }
  const write = (rows, file, sheet) => {
    const wb = XLSX.utils.book_new()
    XLSX.utils.book_append_sheet(wb, XLSX.utils.aoa_to_sheet(rows, { cellDates: true }), sheet)
    XLSX.writeFile(wb, file, { compression: true })
  }
  write(bank, LARGE_FILES[0], 'Statement')
  write(gl, LARGE_FILES[1], 'GL')
  return { bankRows: bank.length - 1, glRows: gl.length - 1 }
}

// Measures how long the UI thread is blocked: the longest gap between 25 ms timer ticks since the last reset.
const BLOCK_MONITOR = `
  (() => {
    if (!window.__block) {
      window.__block = { last: performance.now(), max: 0 }
      setInterval(() => { const now = performance.now(); window.__block.max = Math.max(window.__block.max, now - window.__block.last); window.__block.last = now }, 25)
    }
    window.__block.max = 0; window.__block.last = performance.now(); return true
  })()`

async function phase(win, label, action, doneCode, timeout = 180000) {
  await js(win, BLOCK_MONITOR)
  const start = Date.now()
  await js(win, action)
  await waitFor(win, doneCode, label, timeout)
  const elapsed = Date.now() - start
  await wait(100) // one more tick, so a block that just ended is counted
  const blocked = Math.round(await js(win, 'window.__block.max'))
  console.log(`TIME ${label}: ${(elapsed / 1000).toFixed(1)} s, longest UI block ${(blocked / 1000).toFixed(2)} s`)
  return { elapsed, blocked }
}

async function runLarge(win) {
  const t0 = Date.now()
  const { bankRows, glRows } = writeLargeFiles()
  console.log(`\nGenerated ${bankRows.toLocaleString('en-US')} bank rows and ${glRows.toLocaleString('en-US')} GL rows in ${((Date.now() - t0) / 1000).toFixed(1)} s`)

  await js(win, `location.hash = '#/'; location.reload(); true`)
  await new Promise((r) => win.webContents.once('did-finish-load', r))
  await wait(600)
  await open(win, '/module/bank')
  const zones = `Array.from(document.querySelectorAll('div[role="button"]')).filter((d) => d.className.includes('border-dashed'))`
  await waitFor(win, `${zones}.length === 2`, 'upload drop zones')
  const results = {}
  results.readA = await phase(win, 'Read 50k bank statement', `${zones}[0].click(); true`, `window.__smoke.text().includes('1 of 2 files read')`)
  results.readB = await phase(win, 'Read 50k GL', `${zones}[1].click(); true`, `window.__smoke.text().includes('Both files read') && !window.__smoke.q('[data-testid="to-map"]').disabled`)
  results.map = await phase(
    win,
    'Open Map & rules (key suggestions)',
    `window.__smoke.click('[data-testid="to-map"]')`,
    `(() => { const b = window.__smoke.q('[data-testid="run-recon"]'); return b && !b.disabled })()`
  )
  await wait(400)
  results.run = await phase(win, 'Reconcile 50k x 50k', `window.__smoke.click('[data-testid="run-recon"]')`, `!!window.__smoke.q('[data-testid="to-smart"]')`, 300000)
  results.smart = await phase(win, 'Open Smart Recon', `window.__smoke.click('[data-testid="to-smart"]')`, `!!window.__smoke.q('[data-testid="to-review"]')`, 120000)
  results.review = await phase(win, 'Open Review & Export', `window.__smoke.click('[data-testid="to-review"]')`, `!!window.__smoke.q('[data-testid="kpi-matched"]')`, 120000)
  const k = await kpis(win)
  console.log(`50k KPIs (matched, doubtful, likely, unmatched A/B, AI): ${JSON.stringify(k)}`)
  check('50k reconcile matched most lines', Number(String(k[0]).replace(/,/g, '')) > 45000, true)

  // Per-decision save on the 50,000-row session: wait for the first (full) save, then time one Accept until the
  // decision is in IndexedDB, and check that a quick burst of decisions all end up saved (latest wins).
  const LATEST = `new Promise((res) => { const r = indexedDB.open('reco-do'); r.onsuccess = () => { const t = r.result.transaction('sessions').objectStore('sessions').getAll(); t.onsuccess = () => { r.result.close(); const s = t.result.sort((a, b) => b.updatedAt.localeCompare(a.updatedAt))[0]; res(s ? { lines: s.result.stats.linesA, audit: s.audit.length } : null) } }; r.onerror = () => res(null) })`
  // The history row is written in the same transaction as the session and is tiny, so polling it does not
  // itself block the page (reading the whole session would).
  const BIG_HISTORY = `new Promise((res) => { const r = indexedDB.open('reco-do'); r.onsuccess = () => { const t = r.result.transaction('history').objectStore('history').getAll(); t.onsuccess = () => { r.result.close(); const h = t.result.filter((x) => x.totalLines >= 80000)[0]; res(h ? h.finishedAt : null) } }; r.onerror = () => res(null) })`
  await waitFor(win, `${BIG_HISTORY}.then((f) => !!f)`, '50k session saved', 120000)
  const savedAt = await js(win, BIG_HISTORY)
  const accept = `button[aria-label="Accept"]`
  // Decisions are made on the Doubtful tab, or on Likely when there is nothing Doubtful.
  if (!(await js(win, `!!document.querySelector('${accept}')`))) {
    await js(win, `(() => { const t = document.querySelector('[role="tab"][id$="likely"]'); if (t) window.__smoke.press('[role="tab"][id$="likely"]'); return true })()`)
    await wait(400)
  }
  if (await js(win, `!!document.querySelector('${accept}')`)) {
    results.decision = await phase(win, 'Review decision + save (50k session)', `window.__smoke.click('${accept}')`, `${BIG_HISTORY}.then((f) => !!f && f !== ${JSON.stringify(savedAt)})`, 60000)
    await wait(300)
    await js(win, `window.__smoke.click('${accept}'); true`)
    await wait(60)
    await js(win, `window.__smoke.click('${accept}'); true`)
    await waitFor(win, `${LATEST}.then((s) => !!s && s.audit >= 3)`, 'burst of decisions saved', 60000)
    check('50k: three quick decisions all saved', (await js(win, LATEST)).audit, 3)
  } else {
    console.log('No Doubtful pair to accept in the 50k run; decision timing skipped.')
  }
  const total = Object.values(results).reduce((s, r) => s + r.elapsed, 0)
  const worst = Object.entries(results).sort((a, b) => b[1].blocked - a[1].blocked)[0]
  console.log(`50k through the UI: ${(total / 1000).toFixed(1)} s in all; longest UI block ${(worst[1].blocked / 1000).toFixed(2)} s (${worst[0]})`)
}

async function runGeneralHr(win) {
  await open(win, '/module/general')
  await waitFor(win, `!!window.__smoke.q('[data-testid="try-samples"]')`, 'sample button')
  await js(win, `window.__smoke.press('[data-testid="try-samples"]')`)
  await waitFor(win, `!!window.__smoke.q('[data-testid="sample-hr"]')`, 'sample menu')
  await js(win, `window.__smoke.click('[data-testid="sample-hr"]')`)
  await waitFor(win, `window.__smoke.text().includes('Both files read')`, 'general files read')
  await wait(400)
  await shot(win, '17-general-upload.png')

  await js(win, `window.__smoke.click('[data-testid="to-map"]')`)
  await waitFor(win, `(() => { const b = window.__smoke.q('[data-testid="run-recon"]'); return b && !b.disabled })()`, 'run enabled')
  await wait(600)
  await shot(win, '13-general-map.png')

  await js(win, `window.__smoke.click('[data-testid="run-recon"]')`)
  await waitFor(win, `!!window.__smoke.q('[data-testid="to-review"]')`, 'reconcile finished', 60000)
  await js(win, `window.__smoke.click('[data-testid="to-review"]')`)
  await waitFor(win, `!!window.__smoke.q('[data-testid="kpi-matched"]')`, 'results')
  await wait(600)
  check('General HR KPIs (matched, doubtful, likely, unmatched A/B, AI)', await kpis(win), ['165', '8', '0', '7 / 1', '0'])
  const tabs = await js(win, `Array.from(document.querySelectorAll('[role="tab"]')).map((t) => t.textContent)`)
  check('General tabs use the side names', tabs.some((t) => t.includes('HR employee master')), true)
  await shot(win, '18-general-results.png')

  // Bulk-reject every Doubtful pair, then finalise and sign off.
  await js(win, `window.__smoke.click('[role="tabpanel"][data-state="active"] [aria-label="Select all rows"]')`)
  await wait(200)
  await js(win, `window.__smoke.clickText('Reject selected')`)
  await waitFor(win, `window.__smoke.kpi('doubtful') === '0'`, 'doubtful cleared')
  await js(win, `window.__smoke.click('[data-testid="finalise"]')`)
  await waitFor(win, `!!document.querySelector('[role="dialog"]') && window.__smoke.text().includes('Finalise and sign off?')`, 'finalise dialog')
  await js(win, `window.__smoke.clickText('Finalise & sign off', '[role="dialog"]')`)
  await waitFor(win, `window.__smoke.text().includes('Finalised and signed off by')`, 'finalised banner')
  check('General finalised: read-only (no Accept/Reject buttons, no finalise button)', await js(win, `!document.querySelector('button[aria-label="Accept"]') && !document.querySelector('[data-testid="finalise"]')`), true)
  await shot(win, '21-general-finalised.png')

  // Resume from IndexedDB after a reload (as Recon History does): the finalised session opens read-only.
  const id = await js(
    win,
    `new Promise((res) => { const r = indexedDB.open('reco-do'); r.onsuccess = () => { const t = r.result.transaction('sessions').objectStore('sessions').getAll(); t.onsuccess = () => res((t.result.find((x) => x.finalised) || {}).id || null) } })`
  )
  await js(win, `location.hash = '#/'; location.reload(); true`)
  await new Promise((r) => win.webContents.once('did-finish-load', r))
  await wait(600)
  await open(win, `/module/general?session=${id}`)
  await waitFor(win, `window.__smoke.text().includes('Finalised and signed off by')`, 'resumed finalised session')
  check('Resumed session from history shows the same counts', await kpis(win), ['165', '0', '0', '15 / 10', '0'])
  await shot(win, '22-general-resumed.png')
}

/** Types into a React-controlled input. */
function typeInto(selector, value) {
  return `(() => { const i = document.querySelector(${JSON.stringify(selector)}); if (!i) throw new Error('missing input'); const set = Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set; set.call(i, ${JSON.stringify(value)}); i.dispatchEvent(new Event('input', { bubbles: true })); return true })()`
}

const ACCOUNT_INPUT = 'input[placeholder^="e.g. ENBD Current"]'
const MENU = '[data-testid="in-progress-menu"]'
/** The In progress menu rows as [account, status chip, stage line, on screen]. */
const MENU_ROWS = `Array.from(document.querySelectorAll('${MENU} [data-testid="in-progress-item"]')).map((li) => li.innerText)`

async function openMenu(win) {
  if (!(await js(win, `!!document.querySelector('${MENU}')`))) await js(win, `window.__smoke.click('[data-testid="in-progress"]')`)
  await waitFor(win, `document.querySelectorAll('${MENU} [data-testid="in-progress-item"]').length > 0`, 'In progress menu')
}

async function openFromMenu(win, account) {
  await openMenu(win)
  await js(
    win,
    `(() => { const li = Array.from(document.querySelectorAll('${MENU} [data-testid="in-progress-item"]')).find((x) => x.innerText.includes(${JSON.stringify(account)})); if (!li) throw new Error('no row ${account}'); li.querySelector('[data-testid="in-progress-open"]').click(); return true })()`
  )
}

const RUN_READY = `(() => { const b = window.__smoke.q('[data-testid="run-recon"]'); return b && !b.disabled })()`
const SESSIONS = `new Promise((res) => { const r = indexedDB.open('reco-do'); r.onsuccess = () => { const t = r.result.transaction('sessions').objectStore('sessions').getAll(); t.onsuccess = () => { r.result.close(); res(t.result.map((x) => ({ account: x.meta.accountLabel, audit: x.audit.length, finalised: !!x.finalised }))) } }; r.onerror = () => res(null) })`
const DRAFTS = `new Promise((res) => { const r = indexedDB.open('reco-do'); r.onsuccess = () => { const t = r.result.transaction(['drafts', 'sourceTables']); const d = t.objectStore('drafts').getAll(); const k = t.objectStore('sourceTables').getAllKeys(); t.oncomplete = () => { r.result.close(); res({ drafts: d.result.map((x) => ({ id: x.id, account: x.accountLabel, step: x.step })), sources: k.result }) } }; r.onerror = () => res(null) })`

/**
 * Several reconciliations at once: Bank recon A to Map & rules, New reconciliation, Bank recon B to Results,
 * back to A via In progress, reload the app (both still listed, A resumes at Map with its files), then B.
 */
async function runMultiRecon(win) {
  console.log('\nSeveral reconciliations at once')
  await open(win, '/module/bank')
  await waitFor(win, `!!window.__smoke.q('[data-testid="try-samples"]') && !!window.__smoke.q('[data-testid="new-recon"]')`, 'fresh Bank wizard with New reconciliation')

  // Recon A: sample files, own account name, up to Map & rules.
  await js(win, `window.__smoke.click('[data-testid="try-samples"]')`)
  await waitFor(win, `window.__smoke.text().includes('Both files read')`, 'recon A files read')
  await wait(400)
  await js(win, typeInto(ACCOUNT_INPUT, 'Recon A ENBD Current'))
  await js(win, `window.__smoke.click('[data-testid="to-map"]')`)
  await waitFor(win, RUN_READY, 'recon A at Map & rules')
  await wait(900) // the draft is saved after a short pause
  const draftA = await js(win, DRAFTS)
  check('Recon A saved as a draft at Map & rules with its files', [draftA.drafts.map((d) => [d.account, d.step]), draftA.sources.includes(draftA.drafts[0]?.id)], [[['Recon A ENBD Current', 1]], true])

  // New reconciliation: A is kept as a draft, a fresh wizard opens.
  await js(win, `window.__smoke.closeToasts()`)
  await js(win, `window.__smoke.click('[data-testid="new-recon"]')`)
  await waitFor(win, `window.__smoke.text().includes('Saved as draft') && window.__smoke.text().includes('Choose two files')`, 'fresh wizard after New reconciliation')
  check('New reconciliation opens a fresh Upload step', await js(win, `!!window.__smoke.q('[data-testid="try-samples"]') && window.__smoke.q('[data-testid="to-map"]').disabled`), true)

  // Recon B: run to Results.
  await js(win, `window.__smoke.click('[data-testid="try-samples"]')`)
  await waitFor(win, `window.__smoke.text().includes('Both files read')`, 'recon B files read')
  await wait(400)
  await js(win, typeInto(ACCOUNT_INPUT, 'Recon B ENBD Current'))
  await js(win, `window.__smoke.click('[data-testid="to-map"]')`)
  await waitFor(win, RUN_READY, 'recon B at Map & rules')
  await js(win, `window.__smoke.click('[data-testid="run-recon"]')`)
  await waitFor(win, `!!window.__smoke.q('[data-testid="to-review"]')`, 'recon B reconciled', 60000)
  await js(win, `window.__smoke.click('[data-testid="to-review"]')`)
  await waitFor(win, `!!window.__smoke.q('[data-testid="kpi-matched"]')`, 'recon B results')
  check('Recon B KPIs (matched, doubtful, likely, unmatched A/B, AI)', await kpis(win), ['255', '16', '1', '29 / 19', '0'])
  await wait(500)
  const afterRun = await js(win, DRAFTS)
  check('Running recon B turned its draft into a session (only recon A is still a draft)', afterRun.drafts.map((d) => d.account), ['Recon A ENBD Current'])

  // Switch back to A via In progress: its state is intact.
  await openMenu(win)
  const rows = await js(win, MENU_ROWS)
  check('In progress lists A (draft, Map & rules), B (on screen) and the first Bank recon', [
    rows.some((r) => r.includes('Recon A ENBD Current') && r.includes('Draft') && r.includes('Map & rules')),
    rows.some((r) => r.includes('Recon B ENBD Current') && r.includes('On screen') && r.includes('Review: 16 doubtful')),
    rows.length
  ], [true, true, 3])
  await shot(win, '23-in-progress.png')
  await openFromMenu(win, 'Recon A ENBD Current')
  await waitFor(win, RUN_READY, 'recon A back at Map & rules')
  check('Recon A comes back at Map & rules with its account and files', await js(win, `(() => { const t = window.__smoke.text(); return t.includes('Recon A ENBD Current') && t.includes('Bank Reconciliation — Setup') && /ENBD/i.test(t) && /GL_/i.test(t) })()`), true)

  // Reload the app: both are still listed, A resumes at Map with its files.
  await js(win, `location.hash = '#/'; location.reload(); true`)
  await new Promise((r) => win.webContents.once('did-finish-load', r))
  await wait(800)
  await js(win, PAGE_HELPERS)
  await waitFor(win, `!!window.__smoke.q('[data-testid="in-progress-bank"]')`, 'dashboard in-progress count')
  check('Dashboard after reload: Bank card shows 3 in progress', await js(win, `window.__smoke.q('[data-testid="in-progress-bank"]').textContent.trim()`), '3 in progress')
  check('Dashboard In progress strip lists recons A and B', await js(win, `(() => { const t = window.__smoke.q('[data-testid="in-progress-strip"]').innerText; return t.includes('Recon A ENBD Current') && t.includes('Recon B ENBD Current') })()`), true)
  await js(win, `window.__smoke.click('[data-testid="in-progress-bank"]')`)
  await wait(400)
  await js(win, PAGE_HELPERS)
  await waitFor(win, `document.querySelectorAll('${MENU} [data-testid="in-progress-item"]').length === 3`, 'In progress menu opened from the Dashboard')
  await openFromMenu(win, 'Recon A ENBD Current')
  await waitFor(win, RUN_READY, 'recon A resumed after reload', 30000)
  check('After reload recon A resumes at Map & rules with both files', await js(win, `(() => { const t = window.__smoke.text(); return t.includes('Recon A ENBD Current') && t.includes('Bank Reconciliation — Setup') && document.querySelectorAll('ul[aria-label^="Columns in"]').length === 2 })()`), true)

  // Open B: its results are back, Map & rules can be used again (files kept), and one item is accepted.
  await openFromMenu(win, 'Recon B ENBD Current')
  await waitFor(win, `!!window.__smoke.q('[data-testid="kpi-matched"]') && window.__smoke.text().includes('Recon B ENBD Current')`, 'recon B reopened', 30000)
  check('Recon B reopened with the same counts', await kpis(win), ['255', '16', '1', '29 / 19', '0'])
  await js(win, `(() => { const b = Array.from(document.querySelectorAll('nav[aria-label="Reconciliation steps"] button')).find((x) => x.textContent.includes('Map & rules')); if (!b) throw new Error('no Map step'); b.click(); return true })()`)
  await waitFor(win, RUN_READY, 'recon B Map & rules editable')
  check('Reopened recon B can go back to Map & rules (files kept with the session)', await js(win, `!window.__smoke.text().includes('Reopened from Recon History')`), true)
  await js(win, `(() => { const b = Array.from(document.querySelectorAll('nav[aria-label="Reconciliation steps"] button')).find((x) => x.textContent.includes('Reconcile')); b.click(); return true })()`)
  await waitFor(win, `!!window.__smoke.q('[data-testid="to-review"]')`, 'recon B reconcile step')
  await js(win, `window.__smoke.click('[data-testid="to-review"]')`)
  await waitFor(win, `!!window.__smoke.q('button[aria-label="Accept"]')`, 'recon B review')
  await js(win, `window.__smoke.click('button[aria-label="Accept"]')`)
  await waitFor(win, `window.__smoke.kpi('matched') === '256'`, 'recon B accepted pair')
  await waitFor(win, `${SESSIONS}.then((list) => list && list.some((s) => s.account === 'Recon B ENBD Current' && s.audit === 1))`, 'recon B decision saved')
  check('Recon B decision saved; recon A still a draft', (await js(win, DRAFTS)).drafts.map((d) => d.account), ['Recon A ENBD Current'])
}

app.on('browser-window-created', (_e, win) => {
  win.webContents.on('console-message', (event) => {
    if (event.level === 'error') consoleErrors.push(event.message)
  })
  // The app sizes its first window to the display; the docs screenshots are always taken at 1440 × 900.
  win.once('show', () => {
    if (win.isMaximized()) win.unmaximize()
    win.setSize(1440, 900)
    win.setPosition(-3000, 0)
  })
})

require(join(ROOT, 'out', 'main', 'index.js'))

app.whenReady().then(async () => {
  mkdirSync(OUT, { recursive: true })
  let win
  for (let i = 0; i < 100 && !win; i++) {
    win = BrowserWindow.getAllWindows()[0]
    if (!win) await wait(100)
  }
  try {
    if (!win) throw new Error('The app window did not open.')
    // An off-screen window is throttled to one timer tick a second; keep it at full speed so the
    // UI-block timings below are accurate.
    win.webContents.setBackgroundThrottling(false)
    await new Promise((r) => (win.webContents.isLoading() ? win.webContents.once('did-finish-load', r) : r()))
    await wait(800)
    await js(win, PAGE_HELPERS)
    await runBank(win)
    await runGeneralHr(win)
    await runMultiRecon(win)
    if (RUN_LARGE) await runLarge(win)
  } catch (err) {
    failures.push(String(err && err.message ? err.message : err))
    console.error('FAIL', err)
    // Failure captures go to the system temp folder, never into docs/screenshots.
    if (win) {
      await shot(win, 'reco-do-wizard-smoke-failure.png', tmpdir())
        .then(() => console.log(`Failure screenshot: ${join(tmpdir(), 'reco-do-wizard-smoke-failure.png')}`))
        .catch(() => undefined)
    }
  }
  if (consoleErrors.length) console.log('Console errors:\n  ' + consoleErrors.join('\n  '))
  console.log(failures.length ? `\n${failures.length} failure(s): ${failures.join('; ')}` : '\nAll wizard smoke checks passed.')
  const code = failures.length ? 1 : 0
  win?.destroy()
  await wait(300)
  try {
    rmSync(USER_DATA, { recursive: true, force: true })
  } catch {
    // temp folder cleanup is best effort
  }
  app.exit(code)
})

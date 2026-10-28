// Checks that every main screen fits common laptop windows: 1440×900, 1229×728 (1536×960 at 125% scaling)
// and 1024×640 (the smallest window the app allows).
// Usage (bash): npx electron-vite build && env -u ELECTRON_RUN_AS_NODE npx electron scripts/responsive-smoke.cjs
//
// It runs the real main process (out/main/index.js) with a throw-away user-data folder and an off-screen window.
// At each screen (Dashboard, the Bank wizard with the sample files from Upload to Review, the side panel, the
// Save mapping and Finalise dialogs, the audit trail, the workspace pages and the six tools with their sample files) it resizes
// the window to each size and checks that:
//   - the page never scrolls sideways (document and the main content area) and has no second page-level scrollbar,
//   - tab rows stay on one row,
//   - no key element ([data-testid], cards, buttons, inputs, tabs, headings, dialogs) reaches past the right
//     edge of the window, or is cut off by a parent that hides overflow (scrollable table areas are allowed).
// Screenshots at 1229×728 go to docs/screenshots/responsive/. Exit code 1 on any failure.
const { app, BrowserWindow } = require('electron')
const { join } = require('path')
const { mkdirSync, mkdtempSync, rmSync, writeFileSync } = require('fs')
const { tmpdir } = require('os')

const ROOT = join(__dirname, '..')
const OUT = join(ROOT, 'docs', 'screenshots', 'responsive')
const USER_DATA = mkdtempSync(join(tmpdir(), 'reco-do-responsive-'))
const SAVE_DIR = join(USER_DATA, 'saved')
mkdirSync(SAVE_DIR, { recursive: true })
process.env.RECODO_SMOKE_SAVE_DIR = SAVE_DIR
app.setPath('userData', USER_DATA)

const SIZES = [
  [1440, 900],
  [1229, 728],
  [1024, 640]
]
const SHOT_SIZE = '1229x728'
// Optional: also save every size to this folder (for looking at the 1440 and 1024 layouts).
const ALL_SHOTS_DIR = process.env.RECODO_RESPONSIVE_ALL_SHOTS
if (ALL_SHOTS_DIR) mkdirSync(ALL_SHOTS_DIR, { recursive: true })

const wait = (ms) => new Promise((r) => setTimeout(r, ms))
const failures = []
let checks = 0

const PAGE_HELPERS = `
  window.__rs = {
    q: (sel) => document.querySelector(sel),
    click: (sel) => { const el = document.querySelector(sel); if (!el) throw new Error('missing ' + sel); el.click(); return true },
    press: (sel) => {
      const el = document.querySelector(sel); if (!el) throw new Error('missing ' + sel)
      el.dispatchEvent(new PointerEvent('pointerdown', { bubbles: true, button: 0, pointerType: 'mouse' }))
      el.dispatchEvent(new MouseEvent('mousedown', { bubbles: true, button: 0 }))
      return true
    },
    clickText: (text, scope) => {
      const root = scope ? document.querySelector(scope) : document
      const el = Array.from(root.querySelectorAll('button')).find((b) => b.textContent.trim() === text && !b.disabled)
      if (!el) throw new Error('no button ' + text); el.click(); return true
    },
    type: (sel, value) => {
      const i = document.querySelector(sel); if (!i) throw new Error('missing ' + sel)
      Object.getOwnPropertyDescriptor(HTMLInputElement.prototype, 'value').set.call(i, value)
      i.dispatchEvent(new Event('input', { bubbles: true })); return true
    },
    text: () => document.body.innerText,
    closeToasts: () => { document.querySelectorAll('ol li button[aria-label="Close"]').forEach((b) => b.click()); return true },
    scrollTop: () => { const m = document.getElementById('main'); if (m) m.scrollTop = 0; return true },
    describe: (el) => {
      const id = el.getAttribute('data-testid')
      const label = (el.getAttribute('aria-label') || el.innerText || el.value || '').trim().replace(/\\s+/g, ' ').slice(0, 40)
      return el.tagName.toLowerCase() + (id ? '[data-testid=' + id + ']' : '') + (label ? ' "' + label + '"' : '') + ' .' + String(el.className).slice(0, 50)
    },
    layout: () => {
      const issues = []
      const vw = window.innerWidth
      const docW = document.documentElement.scrollWidth
      if (docW > vw) issues.push('document scrollWidth ' + docW + ' > innerWidth ' + vw)
      const docH = document.documentElement.scrollHeight
      if (docH > window.innerHeight + 1) issues.push('document scrollHeight ' + docH + ' > innerHeight ' + window.innerHeight + ' (a second, page-level scrollbar)')
      // Tabs must stay on one row: a wrapped or scrolled tab row hides tabs or looks broken.
      for (const list of document.querySelectorAll('[role="tablist"]')) {
        const tabs = Array.from(list.querySelectorAll('[role="tab"]'))
        if (tabs.length > 1 && new Set(tabs.map((t) => Math.round(t.getBoundingClientRect().top))).size > 1) issues.push('tab row wraps: ' + tabs.map((t) => t.innerText.trim()).join(' | '))
        if (list.scrollWidth > list.clientWidth + 1) issues.push('tab row scrolls sideways: ' + tabs.map((t) => t.innerText.trim()).join(' | '))
      }
      const main = document.getElementById('main')
      if (main && main.scrollWidth > main.clientWidth + 1) issues.push('main content scrolls sideways (' + main.scrollWidth + ' > ' + main.clientWidth + ')')
      const sel = '[data-testid], .rounded-xl.border, button, input, select, textarea, [role="tab"], [role="dialog"], [role="alertdialog"], h1, h2, h3, table'
      const seen = new Set()
      for (const el of document.querySelectorAll(sel)) {
        const r = el.getBoundingClientRect()
        if (r.width <= 1 || r.height <= 1) continue
        const cs = getComputedStyle(el)
        if (cs.visibility === 'hidden' || cs.display === 'none') continue
        // Walk up: stop at a scroll area (its content may extend; the area itself is checked on its own);
        // a parent that hides overflow must contain the element.
        let limit = vw
        let limitBy = 'window'
        let scrolled = false
        for (let p = el.parentElement; p && p !== document.body; p = p.parentElement) {
          const ps = getComputedStyle(p)
          if (ps.overflowX === 'visible') continue
          if ((ps.overflowX === 'auto' || ps.overflowX === 'scroll') && p !== main) { scrolled = true; break }
          if (p === main) continue
          const pr = p.getBoundingClientRect()
          if (pr.right < limit) { limit = pr.right; limitBy = window.__rs.describe(p) }
        }
        if (scrolled) continue
        if (r.right > limit + 1 && r.left < limit) {
          const key = window.__rs.describe(el)
          if (seen.has(key)) continue
          seen.add(key)
          issues.push(key + ' right=' + Math.round(r.right) + ' beyond ' + limitBy + ' (' + Math.round(limit) + ')')
        }
      }
      return { vw, vh: window.innerHeight, issues: issues.slice(0, 12) }
    }
  }; true`

const js = (win, code) => win.webContents.executeJavaScript(code, true)

async function waitFor(win, code, label, timeout = 30000) {
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

async function open(win, route) {
  await js(win, `location.hash = '#${route}'; true`)
  await wait(500)
  await js(win, PAGE_HELPERS)
}

async function capture(win, file, dir = OUT) {
  let image
  for (let attempt = 0; attempt < 4 && !image; attempt++) {
    try {
      win.webContents.invalidate()
      await wait(350)
      await win.webContents.capturePage()
      win.webContents.invalidate()
      await wait(350)
      image = await win.webContents.capturePage()
    } catch {
      await wait(800)
    }
  }
  if (!image) throw new Error(`Could not capture ${file}`)
  writeFileSync(join(dir, file), image.toPNG())
}

/** Checks the current screen at every size; saves a screenshot at 1229×728. Leaves the window at 1440×900. */
async function checkScreen(win, name, { scrollTop = true } = {}) {
  await js(win, 'window.__rs.closeToasts()')
  for (const [w, h] of SIZES) {
    win.setSize(w, h)
    await wait(450)
    if (scrollTop) await js(win, 'window.__rs.scrollTop()')
    const res = await js(win, 'window.__rs.layout()')
    checks++
    const size = `${w}x${h}`
    if (res.issues.length) {
      failures.push(`${name} @ ${size}`)
      console.log(`FAIL ${name} @ ${size} (viewport ${res.vw}x${res.vh}):\n    ${res.issues.join('\n    ')}`)
    } else {
      console.log(`PASS ${name} @ ${size} (viewport ${res.vw}x${res.vh})`)
    }
    if (size === SHOT_SIZE) await capture(win, `${name}.png`)
    if (ALL_SHOTS_DIR) await capture(win, `${name}@${size}.png`, ALL_SHOTS_DIR)
  }
  win.setSize(SIZES[0][0], SIZES[0][1])
  await wait(300)
}

async function bankWizard(win) {
  await open(win, '/module/bank')
  await waitFor(win, `!!window.__rs.q('[data-testid="try-samples"]')`, 'sample button')
  await js(win, `window.__rs.click('[data-testid="try-samples"]')`)
  await waitFor(win, `window.__rs.text().includes('Both files read') && !window.__rs.q('[data-testid="to-map"]').disabled`, 'bank files read')
  await checkScreen(win, '10-bank-upload')

  await js(win, `window.__rs.click('[data-testid="to-map"]')`)
  await waitFor(win, `(() => { const b = window.__rs.q('[data-testid="run-recon"]'); return b && !b.disabled })()`, 'run enabled')
  await wait(500)
  await checkScreen(win, '11-bank-map-rules')

  await js(win, `window.__rs.clickText('Save mapping')`)
  await waitFor(win, `!!document.querySelector('[role="dialog"] input')`, 'save mapping dialog')
  await checkScreen(win, '12-dialog-save-mapping')
  await js(win, `document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); true`)
  await waitFor(win, `!document.querySelector('[role="dialog"]')`, 'dialog closed')

  await js(win, `window.__rs.click('[data-testid="run-recon"]')`)
  await waitFor(win, `!!window.__rs.q('[data-testid="to-smart"]')`, 'reconcile finished', 60000)
  await checkScreen(win, '13-bank-reconcile')

  await js(win, `window.__rs.click('[data-testid="to-smart"]')`)
  await waitFor(win, `window.__rs.text().includes('Smart Reconciliation')`, 'smart recon panel')
  await wait(400)
  await checkScreen(win, '14-bank-smart-recon')

  await js(win, `window.__rs.click('[data-testid="to-review"]')`)
  await waitFor(win, `!!window.__rs.q('[data-testid="kpi-matched"]')`, 'results')
  await wait(500)
  await checkScreen(win, '15-bank-results')

  await js(win, `window.__rs.click('[data-testid="toggle-panel"]')`)
  await waitFor(win, `window.__rs.text().includes('Unexplained difference')`, 'statement card')
  await checkScreen(win, '16-bank-results-side-panel')
  await js(win, `window.__rs.click('[data-testid="toggle-panel"]')`)

  await js(win, `window.__rs.click('button[aria-label="Accept"]')`)
  // The first decision asks for the preparer name only when Settings has none; here Settings has one, so the
  // decision goes straight in. The Finalise dialog is the review dialog checked instead.
  await waitFor(win, `window.__rs.q('[data-testid="kpi-matched"] [data-kpi-value]').textContent === '256'`, 'accepted pair')
  await js(win, `window.__rs.click('[data-testid="finalise"]')`)
  await waitFor(win, `!!document.querySelector('[role="dialog"]')`, 'finalise dialog')
  await wait(300)
  await checkScreen(win, '18-dialog-finalise', { scrollTop: false })
  await js(win, `document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); true`)
  await waitFor(win, `!document.querySelector('[role="dialog"]')`, 'finalise dialog closed')
  await js(win, `window.__rs.click('button[aria-label="Open audit trail"]')`)
  await waitFor(win, `window.__rs.text().includes('Audit trail')`, 'audit trail')
  await wait(300)
  await checkScreen(win, '19-bank-audit-trail', { scrollTop: false })
  await js(win, `document.dispatchEvent(new KeyboardEvent('keydown', { key: 'Escape', bubbles: true })); true`)
  await wait(300)

  await js(win, `window.__rs.press('[role="tab"][id$="unmatchedA"]')`)
  await wait(400)
  await checkScreen(win, '17-bank-results-unmatched-tab')
}

const TOOLS = [
  ['pdf-to-excel', 'Bank_Statement_6_pages_digital.pdf', `/Preview: \\d+ table/i.test(document.querySelector('[data-testid="preview-title"]')?.innerText ?? '')`],
  ['excel-to-pdf', 'Sheet_to_print.xlsx', `(() => { const i = document.querySelector('[data-testid="pdf-preview"]'); return !!i && i.complete && i.naturalWidth > 0 })()`],
  ['merge-pdfs', 'Merge_Part1.pdf+Merge_Part2.pdf', `document.querySelectorAll('[data-testid="merged-pages"] img').length === 5`],
  ['split-pdf', 'Split_Me_12_pages.pdf', `document.querySelectorAll('[data-testid="split-pages"] img').length === 12`],
  ['merge-files', 'Statement_Jul2026.xlsx+Statement_Aug2026.xlsx+Statement_Sep2026.xlsx', `/Merged: 142 rows/i.test(document.querySelector('[data-testid="preview-title"]')?.innerText ?? '')`],
  ['data-cleaner', 'Messy_Data_for_Cleaner.xlsx', `/After cleaning: 42 rows/i.test(document.querySelector('[data-testid="preview-title"]')?.innerText ?? '')`]
]

async function tools(win) {
  let n = 30
  for (const [id, sample, done] of TOOLS) {
    await open(win, `/tools/${id}`)
    await waitFor(win, `!!document.querySelector('[data-privacy-note]')`, `${id} screen`)
    await checkScreen(win, `${n}-tool-${id}-empty`)
    const sel = `[data-sample="${sample}"]`
    await waitFor(win, `!!document.querySelector(${JSON.stringify(sel)})`, `${id} sample button`)
    await js(win, `document.querySelector(${JSON.stringify(sel)}).click(); true`)
    await waitFor(win, done, `${id} result`, 90000)
    await wait(500)
    await checkScreen(win, `${n + 1}-tool-${id}`)
    n += 2
  }
}

app.on('browser-window-created', (_e, win) => {
  win.once('show', () => {
    if (win.isMaximized()) win.unmaximize()
    win.setPosition(-4000, 0)
  })
})

require(join(ROOT, 'out', 'main', 'index.js'))

app.whenReady().then(async () => {
  rmSync(OUT, { recursive: true, force: true })
  mkdirSync(OUT, { recursive: true })
  let win
  for (let i = 0; i < 100 && !win; i++) {
    win = BrowserWindow.getAllWindows()[0]
    if (!win) await wait(100)
  }
  try {
    if (!win) throw new Error('The app window did not open.')
    win.webContents.setBackgroundThrottling(false)
    await new Promise((r) => (win.webContents.isLoading() ? win.webContents.once('did-finish-load', r) : r()))
    await wait(800)
    if (win.isMaximized()) win.unmaximize()
    win.setPosition(-4000, 0)
    await js(win, PAGE_HELPERS)

    await open(win, '/workspace/settings')
    await waitFor(win, `!!window.__rs.q('#preparer')`, 'settings form')
    await js(win, `window.__rs.type('#preparer', 'Sana Fathima')`)
    await js(win, `window.__rs.type('#department', 'Finance — Treasury')`)
    await wait(150)
    await js(win, `window.__rs.clickText('Save settings')`)
    await waitFor(win, `window.__rs.text().includes('Settings saved')`, 'settings saved')

    await bankWizard(win)

    await open(win, '/')
    await waitFor(win, `!!window.__rs.q('[data-testid="in-progress-strip"]') && window.__rs.text().includes('Sana')`, 'dashboard with In progress')
    await checkScreen(win, '01-dashboard')

    await open(win, '/module/general')
    await waitFor(win, `!!window.__rs.q('[data-testid="try-samples"]')`, 'general upload')
    await checkScreen(win, '02-general-upload')

    await open(win, '/workspace/settings')
    await waitFor(win, `!!window.__rs.q('#preparer')`, 'settings')
    await checkScreen(win, '20-workspace-settings')
    await open(win, '/workspace/mappings')
    await waitFor(win, `window.__rs.text().includes('Mappings')`, 'mappings')
    await wait(400)
    await checkScreen(win, '21-workspace-mappings')
    await open(win, '/workspace/history')
    await waitFor(win, `window.__rs.text().includes('Recon History')`, 'history')
    await wait(400)
    await checkScreen(win, '22-workspace-history')

    await tools(win)
  } catch (err) {
    failures.push(String(err && err.message ? err.message : err))
    console.error('FAIL', err && err.message ? err.message : err)
  }
  console.log(failures.length ? `\n${failures.length} failure(s) in ${checks} checks: ${failures.join('; ')}` : `\nAll ${checks} responsive checks passed.`)
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

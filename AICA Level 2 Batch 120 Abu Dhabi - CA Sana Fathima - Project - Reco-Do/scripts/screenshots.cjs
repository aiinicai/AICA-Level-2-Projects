// Captures the README / docs overview screenshots from the real app (main process, app:// protocol, IPC bridge).
// Usage (bash): npx electron-vite build && env -u ELECTRON_RUN_AS_NODE npx electron scripts/screenshots.cjs
//
// It loads out/main/index.js with a throw-away user-data folder and keeps the window off screen. To make the
// workspace pages realistic it first fills in Settings, saves a Bank mapping, and runs the Bank and General (HR)
// samples so Recon History has entries. Then it saves 01-06 to docs/screenshots/. The wizard steps and the
// tools are captured by scripts/wizard-smoke.cjs and scripts/tools-smoke.cjs. Exit code 1 on any failure.
const { app, BrowserWindow } = require('electron')
const { join } = require('path')
const { mkdirSync, mkdtempSync, rmSync, writeFileSync } = require('fs')
const { tmpdir } = require('os')

const ROOT = join(__dirname, '..')
const OUT = join(ROOT, 'docs', 'screenshots')
const USER_DATA = mkdtempSync(join(tmpdir(), 'reco-do-shots-'))
app.setPath('userData', USER_DATA)

const wait = (ms) => new Promise((r) => setTimeout(r, ms))

const PAGE_HELPERS = `
  window.__shots = {
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
    scrollTop: () => { const m = document.getElementById('main'); if (m) m.scrollTop = 0; return true }
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

async function shot(win, file) {
  await js(win, 'window.__shots.closeToasts()')
  await wait(400)
  await js(win, 'window.__shots.scrollTop()')
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
      await wait(800)
    }
  }
  if (!image) throw new Error(`Could not capture ${file}`)
  writeFileSync(join(OUT, file), image.toPNG())
  console.log('saved', file)
}

async function fillSettings(win) {
  await open(win, '/workspace/settings')
  await waitFor(win, `!!window.__shots.q('#preparer')`, 'settings form')
  await js(win, `window.__shots.type('#preparer', 'Sana Fathima')`)
  await js(win, `window.__shots.type('#department', 'Finance — Treasury')`)
  await wait(150)
  await js(win, `window.__shots.clickText('Save settings')`)
  await waitFor(win, `window.__shots.text().includes('Settings saved')`, 'settings saved')
}

async function runToReview(win, moduleId, sample, saveMapping) {
  await open(win, `/module/${moduleId}`)
  await waitFor(win, `!!window.__shots.q('[data-testid="try-samples"]')`, 'sample button')
  if (sample) {
    await js(win, `window.__shots.press('[data-testid="try-samples"]')`)
    await waitFor(win, `!!window.__shots.q('[data-testid="sample-${sample}"]')`, 'sample menu')
    await js(win, `window.__shots.click('[data-testid="sample-${sample}"]')`)
  } else {
    await js(win, `window.__shots.click('[data-testid="try-samples"]')`)
  }
  await waitFor(win, `window.__shots.text().includes('Both files read') && !window.__shots.q('[data-testid="to-map"]').disabled`, 'files read')
  await js(win, `window.__shots.click('[data-testid="to-map"]')`)
  await waitFor(win, `(() => { const b = window.__shots.q('[data-testid="run-recon"]'); return b && !b.disabled })()`, 'run enabled')
  if (saveMapping) {
    await js(win, `window.__shots.clickText('Save mapping')`)
    await waitFor(win, `!!document.querySelector('[role="dialog"] input')`, 'save mapping dialog')
    await js(win, `document.querySelector('[role="dialog"] button[type="submit"]').click(); true`)
    await waitFor(win, `window.__shots.text().includes("Mapping '")`, 'mapping saved')
  }
  await js(win, `window.__shots.click('[data-testid="run-recon"]')`)
  await waitFor(win, `!!window.__shots.q('[data-testid="to-smart"]') || !!window.__shots.q('[data-testid="to-review"]')`, 'reconcile finished', 60000)
  if (await js(win, `!!window.__shots.q('[data-testid="to-smart"]')`)) {
    await js(win, `window.__shots.click('[data-testid="to-smart"]')`)
    await waitFor(win, `!!window.__shots.q('[data-testid="to-review"]')`, 'smart recon step')
  }
  await js(win, `window.__shots.click('[data-testid="to-review"]')`)
  await waitFor(win, `!!window.__shots.q('[data-testid="kpi-matched"]')`, 'results')
}

app.on('browser-window-created', (_e, win) => {
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
  let code = 0
  try {
    if (!win) throw new Error('The app window did not open.')
    await new Promise((r) => (win.webContents.isLoading() ? win.webContents.once('did-finish-load', r) : r()))
    await wait(800)
    await js(win, PAGE_HELPERS)

    await fillSettings(win)
    // SHOTS_ONLY=settings retakes just the Settings screenshot (no reconciliations needed).
    if (process.env.SHOTS_ONLY === 'settings') {
      await open(win, '/workspace/settings')
      await waitFor(win, `!!window.__shots.q('#preparer')`, 'settings')
      // Full-height capture so the About card (below the fold) is visible too.
      const fullHeight = await js(win, `document.getElementById('main').scrollHeight`)
      win.setSize(1440, Math.min(2400, Math.max(900, Number(fullHeight) || 900)))
      await wait(800)
      await shot(win, '04-settings.png')
      throw Object.assign(new Error('done'), { done: true })
    }
    await runToReview(win, 'bank', null, true)
    await runToReview(win, 'general', 'hr', false)

    // Fresh load so every page starts from its default state.
    await js(win, `location.hash = '#/'; location.reload(); true`)
    await new Promise((r) => win.webContents.once('did-finish-load', r))
    await wait(800)
    await open(win, '/')
    await waitFor(win, `window.__shots.text().includes('Sana')`, 'dashboard greeting')
    await shot(win, '01-dashboard.png')
    await open(win, '/module/general')
    await waitFor(win, `!!window.__shots.q('[data-testid="try-samples"]')`, 'general upload')
    await shot(win, '02-general-reconciliation.png')
    await open(win, '/tools/pdf-to-excel')
    await waitFor(win, `!!window.__shots.q('[data-privacy-note]')`, 'tool screen')
    await shot(win, '03-tool-pdf-to-excel.png')
    await open(win, '/workspace/settings')
    await waitFor(win, `!!window.__shots.q('#preparer')`, 'settings')
    await shot(win, '04-settings.png')
    await open(win, '/workspace/mappings')
    await waitFor(win, `window.__shots.text().includes('↔ GL')`, 'saved mapping listed')
    await shot(win, '05-mappings-templates.png')
    await open(win, '/workspace/history')
    await waitFor(win, `window.__shots.text().includes('Bank') && window.__shots.text().includes('HR')`, 'history entries')
    await shot(win, '06-recon-history.png')
    console.log('\nAll screenshots captured.')
  } catch (err) {
    if (err && err.done) {
      console.log('\nSettings screenshot captured.')
    } else {
      console.error('FAIL', err && err.message ? err.message : err)
      code = 1
    }
  }
  win?.destroy()
  await wait(300)
  try {
    rmSync(USER_DATA, { recursive: true, force: true })
  } catch {
    // temp folder cleanup is best effort
  }
  app.exit(code)
})

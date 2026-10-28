// Offscreen smoke test of the six tool screens in the built app (out/), including offline OCR.
// Usage (bash):  npx electron-vite build && env -u ELECTRON_RUN_AS_NODE npx electron scripts/tools-smoke.cjs
//
// Loads the real main process (app:// protocol, IPC, bundled samples), keeps its window hidden,
// clicks "Try with sample file" on each tool through webContents.executeJavaScript, checks the result,
// saves screenshots to docs/screenshots/2x-<tool>.png and answers the Save dialog with a temp folder
// (failure captures go to that temp folder too).
const { app, BrowserWindow, dialog } = require('electron')
const { join } = require('path')
const { existsSync, mkdirSync, rmSync, statSync, writeFileSync } = require('fs')
const os = require('os')

const ROOT = join(__dirname, '..')
const SHOTS = join(ROOT, 'docs', 'screenshots')
const TMP = join(os.tmpdir(), 'reco-do-tools-smoke')
rmSync(TMP, { recursive: true, force: true })
mkdirSync(join(TMP, 'saved'), { recursive: true })
mkdirSync(SHOTS, { recursive: true })

// Separate profile so the smoke run never touches the user's own database.
app.setPath('userData', join(TMP, 'profile'))

// Answer every Save dialog with a file in the temp folder.
const saved = []
dialog.showSaveDialog = async (...args) => {
  const opts = args.length > 1 ? args[1] : args[0]
  const filePath = join(TMP, 'saved', opts.defaultPath ? require('path').basename(opts.defaultPath) : 'output.bin')
  saved.push(filePath)
  return { canceled: false, filePath }
}

let win = null
app.on('browser-window-created', (_e, w) => {
  win = w
  // Painted but out of sight: shown without focus at a position off every screen.
  w.show = () => undefined
  w.setSize(1440, 960)
  w.setPosition(-4000, -4000)
  w.showInactive()
  w.setPosition(-4000, -4000)
})

require(join(ROOT, 'out', 'main', 'index.js'))

const sleep = (ms) => new Promise((r) => setTimeout(r, ms))
const results = []
const logs = []

function js(code) {
  return win.webContents.executeJavaScript(code, true)
}

async function waitFor(desc, code, timeoutMs = 30000) {
  const start = Date.now()
  for (;;) {
    let v
    try {
      v = await js(code)
    } catch (e) {
      v = undefined
    }
    if (v) return v
    if (Date.now() - start > timeoutMs) throw new Error(`Timed out waiting for: ${desc}`)
    await sleep(250)
  }
}

const text = (sel) => `(document.querySelector(${JSON.stringify(sel)})?.innerText ?? '')`

async function go(route) {
  await js(`location.hash = ${JSON.stringify('#' + route)}`)
  await waitFor(`route ${route}`, `!!document.querySelector('[data-privacy-note]') && location.hash === ${JSON.stringify('#' + route)}`)
  await sleep(300)
}

async function clickSample(files) {
  const sel = `[data-sample="${files}"]`
  await waitFor(`sample button ${files}`, `!!document.querySelector(${JSON.stringify(sel)})`)
  await js(`document.querySelector(${JSON.stringify(sel)}).click()`)
}

async function shot(name, dir = SHOTS) {
  await sleep(700)
  win.webContents.invalidate()
  await sleep(300)
  const image = await win.webContents.capturePage()
  writeFileSync(join(dir, name), image.toPNG())
}

async function download() {
  const before = saved.length
  await js(`document.querySelector('[data-action="download"]').click()`)
  const start = Date.now()
  while (saved.length === before) {
    if (Date.now() - start > 60000) throw new Error('Download did not start')
    await sleep(200)
  }
  const file = saved[saved.length - 1]
  const t0 = Date.now()
  while (!existsSync(file) || statSync(file).size === 0) {
    if (Date.now() - t0 > 60000) throw new Error(`Saved file never appeared: ${file}`)
    await sleep(200)
  }
  await sleep(300)
  return { name: require('path').basename(file), size: statSync(file).size }
}

async function step(name, fn) {
  const t = Date.now()
  try {
    const detail = await fn()
    results.push({ name, ok: true, ms: Date.now() - t, detail })
    console.log(`PASS ${name} (${Date.now() - t} ms) ${detail ?? ''}`)
  } catch (e) {
    results.push({ name, ok: false, ms: Date.now() - t, detail: e.message })
    console.log(`FAIL ${name}: ${e.message}`)
    try {
      // Failure captures go to the temp folder, never into docs/screenshots.
      await shot(`FAILED-${name.replace(/[^a-z0-9]+/gi, '-')}.png`, TMP)
    } catch {
      /* window may be gone */
    }
  }
}

process.on('unhandledRejection', (e) => {
  console.log('FATAL', e && e.stack ? e.stack : e)
  app.exit(2)
})

app.whenReady().then(async () => {
  while (!win) await sleep(100)
  win.webContents.on('console-message', (event) => {
    const level = event.level ?? ''
    if (level === 'error' || level === 'warning' || level === 3 || level === 2) logs.push(`[${level}] ${event.message}`)
  })
  // Keep the hidden page painting and its timers running at full speed.
  win.webContents.setBackgroundThrottling(false)
  await waitFor('app loaded', `!!document.querySelector('#main')`, 60000)

  await step('pdf-to-excel: digital bank statement', async () => {
    await go('/tools/pdf-to-excel')
    await clickSample('Bank_Statement_6_pages_digital.pdf')
    const title = await waitFor('preview', `/Preview: \\d+ table/i.test(${text('[data-testid="preview-title"]')}) && ${text('[data-testid="preview-title"]')}`, 60000)
    await shot('2x-pdf-to-excel.png')
    const file = await download()
    return `${title} · saved ${file.name} (${file.size} bytes)`
  })

  await step('pdf-to-excel: bank layout toggle', async () => {
    await js(`[...document.querySelectorAll('[role="radio"],button')].find((b) => b.innerText.trim() === 'Bank statement').click()`)
    await waitFor('bank mapping', `!!document.querySelector('[data-testid="bank-mapping"]')`)
    const headers = await js(`[...document.querySelectorAll('[role="columnheader"]')].map((h) => h.innerText.split('\\n')[0]).join(' | ')`)
    await shot('2x-pdf-to-excel-bank-layout.png')
    if (!/Debit/.test(headers) || !/Credit/.test(headers)) throw new Error(`Bank columns missing: ${headers}`)
    return headers
  })

  await step('pdf-to-excel: scanned page with offline OCR', async () => {
    await go('/tools/data-cleaner')
    await go('/tools/pdf-to-excel')
    await clickSample('Statement_with_scanned_page.pdf')
    const ocr = await waitFor(
      'OCR badge or error',
      `document.querySelector('[data-ocr-pages]')?.getAttribute('data-ocr-pages') || (document.querySelector('[role="alert"]')?.innerText ? 'ERROR: ' + document.querySelector('[role="alert"]').innerText : '') || ([...document.querySelectorAll('.text-unmatched,.bg-\\\\[\\\\#FFF8EA\\\\]')].map(e=>e.innerText).find(t => /OCR|not read|skipped/i.test(t)) ? 'WARN: ' + [...document.querySelectorAll('.text-unmatched,.bg-\\\\[\\\\#FFF8EA\\\\]')].map(e=>e.innerText).join(' / ') : '')`,
      240000
    )
    const title = await js(text('[data-testid="preview-title"]'))
    const low = await js(String.raw`(/Amber cells \((\d+)\)/.exec(document.body.innerText) || [0, 0])[1]`)
    await shot('2x-pdf-to-excel-ocr.png')
    if (String(ocr).startsWith('ERROR') || String(ocr).startsWith('WARN')) throw new Error(String(ocr))
    if (String(ocr) !== '3') throw new Error(`Expected page 3 to use OCR, got pages ${ocr}`)
    return `OCR pages: ${ocr} · ${title} · amber (low-confidence) cells: ${low}`
  })

  await step('pdf-to-excel: password-protected PDF', async () => {
    await clickSample('Password_protected.pdf')
    const msg = await waitFor('password message', `[...document.querySelectorAll('[role="alert"]')].map((e) => e.innerText).find((t) => /password-protected/.test(t))`)
    return msg
  })

  await step('excel-to-pdf: trial balance', async () => {
    await go('/tools/excel-to-pdf')
    await clickSample('Sheet_to_print.xlsx')
    await waitFor('first-page preview', `(() => { const i = document.querySelector('[data-testid="pdf-preview"]'); return !!i && i.complete && i.naturalWidth > 0 })()`, 60000)
    const title = await js(text('[data-testid="preview-title"]'))
    await shot('2x-excel-to-pdf.png')
    const file = await download()
    return `${title} · saved ${file.name} (${file.size} bytes)`
  })

  await step('merge-pdfs: two parts', async () => {
    await go('/tools/merge-pdfs')
    await clickSample('Merge_Part1.pdf+Merge_Part2.pdf')
    const title = await waitFor('merged pages', `/5 pages/i.test(${text('[data-testid="preview-title"]')}) && ${text('[data-testid="preview-title"]')}`)
    await waitFor('thumbnails', `document.querySelectorAll('[data-testid="merged-pages"] img').length === 5`, 30000)
    // Expand the first file to show page thumbnails with rotate / remove.
    await js(`document.querySelector('[aria-label="Show pages"]').click()`)
    await shot('2x-merge-pdfs.png')
    // Keyboard-accessible reorder: move page 1 of Part 1 later, then move Part 1 below Part 2, with the buttons.
    await js(`document.querySelector('[aria-label="Move page 1 later"]').click()`)
    await js(`document.querySelector('[aria-label="Move Merge_Part1.pdf down"]').click()`)
    const order = await waitFor(
      'reordered files',
      `(() => { const names = [...document.querySelectorAll('[data-testid="merge-file-list"] > li')].map((li) => li.querySelector('[title]')?.getAttribute('title')); return names[0] === 'Merge_Part2.pdf' && names.join(' > ') })()`
    )
    const file = await download()
    return `${title} · reordered with buttons: ${order} · saved ${file.name} (${file.size} bytes)`
  })

  await step('split-pdf: every 3 pages', async () => {
    await go('/tools/split-pdf')
    await clickSample('Split_Me_12_pages.pdf')
    await waitFor('plan', `document.querySelectorAll('[data-testid="split-plan"] li').length === 4`)
    await waitFor('thumbnails', `document.querySelectorAll('[data-testid="split-pages"] img').length === 12`, 30000)
    const plan = await js(`[...document.querySelectorAll('[data-testid="split-plan"] li')].map((l) => l.innerText.split('\\n')[0]).join(', ')`)
    await shot('2x-split-pdf.png')
    const file = await download()
    return `${plan} · saved ${file.name} (${file.size} bytes)`
  })

  await step('merge-files: three monthly statements', async () => {
    await go('/tools/merge-files')
    await clickSample('Statement_Jul2026.xlsx+Statement_Aug2026.xlsx+Statement_Sep2026.xlsx')
    const title = await waitFor('merged', `/Merged: 142 rows/i.test(${text('[data-testid="preview-title"]')}) && ${text('[data-testid="preview-title"]')}`, 60000)
    const summary = await js(text('[data-testid="merge-summary"]'))
    await shot('2x-merge-files.png')
    await js(`[...document.querySelectorAll('[role="tab"]')].find((t) => t.innerText.startsWith('Preview')).dispatchEvent(new MouseEvent('mousedown', { bubbles: true }))`)
    await sleep(400)
    await shot('2x-merge-files-preview.png')
    const file = await download()
    return `${title} · ${summary} · saved ${file.name} (${file.size} bytes)`
  })

  await step('data-cleaner: messy expense register', async () => {
    await go('/tools/data-cleaner')
    await clickSample('Messy_Data_for_Cleaner.xlsx')
    const title = await waitFor('cleaned', `/After cleaning: 42 rows/i.test(${text('[data-testid="preview-title"]')}) && ${text('[data-testid="preview-title"]')}`, 60000)
    const counts = await js(`[...document.querySelectorAll('[data-action-row]')].map((r) => r.getAttribute('data-action-row') + '=' + (r.querySelector('.num')?.innerText ?? '')).join(', ')`)
    await shot('2x-data-cleaner.png')
    const file = await download()
    return `${title} · ${counts} · saved ${file.name} (${file.size} bytes)`
  })

  const failed = results.filter((r) => !r.ok)
  writeFileSync(join(TMP, 'results.json'), JSON.stringify({ results, logs }, null, 2))
  console.log(`\n${results.length - failed.length}/${results.length} passed. Console warnings/errors: ${logs.length}`)
  for (const l of logs.slice(0, 30)) console.log('  ' + l.slice(0, 300))
  app.exit(failed.length ? 1 : 0)
})

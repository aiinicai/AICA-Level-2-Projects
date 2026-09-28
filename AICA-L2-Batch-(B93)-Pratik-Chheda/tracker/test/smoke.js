// Smoke test: node_modules/.bin/electron test/smoke.js   (uses a temporary data folder)
const { app, BrowserWindow } = require('electron');
const path = require('path'), fs = require('fs'), os = require('os');
const tmp = fs.mkdtempSync(path.join(os.tmpdir(), 'mft-'));
app.setPath('userData', tmp);
app.on('browser-window-created', (e, w) => {
  w.webContents.once('did-finish-load', async () => {
    try {
      await new Promise(r => setTimeout(r, 1500));
      const js = s => w.webContents.executeJavaScript(s);
      const mode = await js("HOST.mode");
      await js("STORE.newItems.push({id:++STORE.seq,created:'2026-09-26',company:'Desktop Lead Co',associate:'Test Associate',owner:'PC'});EDITS[5]={status:'On hold',notes:[{d:'2026-09-26',t:'desktop note'}]};persistStore();HOST.saving");
      await new Promise(r => setTimeout(r, 500));
      const ver = await js("HOST.version");
      const db = await require('../src/db').open(path.join(tmp, 'dealflow-tracker.sqlite'));
      const s = db.loadStore().store;
      const pdfHtml = await js("derive();reportHTML(reportLead('Desktop Lead Co'))");
      const pw = new BrowserWindow({ show: false }); const f = path.join(tmp, 'r.html'); fs.writeFileSync(f, pdfHtml); await pw.loadFile(f);
      const pdf = await pw.webContents.printToPDF({ pageSize: 'A4', printBackground: true, preferCSSPageSize: true, margins: { marginType: 'none' } });
      fs.writeFileSync(path.join(tmp, 'desktop_lead.pdf'), pdf);
      // 1.1 features: automation settings, Google bridge guard, Drive flag, deal pipeline
      const auto = await js("dfAPI.automationSet({baseUrl:'https://example.app.n8n.cloud',headerName:'X-Sample Advisory-Secret',secret:'smoke-secret',people:{PC:'pc@example.com'}})");
      const guard = await js("dfAPI.googleFetch({method:'GET',url:'https://example.com/x'}).then(()=>'allowed',e=>'blocked')");
      const gstat = await js("dfAPI.gcalStatus()");
      await js("setStage(5,'Mandate sent','smoke');go('pipeline')");
      await new Promise(r => setTimeout(r, 400));
      const cards = await js("document.querySelectorAll('#v-pipeline .dcard').length");
      const png = await w.webContents.capturePage(); fs.writeFileSync(path.join(tmp, 'desktop.png'), png.toPNG());
      console.log(JSON.stringify({ mode, ver, leads: s.newItems.map(x => x.company), edit5: s.edits[5], backups: fs.readdirSync(path.join(tmp, 'backups')), pdfBytes: pdf.length,
        auto: { hasSecret: auto.hasSecret, secretReturned: 'secret' in auto, people: auto.people }, guard, driveFlag: gstat.drive, pipelineCards: cards, out: tmp }));
    } catch (err) { console.log('SMOKE ERROR', err); }
    app.exit(0);
  });
});
require('../src/main.js');

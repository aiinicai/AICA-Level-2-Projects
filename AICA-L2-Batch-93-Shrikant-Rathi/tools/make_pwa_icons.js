/* Renders the PWA icons (PNG) from app_src/pwa/icon.svg and icon-maskable.svg with headless Chrome.
   Usage (from the repo root):  node tools/make_pwa_icons.js      (needs verify/node_modules/playwright)  */
const path = require("path"), fs = require("fs");
const { chromium } = require(path.join(__dirname, "..", "verify", "node_modules", "playwright"));
const SRC = path.join(__dirname, "..", "app_src", "pwa"), OUT = path.join(SRC, "icons");
(async () => {
  fs.mkdirSync(OUT, { recursive: true });
  const b = await chromium.launch({ channel: "chrome" });
  for (const [svg, size, name] of [["icon.svg", 192, "icon-192.png"], ["icon.svg", 512, "icon-512.png"],
                                   ["icon-maskable.svg", 512, "icon-maskable-512.png"], ["icon-maskable.svg", 180, "apple-touch-icon.png"]]) {
    const p = await b.newPage({ viewport: { width: size, height: size }, deviceScaleFactor: 1 });
    await p.setContent(`<html><body style="margin:0;background:transparent">${fs.readFileSync(path.join(SRC, svg), "utf8").replace("<svg ", `<svg width="${size}" height="${size}" `)}</body></html>`);
    await p.screenshot({ path: path.join(OUT, name), omitBackground: true, clip: { x: 0, y: 0, width: size, height: size } });
    await p.close();
    console.log("wrote", name);
  }
  await b.close();
})();

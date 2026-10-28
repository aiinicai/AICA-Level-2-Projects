import fs from "node:fs";
import path from "node:path";

const root = process.cwd();
const outputPublic = path.join(root, ".output", "public");
const distClient = path.join(root, "dist", "client");
const distDir = path.join(root, "dist");

if (!fs.existsSync(distDir)) {
  fs.mkdirSync(distDir, { recursive: true });
}

// 1. Copy all assets and public files from .output/public (or dist/client) and public/ to dist
if (fs.existsSync(outputPublic)) {
  // Remove old assets folder in dist first so stale hashed bundles never accumulate
  const oldDistAssets = path.join(distDir, "assets");
  if (fs.existsSync(oldDistAssets)) {
    fs.rmSync(oldDistAssets, { recursive: true, force: true });
  }
  fs.cpSync(outputPublic, distDir, { recursive: true, force: true });
  console.log("Copied .output/public files to dist/");
} else if (fs.existsSync(distClient)) {
  fs.cpSync(distClient, distDir, { recursive: true, force: true });
  console.log("Copied dist/client files to dist/");
}

const publicDir = path.join(root, "public");
if (fs.existsSync(publicDir)) {
  fs.cpSync(publicDir, distDir, { recursive: true, force: true });
  console.log("Copied public/ files to dist/");
}

// 2. Identify the most recently built CSS and JS files by mtime
const assetsDir = path.join(distDir, "assets");
let mainCss = "";
let mainJs = "";

if (fs.existsSync(assetsDir)) {
  const files = fs
    .readdirSync(assetsDir)
    .map((f) => ({
      name: f,
      mtime: fs.statSync(path.join(assetsDir, f)).mtimeMs,
    }))
    .sort((a, b) => b.mtime - a.mtime);

  const cssFiles = files.filter((f) => f.name.startsWith("styles-") && f.name.endsWith(".css"));
  if (cssFiles.length > 0) mainCss = `/assets/${cssFiles[0].name}`;

  const jsFiles = files.filter((f) => f.name.startsWith("index-") && f.name.endsWith(".js"));
  if (jsFiles.length > 0) mainJs = `/assets/${jsFiles[0].name}`;
}

console.log("Detected main CSS:", mainCss);
console.log("Detected main JS:", mainJs);

// 3. Generate production dist/index.html
const indexHtmlContent = `<!DOCTYPE html>
<html lang="en">
  <head>
    <meta charset="utf-8" />
    <meta name="viewport" content="width=device-width, initial-scale=1, viewport-fit=cover" />
    <title>Fair Share — Group Expense Sharing &amp; Bill Splitter</title>
    <meta name="description" content="Split group and personal expenses fairly with friends, roommates, and travel groups." />
    <meta property="og:title" content="Fair Share — Group Expense Sharing &amp; Bill Splitter" />
    <meta property="og:description" content="Split group and personal expenses fairly with friends, roommates, and travel groups." />
    <meta property="og:type" content="website" />
    <meta name="twitter:card" content="summary_large_image" />
    <meta name="theme-color" content="#0F2744" />
    <meta name="apple-mobile-web-app-capable" content="yes" />
    <meta name="apple-mobile-web-app-title" content="Fair Share" />
    <link rel="icon" type="image/svg+xml" href="/favicon.svg" />
    <link rel="icon" type="image/png" href="/favicon.png" />
    <link rel="manifest" href="/manifest.webmanifest" crossorigin="use-credentials" />
    <link rel="apple-touch-icon" sizes="180x180" href="/icons/apple-touch-icon.png" />
    <link rel="preconnect" href="https://fonts.googleapis.com" />
    <link rel="preconnect" href="https://fonts.gstatic.com" crossorigin="anonymous" />
    <link rel="stylesheet" href="https://fonts.googleapis.com/css2?family=Manrope:wght@400;500;600;700&amp;family=Plus+Jakarta+Sans:wght@600;700;800&amp;display=swap" />
    ${mainCss ? `<link rel="stylesheet" href="${mainCss}" />` : ""}
  </head>
  <body>
    <div id="root"></div>
    <section aria-label="Notifications alt+T" tabindex="-1" aria-live="polite" aria-relevant="additions text" aria-atomic="false" data-react-aria-top-layer="true"></section>
    <script data-tsr-stream-part="">
      (self.$R=self.$R||{})["tsr"]=[];
      self.$_TSR={h(){this.hydrated=!0,this.c()},e(){this.streamEnded=!0,this.c()},c(){this.hydrated&&this.streamEnded&&(delete self.$_TSR,delete self.$R.tsr)},p(e){this.initialized?e():this.buffer.push(e)},buffer:[]};
      $_TSR.router=($R=>$R[0]={manifest:$R[1]={routes:$R[2]={__root__:$R[3]={preloads:$R[4]=[${JSON.stringify(mainJs)}],scripts:$R[5]=[$R[6]={attrs:$R[7]={type:"module",async:!0,src:${JSON.stringify(mainJs)}}}],css:$R[8]=[$R[9]={href:${JSON.stringify(mainCss)}}]}}},matches:$R[10]=[$R[11]={i:"__root__ ",u:Date.now(),s:"success",ssr:!0}]})($R["tsr"]);
      $_TSR.e();
      {let s=document.currentScript,p;while((p=s.previousElementSibling)&&p.hasAttribute('data-tsr-stream-part'))p.remove();s.remove()}
    </script>
    ${mainJs ? `<script type="module" async="" src="${mainJs}"></script>` : ""}
    <script>document.currentScript?.remove();</script>
  </body>
</html>
`;

fs.writeFileSync(path.join(distDir, "index.html"), indexHtmlContent, "utf8");
fs.writeFileSync(path.join(distDir, "404.html"), indexHtmlContent, "utf8");
console.log("Successfully generated dist/index.html and dist/404.html");

import fs from "node:fs";
import path from "node:path";

const openNextDir = ".open-next";
const assetsDir = path.join(openNextDir, "assets");

console.log("--- Cloudflare Post-Build Step ---");

// 1. Rename worker.js to _worker.js
const workerPath = path.join(openNextDir, "worker.js");
const targetWorkerPath = path.join(openNextDir, "_worker.js");

if (fs.existsSync(workerPath)) {
  fs.renameSync(workerPath, targetWorkerPath);
  console.log("✓ Renamed worker.js to _worker.js");
} else {
  console.log("! worker.js not found, skipping rename.");
}

// 2. Move all contents from assets to the root of .open-next
if (fs.existsSync(assetsDir)) {
  const files = fs.readdirSync(assetsDir);
  for (const file of files) {
    const src = path.join(assetsDir, file);
    const dest = path.join(openNextDir, file);

    if (fs.lstatSync(src).isDirectory()) {
      fs.cpSync(src, dest, { recursive: true });
    } else {
      fs.copyFileSync(src, dest);
    }
  }
  console.log(`✓ Copied ${files.length} assets/folders to root.`);

  // Clean up assets dir
  fs.rmSync(assetsDir, { recursive: true, force: true });
  console.log("✓ Cleaned up assets directory.");
} else {
  console.log("! assets directory not found.");
}

// 3. Patch _worker.js to serve static assets from env.ASSETS
if (fs.existsSync(targetWorkerPath)) {
  let content = fs.readFileSync(targetWorkerPath, "utf8");

  // Check if it already has the fallback to avoid double patching
  if (!content.includes("env.ASSETS.fetch")) {
    const fallbackLogic = `async fetch(request, env, ctx) {
        if (env.ASSETS) {
          const url = new URL(request.url);
          if (url.pathname.startsWith('/_next/') || (url.pathname.includes('.') && !url.pathname.startsWith('/api/'))) {
            try {
              const response = await env.ASSETS.fetch(request);
              if (response.status < 400) return response;
            } catch (e) {}
          }
        }
`;
    // Inject at the start of the fetch function
    content = content.replace(/async\s+fetch\s*\(request,\s*env,\s*ctx\)\s*\{/, fallbackLogic);
    fs.writeFileSync(targetWorkerPath, content);
    console.log("✓ Patched _worker.js with static asset fallback.");
  }
}

console.log("--- Post-Build Complete ---");

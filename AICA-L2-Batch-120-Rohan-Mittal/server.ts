import http from "node:http";
import fs from "node:fs";
import path from "node:path";

const PORT = Number(process.env.PORT || 3000);
const distDir = path.resolve(process.cwd(), "dist");

const mimeTypes: Record<string, string> = {
  ".html": "text/html; charset=utf-8",
  ".css": "text/css; charset=utf-8",
  ".js": "application/javascript; charset=utf-8",
  ".png": "image/png",
  ".svg": "image/svg+xml",
  ".json": "application/json",
  ".webmanifest": "application/manifest+json",
  ".ico": "image/x-icon",
  ".txt": "text/plain; charset=utf-8",
};

export function startServer() {
  const server = http.createServer((req, res) => {
    let reqPath = (req.url || "/").split("?")[0];
    if (reqPath === "/" || reqPath === "") reqPath = "/index.html";

    let filePath = path.join(distDir, reqPath);
    if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      filePath = path.join(distDir, "index.html");
    }

    if (!fs.existsSync(filePath)) {
      res.writeHead(404, { "Content-Type": "text/plain" });
      res.end("Not Found");
      return;
    }

    const ext = path.extname(filePath);
    const contentType = mimeTypes[ext] || "application/octet-stream";

    res.writeHead(200, {
      "Content-Type": contentType,
      "Cache-Control": ext === ".html" ? "no-cache" : "public, max-age=31536000, immutable",
    });
    fs.createReadStream(filePath).pipe(res);
  });

  return server;
}

if (process.argv[1] && process.argv[1].endsWith("server.ts")) {
  const server = startServer();
  server.listen(PORT, "0.0.0.0", () => {
    console.log(`Fair Share server listening on http://0.0.0.0:${PORT}`);
  });
}

export default {
  fetch(request: Request) {
    const url = new URL(request.url);
    let reqPath = url.pathname;
    if (reqPath === "/" || reqPath === "") reqPath = "/index.html";
    let filePath = path.join(distDir, reqPath);
    if (!fs.existsSync(filePath) || fs.statSync(filePath).isDirectory()) {
      filePath = path.join(distDir, "index.html");
    }
    if (!fs.existsSync(filePath)) {
      return new Response("Not Found", { status: 404 });
    }
    const ext = path.extname(filePath);
    const contentType = mimeTypes[ext] || "application/octet-stream";
    const content = fs.readFileSync(filePath);
    return new Response(content, {
      headers: { "Content-Type": contentType },
    });
  },
};

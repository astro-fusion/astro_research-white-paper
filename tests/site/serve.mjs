// Minimal static file server for the smoke test: serves _site/ on PORT.
// (python -m http.server resets connections under Chromium's parallel loads.)
import { createServer } from "node:http";
import { createReadStream, statSync } from "node:fs";
import { extname, join, normalize, resolve } from "node:path";

const ROOT = resolve(process.argv[2] || "_site");
const PORT = Number(process.argv[3] || 4173);
const TYPES = {
  ".html": "text/html; charset=utf-8", ".js": "text/javascript", ".mjs": "text/javascript",
  ".css": "text/css", ".json": "application/json", ".svg": "image/svg+xml", ".png": "image/png",
  ".jpg": "image/jpeg", ".woff": "font/woff", ".woff2": "font/woff2", ".ojs": "text/plain",
  ".pdf": "application/pdf", ".xml": "application/xml", ".txt": "text/plain"
};

createServer((req, res) => {
  const url = decodeURIComponent((req.url || "/").split("?")[0]);
  let file = normalize(join(ROOT, url));
  if (!file.startsWith(ROOT)) { res.writeHead(403).end(); return; }
  try {
    if (statSync(file).isDirectory()) file = join(file, "index.html");
    const size = statSync(file).size;
    res.writeHead(200, { "Content-Type": TYPES[extname(file)] || "application/octet-stream", "Content-Length": size });
    createReadStream(file).pipe(res);
  } catch {
    res.writeHead(404, { "Content-Type": "text/plain" }).end("not found");
  }
}).listen(PORT, "127.0.0.1", () => console.log(`serving ${ROOT} on ${PORT}`));

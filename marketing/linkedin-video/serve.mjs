// Tiny static server for this folder: Chrome blocks web fonts on file:// pages.
// `node serve.mjs` serves it for previewing in a browser; render.mjs/check.mjs import start().
import { createServer } from "node:http";
import { readFile } from "node:fs/promises";
import { extname, join, normalize } from "node:path";
import { fileURLToPath } from "node:url";

const ROOT = fileURLToPath(new URL(".", import.meta.url));
const TYPES = { ".html": "text/html", ".css": "text/css", ".js": "text/javascript", ".woff2": "font/woff2", ".png": "image/png" };

export function start(port = 0) {
  const server = createServer(async (req, res) => {
    const path = normalize(decodeURIComponent(new URL(req.url, "http://x").pathname)).replace(/^([/\\])+/, "") || "index.html";
    if (path.startsWith("..")) return res.writeHead(403).end();
    try {
      const body = await readFile(join(ROOT, path));
      res.writeHead(200, { "content-type": TYPES[extname(path)] ?? "application/octet-stream" }).end(body);
    } catch {
      res.writeHead(404).end();
    }
  });
  return new Promise((resolve) =>
    server.listen(port, "127.0.0.1", () => resolve({ url: `http://127.0.0.1:${server.address().port}/`, close: () => server.close() }))
  );
}

if (process.argv[1] === fileURLToPath(import.meta.url)) {
  const { url } = await start(5300);
  console.log(`Preview: ${url}`);
}

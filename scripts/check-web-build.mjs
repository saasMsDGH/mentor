/** Check actual build artifacts for same-origin routing and private URL leaks. */
import assert from "node:assert/strict";
import fs from "node:fs/promises";
import path from "node:path";
const backend = process.env.API_INTERNAL_URL;
if (!backend) throw new Error("API_INTERNAL_URL must be explicit when checking a qualification build");
const hostname = new URL(backend).hostname;
const routes = JSON.parse(await fs.readFile(".next/routes-manifest.json", "utf8"));
const rewrites = routes.rewrites.beforeFiles;
assert(rewrites.some(r => r.source === "/api/:path*" && r.destination === `${backend}/:path*`));
assert(rewrites.some(r => r.source === "/api/chat" && r.destination === `${backend}/chat/`));
for (const group of routes.headers) {
  const csp = group.headers.find(h => h.key === "Content-Security-Policy");
  if (csp) assert(!csp.value.includes(hostname), "Private backend host leaked in browser CSP");
}
async function scan(dir) {
  for (const entry of await fs.readdir(dir, { withFileTypes: true })) {
    const name = path.join(dir, entry.name);
    if (entry.isDirectory()) await scan(name);
    else if (name.endsWith(".js")) assert(!(await fs.readFile(name, "utf8")).includes(hostname), "Private backend host leaked in a browser bundle");
  }
}
await scan(".next/static");
console.log("Web build: same-origin API proxy, chat route and private host isolation verified");

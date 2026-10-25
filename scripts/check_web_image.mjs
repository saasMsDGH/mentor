/** Executed inside the isolated standalone web container. */
import assert from "node:assert/strict";
import fs from "node:fs/promises";
let live = false;
for (let attempt = 0; attempt < 60; attempt++) {
  try {
    const response = await fetch("http://127.0.0.1:3001", { signal: AbortSignal.timeout(2000) });
    if (response.ok) {
      assert(!response.headers.get("content-security-policy")?.includes("mentor-api"));
      live = true;
      break;
    }
  } catch { /* Startup is bounded below. */ }
  await new Promise(resolve => setTimeout(resolve, 500));
}
assert(live, "Standalone web image did not become live");
const root = "http://127.0.0.1:3001";
assert.equal((await fetch(`${root}/api/health/live`)).status, 200);
const health = await (await fetch(`${root}/api/health`)).json();
assert.equal(health.database_backend, "postgresql");
assert.equal(health.schema, "ready");
assert.equal((await fetch(`${root}/api/courses/`)).status, 401);
assert.equal((await fetch(`${root}/api/health/ready`)).status, 503);
const notice = await fetch(`${root}/licenses/space-grotesk/OFL.txt`);
assert.equal(notice.status, 200);
assert((await notice.text()).includes("SIL OPEN FONT LICENSE"));
assert.equal(process.getuid(), 1001);
const inventory = JSON.parse(await fs.readFile("/usr/share/licenses/mentor/npm/manifest.json", "utf8"));
assert(inventory.some(pkg => pkg.name === "next"));
console.log("Standalone web image: same-origin proxy, PostgreSQL health, anonymous access denial and license notices verified");

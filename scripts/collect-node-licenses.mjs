/** Retain package license notices when Next.js traces a standalone runtime. */
import fs from "node:fs/promises";
import path from "node:path";
const root = process.cwd();
const output = path.join(root, "THIRD_PARTY_LICENSES");
const inventory = [];
async function collect(directory) {
  let entries;
  try { entries = await fs.readdir(directory, { withFileTypes: true }); }
  catch (error) { if (error.code === "ENOENT") return; throw error; }
  for (const entry of entries) {
    if (!entry.isDirectory() || entry.name.startsWith(".")) continue;
    const dir = path.join(directory, entry.name);
    if (entry.name.startsWith("@")) { await collect(dir); continue; }
    let pkg;
    try { pkg = JSON.parse(await fs.readFile(path.join(dir, "package.json"), "utf8")); }
    catch (error) { if (error.code === "ENOENT") continue; throw error; }
    const notices = (await fs.readdir(dir)).filter(name => /^(license|licence|copying|notice)(\.|$)/i.test(name));
    const relative = path.relative(path.join(root, "node_modules"), dir);
    const dest = path.join(output, relative);
    await fs.mkdir(dest, { recursive: true });
    for (const notice of notices) {
      await fs.cp(path.join(dir, notice), path.join(dest, notice), { recursive: true });
    }
    inventory.push({ name: pkg.name, version: pkg.version, license: pkg.license ?? pkg.licenses ?? null, notices, path: relative });
    await collect(path.join(dir, "node_modules"));
  }
}
await collect(path.join(root, "node_modules"));
await fs.mkdir(output, { recursive: true });
inventory.sort((a, b) => a.path.localeCompare(b.path));
await fs.writeFile(path.join(output, "manifest.json"), JSON.stringify(inventory, null, 2));
console.log(`Retained available license notices for ${inventory.length} installed npm packages`);

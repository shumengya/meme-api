import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const memeRoot = path.join(__dirname, "..", "public", "meme");
const outFile = path.join(__dirname, "..", "src", "manifest.json");

/** @param {string} dirPath */
function listWebpFiles(dirPath) {
  if (!fs.existsSync(dirPath)) return [];
  return fs
    .readdirSync(dirPath)
    .filter((f) => f.toLowerCase().endsWith(".webp"))
    .sort((a, b) => a.localeCompare(b, undefined, { numeric: true }));
}

function main() {
  /** @type {{ generatedAt: string; categories: Array<{ id: string; name: string; items: Array<{ file: string; path: string }> }> }} */
  const payload = {
    generatedAt: new Date().toISOString(),
    categories: [],
  };

  if (fs.existsSync(memeRoot)) {
    const dirs = fs.readdirSync(memeRoot, { withFileTypes: true });
    for (const ent of dirs) {
      if (!ent.isDirectory()) continue;
      const id = ent.name;
      const dirPath = path.join(memeRoot, id);
      const files = listWebpFiles(dirPath);
      if (!files.length) continue;
      payload.categories.push({
        id,
        name: id,
        items: files.map((file) => ({
          file,
          path: `${id}/${file}`,
        })),
      });
    }
  }

  payload.categories.sort((a, b) => a.id.localeCompare(b.id, "zh-Hans-CN"));
  fs.mkdirSync(path.dirname(outFile), { recursive: true });
  fs.writeFileSync(outFile, `${JSON.stringify(payload, null, 2)}\n`, "utf8");
  console.log(
    `manifest: ${payload.categories.length} categories, ${payload.categories.reduce((n, c) => n + c.items.length, 0)} webp`
  );
}

main();

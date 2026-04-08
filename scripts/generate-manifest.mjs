import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, "..");
const sourceDir = path.join(repoRoot, "原图");
const publicMeme = path.join(repoRoot, "public", "meme");
const outFile = path.join(repoRoot, "public", "memes.json");

const NUMBERED_ASSET_RE = /^(\d+)\.(webp|gif)$/i;

/**
 * Mirror srcDir into destDir without fs.cpSync (avoids native crashes on huge trees / some Node+Win builds).
 */
function copyTreeIterative(srcDir, destDir) {
  fs.mkdirSync(destDir, { recursive: true });
  /** @type {Array<[string, string]>} */
  const stack = [[srcDir, destDir]];
  let files = 0;
  while (stack.length) {
    const [src, dest] = stack.pop();
    const entries = fs.readdirSync(src, { withFileTypes: true });
    for (const ent of entries) {
      const s = path.join(src, ent.name);
      const d = path.join(dest, ent.name);
      if (ent.isDirectory()) {
        fs.mkdirSync(d, { recursive: true });
        stack.push([s, d]);
      } else if (ent.isFile()) {
        fs.copyFileSync(s, d);
        files += 1;
      }
    }
  }
  return files;
}

function syncSourceToPublic() {
  console.log("build: mirroring 原图/ -> public/meme/ ...");
  if (!fs.existsSync(sourceDir)) {
    console.warn("原图/ not found — 请先运行 convert_to_webp.py，或保留 public/meme");
    return false;
  }
  fs.mkdirSync(path.dirname(publicMeme), { recursive: true });
  if (fs.existsSync(publicMeme)) {
    fs.rmSync(publicMeme, { recursive: true, force: true });
  }
  fs.mkdirSync(publicMeme, { recursive: true });
  const n = copyTreeIterative(sourceDir, publicMeme);
  console.log(`synced 原图/ -> public/meme/ (${n} files copied)`);
  return true;
}

/** @param {string} dirPath */
function listNumberedAssets(dirPath) {
  if (!fs.existsSync(dirPath)) return [];
  return fs
    .readdirSync(dirPath)
    .filter((f) => NUMBERED_ASSET_RE.test(f))
    .sort((a, b) => {
      const na = parseInt(a.replace(NUMBERED_ASSET_RE, "$1"), 10);
      const nb = parseInt(b.replace(NUMBERED_ASSET_RE, "$1"), 10);
      return na - nb;
    });
}

function main() {
  syncSourceToPublic();

  const scanRoot = fs.existsSync(publicMeme) ? publicMeme : sourceDir;

  /** @type {{ generatedAt: string; categories: Array<{ id: string; name: string; items: Array<{ file: string; path: string }> }> }} */
  const payload = {
    generatedAt: new Date().toISOString(),
    categories: [],
  };

  if (fs.existsSync(scanRoot)) {
    const dirs = fs.readdirSync(scanRoot, { withFileTypes: true });
    for (const ent of dirs) {
      if (!ent.isDirectory()) continue;
      const id = ent.name;
      const dirPath = path.join(scanRoot, id);
      const files = listNumberedAssets(dirPath);
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
  const n = payload.categories.reduce((acc, c) => acc + c.items.length, 0);
  console.log(`manifest: ${payload.categories.length} categories, ${n} assets (webp/gif)`);
}

try {
  main();
} catch (err) {
  console.error("generate-manifest failed:", err);
  process.exitCode = 1;
}

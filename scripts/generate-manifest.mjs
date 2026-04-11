import fs from "node:fs";
import path from "node:path";
import { fileURLToPath } from "node:url";

const __dirname = path.dirname(fileURLToPath(import.meta.url));
const repoRoot = path.join(__dirname, "..");
const rawDir = path.join(repoRoot, "原图");
const processedDir = path.join(repoRoot, "原图-已处理");
const publicDir = path.join(repoRoot, "public");
const distDir = path.join(repoRoot, "dist");
const publicMeme = path.join(publicDir, "meme");
const distMeme = path.join(distDir, "meme");
const argv = process.argv.slice(2);
/** 强制从 原图-已处理/原图 扫描清单（忽略 public/meme 里已有素材） */
const manifestFromSource = argv.includes("--manifest-from-source");

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

/**
 * 清空并重建 dist/：复制 public/（需已写好 public/memes.json），再确保 dist/memes.json 一致。
 */
function rebuildDist(manifestJson) {
  if (!fs.existsSync(publicDir)) {
    console.warn("public/ not found — only writing dist/memes.json");
    fs.mkdirSync(distDir, { recursive: true });
    fs.writeFileSync(path.join(distDir, "memes.json"), manifestJson, "utf8");
    return;
  }
  if (fs.existsSync(distDir)) {
    fs.rmSync(distDir, { recursive: true, force: true });
  }
  fs.mkdirSync(distDir, { recursive: true });
  const n = copyTreeIterative(publicDir, distDir);
  fs.writeFileSync(path.join(distDir, "memes.json"), manifestJson, "utf8");
  console.log(`build: public/ -> dist/ (${n} files), dist/memes.json written`);
}

function pickManifestRoot() {
  if (fs.existsSync(processedDir)) return processedDir;
  return rawDir;
}

/**
 * 部署时以 public/meme 为准（你手动拷入的成品）；本地未拷素材时仍可从 原图-已处理 生成清单。
 */
function resolveScanRoot() {
  if (manifestFromSource) {
    const primary = pickManifestRoot();
    if (fs.existsSync(primary)) return { root: primary, label: primary === processedDir ? "原图-已处理/" : "原图/" };
    if (fs.existsSync(publicMeme)) return { root: publicMeme, label: "public/meme/ (--manifest-from-source 但源目录缺失，回退)" };
    if (fs.existsSync(distMeme)) return { root: distMeme, label: "dist/meme/ (回退)" };
    return { root: null, label: "" };
  }
  if (countPublicMemeNumberedFiles() > 0) {
    return { root: publicMeme, label: "public/meme/" };
  }
  const primary = pickManifestRoot();
  if (fs.existsSync(primary)) {
    return { root: primary, label: primary === processedDir ? "原图-已处理/" : "原图/" };
  }
  if (fs.existsSync(publicMeme)) return { root: publicMeme, label: "public/meme/" };
  if (fs.existsSync(distMeme)) return { root: distMeme, label: "dist/meme/" };
  return { root: null, label: "" };
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

/** 统计 public/meme 下已存在的编号素材数量（与图库实际可加载文件一致） */
function countPublicMemeNumberedFiles() {
  if (!fs.existsSync(publicMeme)) return 0;
  let n = 0;
  for (const ent of fs.readdirSync(publicMeme, { withFileTypes: true })) {
    if (!ent.isDirectory()) continue;
    const dirPath = path.join(publicMeme, ent.name);
    for (const f of fs.readdirSync(dirPath)) {
      if (NUMBERED_ASSET_RE.test(f)) n += 1;
    }
  }
  return n;
}

function main() {
  const { root: scanRoot, label: scanLabel } = resolveScanRoot();
  console.log(
    `build: memes.json 扫描自 ${scanLabel || "(无)"}（不修改 public/meme/；素材请自行拷入）`
  );

  /** @type {{ generatedAt: string; categories: Array<{ id: string; name: string; items: Array<{ file: string; path: string }> }> }} */
  const payload = {
    generatedAt: new Date().toISOString(),
    categories: [],
  };

  if (scanRoot && fs.existsSync(scanRoot)) {
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
  const n = payload.categories.reduce((acc, c) => acc + c.items.length, 0);
  const onDisk = countPublicMemeNumberedFiles();
  const scannedPublicMeme = scanRoot === publicMeme;
  if (!scannedPublicMeme && onDisk > 0 && onDisk < n) {
    console.warn(
      `警告: 清单来自「${scanLabel.replace(/\/$/, "")}」共 ${n} 个编号素材，但 public/meme/ 里只有 ${onDisk} 个；部署请把「原图-已处理」整夹拷进 public/meme/ 后再 build，或删空 public/meme 仅用源目录清单。`
    );
  } else if (n > 0 && onDisk === 0 && fs.existsSync(publicMeme)) {
    console.warn(
      "警告: public/meme/ 存在但未发现编号 .webp/.gif，图库可能没有图片。"
    );
  }

  const json = `${JSON.stringify(payload, null, 2)}\n`;
  fs.mkdirSync(publicDir, { recursive: true });
  fs.writeFileSync(path.join(publicDir, "memes.json"), json, "utf8");
  rebuildDist(json);

  console.log(`manifest: ${payload.categories.length} categories, ${n} assets (webp/gif)`);
  console.log(`wrote public/memes.json + dist/memes.json；public/meme/ 中现有 ${onDisk} 个可加载素材`);
}

try {
  main();
} catch (err) {
  console.error("generate-manifest failed:", err);
  process.exitCode = 1;
}

import rawManifest from "./manifest.json";

export interface Env {
  ASSETS: Fetcher;
}

interface MemeItem {
  file: string;
  path: string;
}

interface MemeCategory {
  id: string;
  name: string;
  items: MemeItem[];
}

interface MemeManifest {
  generatedAt: string;
  categories: MemeCategory[];
}

const MANIFEST = rawManifest as MemeManifest;

function corsHeaders(): HeadersInit {
  return {
    "Access-Control-Allow-Origin": "*",
    "Access-Control-Allow-Methods": "GET, HEAD, OPTIONS",
    "Access-Control-Allow-Headers": "Content-Type",
  };
}

function mergeHeaders(
  base: HeadersInit,
  extra: Record<string, string>
): Headers {
  const h = new Headers(base);
  for (const [k, v] of Object.entries(extra)) h.set(k, v);
  return h;
}

function withCors(res: Response): Response {
  const headers = new Headers(res.headers);
  for (const [k, v] of Object.entries(corsHeaders())) {
    headers.set(k, v);
  }
  return new Response(res.body, {
    status: res.status,
    statusText: res.statusText,
    headers,
  });
}

function jsonResponse(data: unknown, status = 200): Response {
  return new Response(JSON.stringify(data), {
    status,
    headers: mergeHeaders(corsHeaders(), {
      "content-type": "application/json; charset=utf-8",
      "cache-control": "public, max-age=60",
    }),
  });
}

function memePathToUrl(origin: string, relPath: string): string {
  const segments = relPath.split("/").map((s) => encodeURIComponent(s));
  return `${origin}/meme/${segments.join("/")}`;
}

function homeHtml(origin: string): string {
  const exampleCategory = "白色小人";
  const exampleFile = "1.webp";
  const examplePath = `${exampleCategory}/${exampleFile}`;
  const exampleUrl = memePathToUrl(origin, examplePath);

  return `<!DOCTYPE html>
<html lang="zh-Hans">
<head>
  <meta charset="utf-8" />
  <meta name="viewport" content="width=device-width, initial-scale=1" />
  <title>meme-api · ${origin.replace(/^https?:\/\//, "")}</title>
  <style>
    :root { color-scheme: light dark; font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, Roboto, "PingFang SC","Microsoft YaHei", sans-serif; line-height: 1.55; }
    body { max-width: 52rem; margin: 2rem auto; padding: 0 1.25rem; }
    code, pre { font-family: ui-monospace, SFMono-Regular, Menlo, Consolas, monospace; font-size: 0.92em; }
    pre { overflow: auto; padding: 0.9rem 1rem; border-radius: 8px; background: color-mix(in oklab, Canvas 92%, CanvasText 8%); }
    a { color: inherit; }
    h1 { font-size: 1.35rem; }
    h2 { font-size: 1.05rem; margin-top: 1.75rem; }
    .muted { opacity: 0.78; font-size: 0.92rem; }
  </style>
</head>
<body>
  <h1>meme-api</h1>
  <p class="muted">资源均为 <strong>WebP</strong>（含静态与动图）。直链可被外部引用；JSON API 已开启跨域 (CORS)。</p>
  <p><a href="/memes">浏览图库（分页、按文件夹分类、点击复制链接）</a></p>

  <h2>获取表情包列表</h2>
  <p><code>GET /api/v1/memes</code></p>
  <p>返回所有分类及文件相对路径；前端与脚本可用其拼接直链。</p>
  <pre>curl -sS "${origin}/api/v1/memes"</pre>

  <h2>直链访问单张表情包</h2>
  <p>文件位于仓库目录 <code>public/meme/&lt;分类&gt;/&lt;文件名&gt;.webp</code>，对应 URL：</p>
  <p><code>GET /meme/&lt;分类&gt;/&lt;文件名&gt;.webp</code></p>
  <pre>${exampleUrl}</pre>
  <p class="muted">中文或多段路径请使用编码后的 URL（浏览器会自动处理，图库「复制链接」亦为已编码地址）。</p>

  <h2>维护流程</h2>
  <ol>
    <li>将 WebP 放入 <code>public/meme/你的文件夹名/</code>（可与本地 <code>convert_to_webp.py</code> 输出结构一致）。</li>
    <li>运行 <code>npm run build</code> 重新生成 <code>src/manifest.json</code>。</li>
    <li><code>npm run deploy</code> 部署到 Cloudflare。</li>
  </ol>
</body>
</html>`;
}

export default {
  async fetch(request: Request, env: Env): Promise<Response> {
    if (request.method === "OPTIONS") {
      return new Response(null, { headers: corsHeaders() });
    }

    const url = new URL(request.url);
    const { pathname } = url;

    if (pathname === "/api/v1/memes" || pathname === "/api/v1/memes/") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        return new Response("Method Not Allowed", { status: 405, headers: corsHeaders() });
      }
      const body =
        request.method === "HEAD" ? null : JSON.stringify(enrichedManifest(url.origin));
      return new Response(body, {
        status: 200,
        headers: mergeHeaders(corsHeaders(), {
          "content-type": "application/json; charset=utf-8",
          "cache-control": "public, max-age=60",
        }),
      });
    }

    if (pathname === "/" || pathname === "/index.html") {
      if (request.method !== "GET" && request.method !== "HEAD") {
        return new Response("Method Not Allowed", { status: 405 });
      }
      const html = homeHtml(url.origin);
      return new Response(request.method === "HEAD" ? null : html, {
        status: 200,
        headers: {
          "content-type": "text/html; charset=utf-8",
          "cache-control": "public, max-age=300",
        },
      });
    }

    if (
      pathname === "/memes" ||
      pathname === "/memes/" ||
      pathname === "/memes/index.html"
    ) {
      // 勿请求 /memes/index.html：默认 html_handling 会 307 到 /memes，而 Worker 再次取 index.html 会形成无限重定向。
      const assetUrl = new URL("/memes/", url.origin);
      const res = await env.ASSETS.fetch(new Request(assetUrl, request));
      return withCors(res);
    }

    if (pathname.startsWith("/meme/")) {
      const res = await env.ASSETS.fetch(request);
      if (res.status === 404) {
        return new Response("Not Found", { status: 404, headers: corsHeaders() });
      }
      return withCors(res);
    }

    return new Response("Not Found", { status: 404, headers: corsHeaders() });
  },
} satisfies ExportedHandler<Env>;

function enrichedManifest(origin: string) {
  return {
    generatedAt: MANIFEST.generatedAt,
    baseUrl: origin,
    categories: MANIFEST.categories.map((c) => ({
      id: c.id,
      name: c.name,
      items: c.items.map((item) => ({
        file: item.file,
        path: item.path,
        url: memePathToUrl(origin, item.path),
      })),
    })),
  };
}

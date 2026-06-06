<div align="center">

# 萌芽表情包图库 meme-api

一个部署在 **Cloudflare Pages** 的纯静态表情包图库 + 公开 API。
打开网页就能翻、一键复制链接 / Markdown / HTML，也支持直链外链和 JSON 接口拉清单。

[![Site](https://img.shields.io/website?url=https%3A%2F%2Fmeme.smyhub.com&label=%E5%9C%A8%E7%BA%BF%E5%9B%BE%E5%BA%93&logo=cloudflare&style=flat-square)](https://meme.smyhub.com)
[![API](https://img.shields.io/badge/API-memes.json-orange?style=flat-square)](https://meme.smyhub.com/memes.json)
[![License: Code MIT](https://img.shields.io/badge/%E4%BB%A3%E7%A0%81-MIT-blue?style=flat-square)](./LICENSE)
[![License: Assets CC BY-NC-SA 4.0](https://img.shields.io/badge/%E7%B4%A0%E6%9D%90-CC%20BY--NC--SA%204.0-lightgrey?style=flat-square)](./ASSET_LICENSE.md)
[![GitHub stars](https://img.shields.io/github/stars/shumengya/meme-api?style=flat-square)](https://github.com/shumengya/meme-api/stargazers)
[![GitHub forks](https://img.shields.io/github/forks/shumengya/meme-api?style=flat-square)](https://github.com/shumengya/meme-api/network)
[![Last commit](https://img.shields.io/github/last-commit/shumengya/meme-api?style=flat-square)](https://github.com/shumengya/meme-api/commits/main)

[在线浏览](https://meme.smyhub.com) · [API 文档](https://meme.smyhub.com/readme/) · [更新日志](./CHANGELOG.md)

</div>

---

## ✨ 这是什么

| 端 | 说明 |
| --- | --- |
| 🌐 **网页图库** | 分类侧边栏 + 移动端 4 列 / 桌面 12 列网格，搜索、暗色模式、键盘可达 |
| 📋 **一键复制** | 点开任意表情可复制 URL / Markdown / HTML（HTML 宽度 96–400px 可选） |
| ⬇️ **原图下载** | 直接下载原图，文件名保持原编号 |
| 🔗 **静态直链** | `/meme/<分类>/<编号>.webp` 可被任何网页、博客、聊天工具直接引用 |
| 📜 **JSON API** | `/memes.json`（兼容 `/api/v1/memes`）返回完整清单，**已配置 CORS** |

> 收录 **51 个分类、约 2600+ 张** WebP / GIF 表情包，全部经过统一处理：最长边缩放至 250px、动图统一存为 GIF。

## 🖼 截图

> 在线版：<https://meme.smyhub.com>

<details>
<summary>🖥️ 桌面端（点击展开）</summary>

```
┌──────────────────────────────────────────────────────────────┐
│ 萌芽表情包图库ﾍ(=^･ω･^=)ﾉ   说明 · memes.json               │
├──────────┬───────────────────────────────────────────────────┤
│ 分类      │  白色小人 · 224   滑稽 · 282   金馆长熊猫 · 304   │
│ 🔍 搜索… │  抹茶旦旦 · 227   抹茶旦旦2 · 120 …               │
│ 全部      │ ┌────┬────┬────┬────┬────┬────┬────┬────┐        │
│ 白色小人  │ │ 1  │ 2  │ 3  │ 4  │ 5  │ 6  │ 7  │ …  │        │
│ 白色小人2 │ └────┴────┴────┴────┴────┴────┴────┴────┘        │
│ …         │ (12 列 × 自动行，点击任意缩略图弹出操作面板)       │
└──────────┴───────────────────────────────────────────────────┘
```

</details>

<details>
<summary>📱 移动端（点击展开）</summary>

```
┌────────────────────────┐
│ 萌芽表情包图库 …       │
├────────────────────────┤
│ ☰  分类                │
│ 白色小人 · 224         │
│ 滑稽 · 282             │
│ 金馆长熊猫 · 304       │
│ …                      │
├────────────────────────┤
│ ┌──┬──┬──┬──┐          │
│ │1 │2 │3 │4 │  (4 列)  │
│ ├──┼──┼──┼──┤          │
│ │5 │6 │7 │8 │          │
│ └──┴──┴──┴──┘          │
└────────────────────────┘
```

</details>

## 🚀 快速开始

### 在线使用

直接打开 <https://meme.smyhub.com>，分类、搜索、复制随便玩。

### 引用单张表情

任意 HTML / Markdown / 聊天工具里粘贴：

```markdown
# Markdown
![哈哈](https://meme.smyhub.com/meme/%E7%99%BD%E8%89%B2%E5%B0%8F%E4%BA%BA/1.webp)
```

```html
<!-- HTML（宽度 240px，自适应） -->
<img src="https://meme.smyhub.com/meme/%E7%99%BD%E8%89%B2%E5%B0%8F%E4%BA%BA/1.webp"
     alt="哈哈" loading="lazy" width="240"
     style="max-width:240px;width:100%;height:auto" />
```

> 路径里的中文 `分类` 名必须 URL 编码；图库的「复制链接」按钮已帮你编好。

### 拉取完整清单

```bash
curl -sS "https://meme.smyhub.com/memes.json"
# 老接口仍兼容：
curl -sS "https://meme.smyhub.com/api/v1/memes"
```

返回结构（节选）：

```json
{
  "generatedAt": "2026-05-19T13:01:45.229Z",
  "categories": [
    {
      "id": "白色小人",
      "name": "白色小人",
      "items": [
        { "file": "1.webp", "path": "白色小人/1.webp" },
        { "file": "2.webp", "path": "白色小人/2.webp" }
      ]
    }
  ]
}
```

拼接规则：`{BASE}/meme/{category.id}/{item.file}`。

## 🛠 本地开发

> 需要 **Node.js ≥ 18** 和 **Python ≥ 3.8**（仅当你需要重新处理图片时才用得到 Python）。

```bash
# 1. 克隆
git clone https://github.com/shumengya/meme-api.git
cd meme-api

# 2. 安装依赖（只需要 wrangler，体积很小）
npm install

# 3. 构建（生成 dist/，含 memes.json）
npm run build

# 4. 本地预览（http://localhost:8788）
npm run dev
```

可选的构建变体：

| 命令 | 作用 |
| --- | --- |
| `npm run build` | 默认构建。清单优先扫描 `public/meme/`（已拷入的成品），否则回退 `原图-已处理/` / `原图/` |
| `npm run build:manifest-from-source` | **强制**按 `原图-已处理/`（无则 `原图/`）生成清单，不看 `public/meme/` |
| `npm run dev` | 构建 + 起 `serve` 静态服务在 8788 端口 |
| `npm run deploy:preview` | 用 `wrangler` 部署到 Cloudflare Pages **预览**分支 |
| `npm run deploy:upload` | 用 `wrangler` 部署到 Cloudflare Pages **生产**分支（仅直连 CLI 的项目用） |

## 📦 添加 / 处理新表情

`public/meme/` 里已经是**可直接部署的成品**（已编号、已缩放、动图已是 GIF）。
当你拿到新的原图想加入，按下面流程走：

```bash
# 1. 把未编号的源素材丢进 原图/<分类名>/
mkdir -p 原图/我的新分类
cp ~/Downloads/xxx.png 原图/我的新分类/

# 2. 装依赖（一次性）
python -m pip install pillow

# 3. 转换：自动编号、统一 webp / gif、最长边缩放到 250px
python 转化.py
# 产物落到 原图-已处理/，原图默认保留；想清源可加 --delete-sources

# 4. 拷入发布目录
cp -r 原图-已处理/我的新分类 public/meme/

# 5. 重新生成清单
npm run build
```

> `转化.py` 的细节（多线程、zip 批处理、WebP→GIF 动图等）见脚本顶部 docstring。

## 🚢 部署到 Cloudflare Pages

### 方式 A：连接 Git（推荐）

1. 在 Cloudflare 控制台创建 Pages 项目，连接本仓库 `main` 分支
2. 构建设置：
   - **构建命令**：`npm run build`
   - **构建输出目录**：`dist`
3. 每次 `git push` 都会自动触发部署

### 方式 B：CLI 直传

```bash
npm install
npx wrangler login                 # 第一次需要登录
npm run deploy:upload              # 部署到生产
# 或
npm run deploy:preview             # 部署到 preview 分支
```

> Git 项目里 `wrangler pages deploy` 通常会落到**预览**环境，属正常。

## 🗂 项目结构

```
meme-api/
├── 原图/                      # 源素材（未编号、可能未处理）
├── 转化.py                    # Python 一键处理脚本（Pillow）
├── scripts/
│   └── generate-manifest.mjs  # 生成 memes.json + 复制 public/ -> dist/
├── public/                    # 构建源（直接作为站点根被复制）
│   ├── index.html             # 图库前端（单文件，零依赖）
│   ├── _headers               # CORS 等响应头
│   ├── _redirects             # 兼容旧路径（/memes -> /）
│   ├── memes.json             # 由脚本生成的清单
│   ├── meme/                  # 处理后的素材（已编号 .webp / .gif）
│   └── readme/index.html      # 在线 API 说明页
├── dist/                      # 构建产物（git 忽略）
├── package.json
└── .gitignore
```

## ⚙️ 配置

| 位置 | 作用 |
| --- | --- |
| `public/_headers` | `memes.json` 和 `/api/v1/memes` 的 CORS 头（已开启 `*`） |
| `public/_redirects` | `/api/v1/memes` → `/memes.json`；`/memes{,/}` → `/` |
| `scripts/generate-manifest.mjs` | 清单生成策略、最大文件格式（`.webp/.gif`）、输出目录 |

如果想换 CDN 域名，可以在前端 JS 里给 `memes.json` 加 `baseUrl` 字段（详见脚本注释）。

## 📝 更新日志

见 [CHANGELOG.md](./CHANGELOG.md)。

## 📄 许可证

本仓库**双重许可**，请分别阅读：

| 内容 | 协议 | 链接 |
| --- | --- | --- |
| **代码**（HTML / JS / Python / Node 脚本、`_headers`、`_redirects` 等） | MIT | [LICENSE](./LICENSE) |
| **表情包素材**（`public/meme/` 下的所有 `.webp` / `.gif` 文件） | CC BY-NC-SA 4.0 | [ASSET_LICENSE.md](./ASSET_LICENSE.md) |

简言之：代码随便用、商用随便；素材**署名 + 非商用 + 相同方式共享**。

## 🙏 致谢

- [Cloudflare Pages](https://pages.cloudflare.com/) 提供静态托管
- [Pillow](https://python-pillow.org/) 提供图片处理能力
- [Cloudflare Pages](https://pages.cloudflare.com/) 提供静态托管
- [Pillow](https://python-pillow.org/) 提供图片处理能力

## 📬 联系

- Issue / PR：<https://github.com/shumengya/meme-api/issues>
- 主页：<https://github.com/shumengya>

---

<div align="center">
<sub>本项目仅作表情包整理与分享；如素材涉及版权或肖像权问题，请提 Issue 或邮件联系，会第一时间处理。</sub>
</div>

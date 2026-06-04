# 投稿指南 🤝

非常欢迎你一起完善这个表情包图库！这份文档说明**怎么提交素材 / 修复 / 功能**才能又快又稳被合入。

> 阅读前请先看一眼 [README](./README.md) 和 [ASSET_LICENSE](./ASSET_LICENSE.md)，了解项目结构与协议。

## 目录

- [我能贡献什么？](#-我能贡献什么)
- [我该 fork 哪个分支？](#-我该-fork-哪个分支)
- [提 Issue](#-提-issue)
- [素材投稿流程](#-素材投稿流程)
- [代码 / 文档投稿](#-代码--文档投稿)
- [约定与规范](#-约定与规范)
- [本地自检](#-本地自检)
- [PR 流程](#-pr-流程)
- [审核标准](#-审核标准)
- [行为准则](#-行为准则)

## 🎁 我能贡献什么？

| 类型 | 说明 |
| --- | --- |
| 🖼 新表情 / 新分类 | 投到 `public/meme/<新分类>/` 下 |
| 🐛 修坏图 / 错图 | 替换、删除或重新分类 |
| 🌐 图库前端改进 | 修改 `public/index.html`（单文件，无构建） |
| ⚙️ 构建脚本改进 | 改 `scripts/generate-manifest.mjs` 或 `转化.py` |
| 📝 文档 | 改进 `README.md`、本文件、API 说明页 |
| 🧪 Bug 报告 / 体验建议 | 提 Issue |

## 🌿 我该 fork 哪个分支？

**默认 `main` 分支。** 任何 PR 都基于 `main`。

预览分支 `preview` 是 wrangler 部署的临时产物，**不要**直接 PR 到那里。

## 🐞 提 Issue

- **Bug 报告**：用 [Bug 报告模板](.github/ISSUE_TEMPLATE/bug_report.md)，按字段填好
- **新功能 / 改进建议**：用 [功能建议模板](.github/ISSUE_TEMPLATE/feature_request.md)
- **侵权 / 删除请求**：标题加 `[takedown]`，并附素材路径和说明

## 🖼 素材投稿流程

### 0. 先确认你有分发权

只投**以下任一**的素材：

- ✅ 你自己原创 / 自己画的表情包
- ✅ 协议允许二次分发的素材（如 CC BY、CC BY-SA、公共领域）
- ✅ 你已经获得作者明确授权

**别投**：商用素材、明显盗图、官方美术资源（除非协议明确允许）。

### 1. 处理素材（推荐）

> `转化.py` 会帮你自动编号、缩放、转格式；**不要**手动起 `1.webp` 这样的名字，编号是脚本加的。

```bash
# 拿一个新分类举例
mkdir -p 原图/我的新分类
cp ~/Downloads/表情.png 原图/我的新分类/

# 装 Pillow（一次性）
python -m pip install pillow

# 转换：自动编号、统一 webp/gif、最长边缩放到 250px
python 转化.py

# 把生成结果拷入发布目录
cp -r 原图-已处理/我的新分类 public/meme/
```

参数说明：

| 参数 | 作用 |
| --- | --- |
| `--delete-sources` | 处理完删除 `原图/` 里的源文件（默认保留） |
| `--max-side 250` | 最长边像素，默认 250px |
| `--jobs 10` | 并行线程数 |

### 2. 直接投到 `public/meme/`

如果你的素材**已经**是 `N.webp` / `N.gif` 命名，且最长边 ≤ 250px，可以**直接**放到 `public/meme/<分类>/`，不跑 `转化.py`。脚本在生成清单时会自动识别已编号的素材。

### 3. 重新生成清单

```bash
npm run build
```

这一步会重写 `public/memes.json` 与 `dist/memes.json`，**请把这两个文件一起 commit**。

### 4. 提交 PR

- **PR 标题**：`feat(meme): 新增 xxx 分类` 或 `fix(meme): 删除损坏的 白色小人/123.webp`
- **PR 描述**：
  - 素材来源（自己画 / 转载自 xxx / 协议 xxxx）
  - 大致数量和分类
  - 截图（可选）

## 💻 代码 / 文档投稿

### 前端

- `public/index.html` 是**单文件**前端（HTML + 内联 CSS + 内联 JS，**无任何依赖**）
- 改完**直接刷新本地预览**就能看效果：
  ```bash
  npm run dev
  # 浏览器打开 http://localhost:8788
  ```
- 尽量保持：
  - 移动端优先 → 桌面端
  - 暗色模式自适应
  - 键盘可达（`Tab`、`Enter`、`Esc`）
  - 不引入外部依赖

### 构建脚本

- `scripts/generate-manifest.mjs` — Node 18+ ESM
- `转化.py` — Python 3.8+，只依赖 Pillow
- 改完跑 `npm run build` 验证 `memes.json` 生成正确

### 文档

- 写完后检查一下渲染效果：本地打开 `README.md` 看看排版
- 文档用 **中文**；变量名、函数名、commit 标题用**英文**
- 引用外部链接优先官方文档

## 📐 约定与规范

### Commit 消息

遵循 [Conventional Commits](https://www.conventionalcommits.org/)：

```
feat(meme): 新增 黄仁勋 分类
fix(meme): 替换损坏的 滑稽/3.webp
docs: 完善 README 的 API 文档
style(frontend): 调整移动端栅格断点
refactor(scripts): 拆分 generate-manifest.mjs
chore: 升级 wrangler 到 4.7
```

允许类型：`feat` / `fix` / `docs` / `style` / `refactor` / `perf` / `test` / `chore` / `ci`

### 分支名

- `feat/<短描述>`：新功能 / 新分类
- `fix/<短描述>`：修 bug
- `docs/<短描述>`：文档
- `chore/<短描述>`：杂项

例：`feat/meme-add-minecraft-pack`、`fix/meme-broken-gifs`

### 分类目录命名

- 用**清晰的中文**，避免过长的字串
- 不要带空格（用空格的话在 URL 里得编码，体验差）
- 不要带特殊符号 `/`、`\`、`#`、`?`
- 想拆同主题的子分类就再加一个目录，例如 `抹茶旦旦2`

### 素材命名

- **不要**自己命名；让 `转化.py` 续号
- 已经手动起好的也 OK（`1.webp` / `2.gif` 这种），脚本会从已有最大编号续起

### 文件格式

- 静态图：`.webp`（默认 lossless，质量 + 体积兼顾）
- 动图：`.gif`（Pillow 转码；WebP 动图也会被转成 GIF 提升兼容性）
- 缩放：最长边 **250px**
- 单张建议 ≤ **30KB**；动图 ≤ **100KB**

## ✅ 本地自检

提交前请跑一遍：

```bash
# 1. 构建通过、清单生成正常
npm run build

# 2. 本地预览，检查图库显示、复制/下载、侧边栏等
npm run dev

# 3. （可选）检查素材大小
du -sh public/meme/<新分类>/
ls -la public/meme/<新分类>/ | head
```

确认：

- [ ] 新分类在侧边栏出现，编号连续无跳号
- [ ] 点开任意一张能正常复制 URL / Markdown / HTML / 下载
- [ ] 移动端（DevTools 切到 375px）布局没崩
- [ ] 没有把 `dist/`、`node_modules/`、`__pycache__/`、`*.pyc` 等 commit 进去

## 🔁 PR 流程

1. Fork → 新分支 → 改代码 / 投素材
2. `npm run build` 自检
3. 提 PR 到 `main`
4. 描述清楚改了什么；附截图（如有 UI 变化）
5. 等 CI / 维护者 review
6. 必要的话按 review 改一轮
7. 合并后 Cloudflare Pages 会自动部署

## 🧐 审核标准

PR 被合的优先级：

- ✅ 修复真实 bug
- ✅ 引入来源清晰的新素材
- ✅ 改进图库体验（无障碍 / 性能 / 暗色）
- ✅ 改进文档可读性
- ⚠️ 大批量素材（> 200 张）建议先开 Issue 沟通
- ❌ 协议不清晰的素材
- ❌ 引入外部依赖（CDN 库、构建工具）的"重"改动
- ❌ 与项目无关的"小改"（拼写错误除外）

## 🫶 行为准则

- 友善、尊重、就事论事
- 拒绝任何形式的骚扰、歧视、人身攻击
- 提 Issue / 评论前先搜一下避免重复
- 不确定时先问，错了就改

违反行为准则的评论 / PR 会被关闭，屡次违反会被封禁。

---

有任何问题，欢迎在 [Issue](https://github.com/shumengya/meme-api/issues) 里沟通。谢谢你的贡献！🌱

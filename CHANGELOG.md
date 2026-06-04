# 更新日志

本项目的所有**重要变更**都会记录在此文件。

格式基于 [Keep a Changelog](https://keepachangelog.com/zh-CN/1.1.0/)，
版本号遵循 [Semantic Versioning](https://semver.org/lang/zh-CN/)。

> 表情包素材的新增 / 删除 **不**计入版本号，详情看 Git 提交历史。

## [Unreleased]

### 计划中
- 给图库前端加 lightbox 预览（点击放大、左右切换）
- 在图库首页显示每个分类的封面图
- 素材缩放阈值参数化（支持多档位 CDN 输出）

## [1.0.0] - 2026-06-04

### 新增
- 仓库首次**公开**整理：补齐 README、LICENSE、CONTRIBUTING、CHANGELOG、Issue / PR 模板
- 双协议声明：代码 MIT，表情包素材 CC BY-NC-SA 4.0
- 收录 **51 个分类、~2600+ 张**表情包（WebP / GIF）
- 图库前端（`public/index.html`）：分类侧边栏 + 搜索 + 移动端 4 列 / 桌面 12 列网格
- 一键复制 URL / Markdown / HTML（HTML 宽度 96–400px 可记忆）
- 一键下载原图
- 在线 API 说明页：`https://meme.smyhub.com/readme/`
- JSON 公开 API：`/memes.json`（兼容 `/api/v1/memes`），已配置 CORS
- Python 一键处理脚本 `转化.py`（Pillow，多线程、动图 WebP→GIF、zip 批处理）
- Node 构建脚本 `scripts/generate-manifest.mjs`（仅生成清单，素材不重处理）
- Cloudflare Pages 部署支持：Git 集成 + wrangler CLI 双通道

### 安全 / 性能
- 静态站点，**无服务端**，无任何用户数据收集
- 所有外链静态资源（fonts、analytics 等）**未引入**
- CORS 头只对 `memes.json` 与 `/api/v1/memes` 开启，不影响其他资源

## 历史

在 1.0.0 之前，仓库作为个人项目维护，无版本号 / 变更日志。

[Unreleased]: https://github.com/shumengya/meme-api/compare/main...HEAD
[1.0.0]: https://github.com/shumengya/meme-api/releases/tag/v1.0.0

---

<div align="center">
<sub>本文件由维护者手工维护，欢迎在 PR 中追加。</sub>
</div>

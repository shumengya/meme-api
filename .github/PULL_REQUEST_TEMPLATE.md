## 描述

<!-- 一两句话说清这个 PR 干了什么。 -->

## 关联 Issue

<!-- 用 `Closes #123` / `Fixes #123` 关联 issue；没关联的写 "无"。 -->

Closes #

## 变更类型

请打勾：

- [ ] 🐛 Bug 修复（fix）
- [ ] ✨ 新功能（feat）
- [ ] 🎨 样式 / UI 调整（style）
- [ ] ♻️ 重构（refactor）
- [ ] ⚡ 性能优化（perf）
- [ ] 📝 文档（docs）
- [ ] 🔧 构建 / 脚本 / 配置（chore）

## 改动内容

<!-- 详细列出做了哪些改动。可以按文件 / 模块分点。 -->

- 
- 
- 

## 涉及的文件

<!-- 方便 reviewer 快速定位 -->

- [ ] `public/index.html`
- [ ] `scripts/generate-manifest.mjs`
- [ ] `转化.py`
- [ ] `public/memes.json`（清单，由 `npm run build` 自动重生成）
- [ ] `dist/memes.json`（构建产物，请确认未手动修改）
- [ ] 文档（README / CHANGELOG / 其他）
- [ ] GitHub 配置（Issue 模板 / PR 模板 / .github 目录）

## 自检清单

- [ ] 本地 `npm run build` 通过，`public/memes.json` 已重生成
- [ ] 本地 `npm run dev` 跑过，浏览器实测没回归
- [ ] 移动端（DevTools 切到 375px）布局没崩
- [ ] 改动不引入新外部依赖
- [ ] 没有把 `dist/`、`node_modules/`、`__pycache__/`、`*.pyc`、`原图/` 里的源文件等 commit 进去
- [ ] 我已更新 [CHANGELOG.md](./CHANGELOG.md)（如适用）

## 截图 / 录屏

<!-- 如有 UI 改动请附图。 -->

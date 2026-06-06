# [萌芽妙妙工具] 萌芽表情包图库 —— 一个纯静态的表情包 API + 图库

> 项目地址：[github.com/shumengya/meme-api](https://github.com/shumengya/meme-api)  
> 在线体验：[meme.smyhub.com](https://meme.smyhub.com)  
> 协议：MIT协议

---

## 这是做什么的

平时在群里聊天、写博客、做项目文档的时候，经常需要找表情包。网上搜到的图要么带水印，要么链接失效，要么格式不统一，用起来很不顺手。

所以我整理了一个表情包图库，做成纯静态站点部署在 Cloudflare Pages 上。打开网页就能翻、能搜、能一键复制链接，也对外提供 JSON API，方便在任何地方调用。

目前一共收录了 **51 个分类、2600 多张** WebP / GIF 表情包，全部经过统一处理（最长边缩放到 250px，动图统一为 GIF），体积和兼容性都控制得比较好。

---

## 打开网页就能用

图库本身是一个单文件 HTML 页面（`public/index.html`），没有任何前端框架、没有任何外部依赖，打开就是下面这样：

- 左侧分类侧边栏，支持搜索过滤
- 手机端自动变成 4 列网格，电脑端最多 12 列
- 点击任意表情弹出操作面板，可以：
  - 复制直链 URL
  - 复制 Markdown 格式
  - 复制 HTML 嵌入代码（宽度 96~400px 可选，会记住你的偏好）
  - 直接下载原图

整个页面加载完之后所有交互都是本地的，不需要后端服务。

---

## 也能当 API 用

如果你不想打开网页，直接用接口拉数据也可以：

```bash
curl -sS "https://meme.smyhub.com/memes.json"
```

返回结构大概长这样：

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

拿到清单之后，拼接一下就是直链：

```
https://meme.smyhub.com/meme/白色小人/1.webp
```

中文路径记得 URL 编码，图库里的「复制链接」按钮已经帮你编好了。

接口还做了 CORS，任何网页、博客、脚本、聊天机器人都可以直接跨域调用。

---

## 引用单张表情

在 Markdown 或 HTML 里直接贴：

```markdown
![哈哈](https://meme.smyhub.com/meme/%E7%99%BD%E8%89%B2%E5%B0%8F%E4%BA%BA/1.webp)
```

```html
<img src="https://meme.smyhub.com/meme/%E7%99%BD%E8%89%B2%E5%B0%8F%E4%BA%BA/1.webp"
     alt="哈哈" loading="lazy" width="240"
     style="max-width:240px;width:100%;height:auto" />
```

因为托管在 Cloudflare Pages，全球边缘节点都有缓存，国内访问速度也还可以。

---

## 技术结构

整个项目非常轻，没有复杂架构：

```
meme-api/
├── public/
│   ├── index.html          ← 图库前端（单文件，零依赖）
│   ├── meme/               ← 处理后的表情包素材
│   ├── memes.json          ← 自动生成的清单
│   ├── _headers            ← CORS 响应头配置
│   ├── _redirects          ← 旧接口兼容
│   └── readme/index.html   ← API 说明页
├── scripts/
│   └── generate-manifest.mjs  ← 生成 memes.json + 复制到 dist/
├── 原图/                    ← 原始素材
├── 转化.py                  ← Python 一键处理脚本
└── package.json
```

### 纯静态，没有后端

所有内容都是静态文件。分类列表、搜索、复制、下载，全部在前端用原生 JS 完成。部署只需要把 `dist/` 丢到任意静态托管就行（Cloudflare Pages、Vercel、GitHub Pages、对象存储都可以）。

### 零依赖前端

`index.html` 是一个完整的单页面应用，内联了所有 CSS 和 JavaScript，没有引用任何外部 CDN。这意味着：

- 内网环境、离线环境也能打开
- 不用担心 CDN 挂掉导致页面崩
- 审计和安全层面很干净

### Python 处理脚本

新素材丢进 `原图/<分类>/`，运行：

```bash
python 转化.py
```

会自动完成：

- 未编号素材自动续号
- 统一转成 WebP（静态）或 GIF（动图）
- 最长边缩放到 250px
- 多线程并行处理

处理完的东西会输出到 `原图-已处理/`，再手动拷进 `public/meme/` 就可以上线。

---

## 协议说明

这个仓库用了**双重许可**，代码和素材分开：

| 内容 | 协议 |
|------|------|
| 代码（HTML / JS / Python / Node / 配置） | MIT，随便用，商用也行 |
| 表情包素材（`public/meme/` 下的所有图片） | CC BY-NC-SA 4.0，署名 + 非商用 + 相同方式共享 |

---

## 部署方式

### 方式一：连接 Git（推荐）

在 Cloudflare Pages 创建项目，连接 GitHub 仓库的 `main` 分支：

- 构建命令：`npm run build`
- 构建输出目录：`dist`

每次 push 会自动触发部署。

### 方式二：CLI 直传

```bash
npm install
npm run build
npx wrangler pages deploy dist
```

---

## 总结

这个项目本质上就是一个**整理好的表情包文件夹 + 一个能用的前端 + 一个能读的 JSON 接口**。没有花里胡哨的功能，但刚好解决了"找表情、发链接、统一管理"这几个常见痛点。

如果你平时也需要大量表情包，或者想给自己的项目搭一个简单的素材 API，可以试着部署一下这个项目。表情包内容会不定期整理更新。

---

**相关链接**

- 🌐 在线图库：[meme.smyhub.com](https://meme.smyhub.com)
- 📦 GitHub 仓库：[github.com/shumengya/meme-api](https://github.com/shumengya/meme-api)
- 📖 API 文档：[meme.smyhub.com/readme/](https://meme.smyhub.com/readme/)

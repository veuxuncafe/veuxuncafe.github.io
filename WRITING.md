# 日常操作手册

本站是 Jekyll + GitHub Pages（用户站点），地址 `https://veuxuncafe.github.io/`。

---

## 一、发一篇文章

### 1. 新建文件

放到 **`_posts/`** 目录下，文件名必须是 **`YYYY-MM-DD-英文短名.md`**：

```
_posts/2026-09-20-my-new-post.md
```

- 文件名里的日期就是这个文章的发布日期
- 短名会成为网址：上面的文件对应 `https://veuxuncafe.github.io/posts/my-new-post/`
- 网址格式由 `_config.yml` 的 `permalink: /posts/:title/` 决定

### 2. 内容格式

```markdown
---
layout: post
title: 文章标题
date: 2026-09-20
categories: 技术
description: 一句话摘要，会显示在首页文章列表里。
---

正文用 Markdown 写，随便写。

## 二级标题

- 列表
- 都可以
```

**两个字段要注意：**

| 字段 | 说明 |
|---|---|
| `categories` | **只能是 `技术` 或 `随笔`**。首页的筛选按钮就是「全部 / 技术 / 随笔」，列表按第一个分类归组；不写默认归为「随笔」 |
| `description` | 显示在首页列表的摘要。不写就自动截取正文前 90 字 |

### 3. 发布

```bash
cd "E:\pilot projects\WOLyosemite.github.io"
git add .
git commit -m "post: 文章标题"
git push
```

推上去后 **1–2 分钟**自动出现在首页文章列表里——**不需要手动在首页加链接**（首页用 `{% for post in site.posts %}` 自动列出）。

也可以在 GitHub 网页上直接 New file 创建，效果一样。

> **本机 push 说明**：仓库已配置 SSH remote + 部署密钥（`core.sshCommand` 指向 `E:\pilot projects\.keys\woly_deploy`），所以在上面这个目录里 `git push` **不需要输密码**。
> 但如果你要在**别的仓库**用 HTTPS 推，需要先跑一次：`git config --global http.sslBackend openssl`（本机 SChannel 后端有问题）。

### 4. 写数学公式

全站已经装了 MathJax（在 `_layouts/default.html` 里加载），文章里直接写 LaTeX 就会渲染。

**但定界符必须用 `$$`，行内公式也是 `$$`。** 这是 kramdown 的规定：它**只认双美元号**，而且行内和行间共用同一个符号——写成单美元号的 `$x$` 完全不会被识别，会原样显示出来，里面的 `_`、`*` 还会交回 Markdown 处理（有被当成强调符号的风险）。

```
行内：设 $$\beta>0$$ 为正则强度。

行间：两个 $$ 各自单独占一行，前后各留一个空行
$$
\mathcal{L} = \mathbb{E}\left[\log\sigma(\beta\Delta)\right]
$$
```

几个要点：

| 事项 | 说明 |
|---|---|
| 行内定界符 | `$$ ... $$`（**不是** `$ ... $`） |
| 行间定界符 | 开头 `$$` 单独占一行，内容另起行，收尾 `$$` 也单独占一行；前后各留空行 |
| 公式内容 | 会被原样送给 MathJax，**不经过 Markdown 处理**——所以 `_`、`*`、`\` 都不会被吃成斜体 |
| 公式编号 | 用 `\tag{7}`，渲染成右对齐的 (7)。**没有 `\tag` 的行间公式不会被自动编号**，所以编号完全由你控制 |
| `\text{}` 里别放中文 | MathJax 的 `\text{}` 用数学字体（MJXTEX），不含中文字形，中文会掉到浏览器默认字体上。标签写英文（`\text{weight}`），中文解释放正文 |
| 多行对齐 | 用 `\begin{aligned} ... \end{aligned}`，换行写 `\\`，对齐点写 `&` |

> **本机没法预览公式。** 文章的渲染由云端 GitHub Pages 完成，本地没有 Ruby/Jekyll。要检查公式写对没有，只能推上去之后刷新页面看。改公式时建议少量多次提交，出问题容易定位。

---

## 二、更新研究页

研究页在 `https://veuxuncafe.github.io/research/`，**只需要改一个文件**：

```
research/data/findings.json      ← 唯一真值
```

里面每个字段的含义：

| 字段 | 内容 |
|---|---|
| `meta.project` / `english` | 标题与英文副题 |
| `meta.data_freeze` | 数据冻结日（页面会显示"已 N 天"） |
| `meta.status` | 研究状态一句话 |
| `meta.integrity` | 「验证门」表格，键值对 |
| `question` | 研究问题 |
| `thesis` | 核心论点 |
| `layers` | 三层分解表（通道 / 实例 / 竞争） |
| `p01` / `p02` | 两部分结果：rates、contingency、tautology、q1、q2 等 |
| `related_work` | 与最接近工作的划界表 |
| `limitations` | 限制与披露列表 |

**改完后有两种生效方式：**

- **等自动**：云端 GitHub Actions 每天 09:17、本地计划任务每天 09:40（时间戳是日期粒度，谁先跑谁提交，一天最多一次提交）
- **立刻生效**：
  ```bash
  cd "E:\pilot projects\WOLyosemite.github.io"
  python research/generate_progress.py     # 重新生成 research/index.html
  git add . && git commit -m "research: 更新数据" && git push
  ```

> ⚠️ **绝对不要手改 `research/index.html`** —— 它是生成产物，下次生成会被覆盖。要改内容只改 `findings.json`。

> 想加一整个新章节（比如第三部分结果），那要改生成器 `research/generate_progress.py` 里 `build()` 的模板，我可以代劳。

---

## 三、本地预览

```bash
cd "E:\pilot projects\WOLyosemite.github.io"
python -m http.server 8000
```

然后打开 `http://localhost:8000/`。

> 直接双击 `research/index.html` **看不到网站的导航和样式**——因为它是 Jekyll 内容页，布局由 `_layouts/default.html` 渲染，必须先经 Jekyll 构建。所以要用上面的起服务方式。

---

## 四、目录结构速查

| 路径 | 作用 | 要手动改吗 |
|---|---|---|
| `_posts/*.md` | **文章** | ✅ 新增文章 |
| `_layouts/default.html` | 全站布局（header / 导航 / footer）+ **MathJax 加载** | 改导航时 |
| `_layouts/post.html` | 文章页布局 | 很少 |
| `index.html` | 首页（hero + 文章列表 + 引言） | 改首页文案时 |
| `about.html` | 关于页 | 改自我介绍时 |
| `styles.css` | 全部样式（含公式横向滚动 / 编号颜色） | 调外观时 |
| `script.js` | 深浅色切换 + 首页分类筛选 | 很少 |
| `_config.yml` | 站点配置（标题、作者、网址、baseurl） | 很少，**改 `baseurl` 会让全站资源 404，别乱动** |
| `research/data/findings.json` | **研究数据** | ✅ 更新研究 |
| `research/generate_progress.py` | 研究页生成器（零依赖） | 加新章节时 |
| `research/index.html` | 研究页产物 | ❌ **不要手改** |
| `math/data/library.py` | **数学资源库内容源** | ✅ 增删条目 |
| `math/generate_math.py` | 数学资源库生成器（零依赖） | 改版式时 |
| `math/index.html` | 数学资源库产物 | ❌ **不要手改** |
| `.github/workflows/daily-research-update.yml` | 云端每日自动更新 | 一般不动 |

---

## 五、历史遗留问题（已清理）

以下问题在 2026-09-15 已修复：

1. **根目录 3 个 `.md` 不是文章** —— 它们写着 `layout: post` 却不在 `_posts/` 里，因此不会被首页列出，而是各自发布成 `/2026-08-12-slowly.html` 这样的独立页面。
   → 已 `git mv` 进 `_posts/`，现在是正常文章：`/posts/slowly/`、`/posts/github-pages/`、`/posts/hello-world/`

2. **`github-pages.html` 重复且样式不一致** —— 它是 `2026-08-18-github-pages.md` 的手写 HTML 版本（同标题、同日期、同正文），自己写了 `<head>` 和内联导航，不走 Jekyll 布局，且全仓库无人链接它。
   → 已删除，保留 Markdown 版本作为正式文章。

3. **`README.md` 的写作说明过时** —— 原文说"复制 `posts/hello-world.html`，再在 `index.html` 列表里加链接"，但 `posts/` 目录不存在，且文章现在由 Jekyll 自动列出。
   → README 已重写，写作说明统一指向本手册。

4. **首页被存根文件占用** —— `index.html` 与 `index.md` 抢同一根路径，Jekyll 选中了 `index.md`（内容是"欢迎来到我的博客"的占位稿，还引用了不存在的 `layout: home`），导致 hero、文章列表、引言区都没渲染。
   → 已删除 `index.md`。


---

## 六、两条自动更新通道

| 通道 | 时间 | 依赖 | 备注 |
|---|---|---|---|
| GitHub Actions | 每天 09:17（北京时间） | 不需要你的电脑 | 需要仓库 Settings → Actions → General → Workflow permissions 设为 **Read and write** |
| Windows 计划任务 | 每天 09:40，错过会补跑 | 电脑开机且已登录 | 任务名 `WOLyosemite Research Daily Update`；日志在 `E:\pilot projects\logs\daily-research-update.log` |

两者不会冲突：页面时间戳精确到**日期**，谁先跑谁提交，另一个发现无变化就不提交。

GitHub 会在仓库 60 天无活动后禁用定时工作流；机器人的提交本身算活动，万一停摆，去 Actions 页面点一次 **Run workflow** 即可唤醒。

---

## 七、内容计划

想写但还没写的选题记在这里，下次发新文章时从这里挑。

**当前待写：暂无。**

### 已发布

- **sigmoid / softmax / softplus** —— 2026-09-29 发布，见 `_posts/2026-09-29-sigmoid-softmax-softplus.md`
  - 原计划只写 sigmoid 和 softmax 两个，发布时按要求加上了 softplus，三者合成一篇
  - 立意：以 **logsumexp** 作为共同的根串起三者——softmax 是它的梯度，softplus 是它补一个 0 之后的一元版本，sigmoid 是 softmax 在 K = 2 时的特例、同时又是 softplus 的导数
  - 明确不写：logits 不单独展开，只在需要处一句带过
  - 与 DPO 那篇互相链接（DPO 里公式 (8) 是 softmax、(12)–(14) 是 sigmoid、损失可直接写成 softplus）

> 记录这条的背景：2026-09-27 讨论 DPO 推导时被问到 logits / sigmoid / softmax，当时口头讲清了，约定之后落成文章。

---

## 八、维护数学资源库

地址 `https://veuxuncafe.github.io/math/`，导航里叫「数学」。用途：把做研究时反复要查的概念、符号、公式集中放一处，随时查。

### 改内容：只改一个文件

```
math/data/library.py      ← 唯一真值
```

每个条目是一个 dict，字段含义：

| 字段 | 内容 |
|---|---|
| `id` | 锚点短名，**全库唯一**，英文小写（`related` 靠它做链接） |
| `term` / `en` | 中文术语 / 英文原词（英文名便于按论文里的说法检索） |
| `topic` | 主题 id，必须是 `TOPICS` 里定义的那几个之一 |
| `symbols` | `[(符号, 说明), ...]`，这是「查符号」的关键 |
| `formula` | 展示公式，LaTeX |
| `plain` | 一句话直观解释 |
| `pitfalls` | 常见误解与坑（列表） |
| `where` | 在你的研究/工作里的位置 |
| `related` | 相关条目的 `id` 列表 |

**文本字段支持两个行内标记**：`**粗体**` 和 `` `代码` ``。别的 Markdown 语法不会生效（页面是 `.html`，不经过 kramdown）。

**公式写法**：行内用 `\( ... \)`，行间用 `\[ ... \]`。注意这是**页面级**的写法，和文章里 `$$` 那套不同——因为文章走 kramdown、这个页面不走。

**LaTeX 一律用 raw 字符串**（`r"..."`）。普通字符串里 `\n`、`\t`、`\b` 会被 Python 当成转义符，静默毁掉公式。

### 改完生成

```bash
cd "E:\pilot projects\WOLyosemite.github.io"
python math/generate_math.py        # 重新生成 math/index.html
git add . && git commit -m "math: 更新资源库" && git push
```

生成器带四道自检，任一条不通过就**拒绝写盘**（不会上线坏页面）：

1. `id` 唯一、`related` 指向存在的条目、主题合法、必填字段齐全
2. 输出里不含 Liquid 定界符（`{{` / `{%`）
3. 公式定界符配对
4. 原始字符串里没有危险的 LaTeX 转义

> ⚠️ **不要手改 `math/index.html`** —— 它是生成产物，下次生成会被覆盖。要改内容只改 `library.py`；要改版式改 `generate_math.py` 里的 `STYLE` / `SCRIPT`。

### 本地预览

和别处一样，双击打开看不到导航和样式（它是 Jekyll 内容页，要经布局渲染）：

```bash
cd "E:\pilot projects\WOLyosemite.github.io"
python -m http.server 8000
```

### 已收录的 30 条

按主题分：概率与信息论 9 · 优化与凸性 8 · 微积分与自动微分 5 · 数值与精度 2 · 偏好优化 6。

条目来源是 2026-09-27 至 09-29 讨论 DPO 推导与数学基础时被问到的问题，所以 `where` 字段大多指向偏好优化的工作。以后有新的疑问，直接加条目即可——这个库的定位就是「问过什么就沉淀什么」。

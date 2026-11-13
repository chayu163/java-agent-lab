# tools/ — 构建与站点

`docs/` 是学习路径站点的源码，本目录负责把仓库里的笔记和代码加工成它能读的内容。
站点已上线：<https://chayu163.github.io/java-agent-lab/>

## 内容从哪来

不给站点单独维护内容。构建脚本扫描仓库本身：

| 站点区块 | 来源 |
|---|---|
| 笔记 | `notes/dayNN/*.md` |
| 代码 | `dayNN/python/*.py`、`dayNN/java/*.java` |
| 调研 | `research/**/*.md` |

日常只需要正常写笔记和代码，推上去由 CI 重建，站点自动跟上。

## 构建与预览

```bash
uv run --group docs python tools/build_site.py
```

```bash
uv run python -m http.server 8765 --directory docs
```

然后打开 <http://localhost:8765>。改了 `notes/` 或代码后要重跑构建脚本，页面才有新内容。

`docs/content/` 是生成物，已 gitignore。

## markdown 渲染

`build_site.py` 里自己实现的 Obsidian 兼容层，覆盖笔记里实际用到的语法：

- frontmatter（`title` / `date` / `tags` / `status`）→ 拆出来喂给抽屉的元信息
- callout：`> [!note]` / `[!tip]` / `[!warning]` / `[!danger]` / `[!important]` / `[!abstract]`
- wikilink：`[[目标]]`、`[[目标|别名]]`，能对上标题就渲染成页内锚点，对不上显示为未解析
- 任务列表：`- [x]` / `- [ ]`
- 表格、代码围栏、行内代码

代码高亮是自写的正则分词器（Python / Java），不引第三方库。

## 站点结构

```text
docs/
├── index.html            单页应用：路线图 + 节点抽屉
├── assets/style.css      设计系统（深/浅主题、分带强调色）
├── assets/app.js         交互层
├── assets/roadmap-data.js  路线图节点、分带、每日计划（手写内容）
└── content/              构建产物，gitignore
```

- **路线图**：4 带 10 节点的纵向路径（底座 → Agent 工程 → 检索与评测 → 作品与投递），
  结构照搬 `research/2026-11-12/学习路径图-original.html`。
- **节点抽屉**：点节点打开，三个页签——概览（计划与产出）、笔记、代码。
- **调研与计划**：右上角按钮，渲染 `research/` 下全部 markdown。

改路线图的节点或每日计划，要同步改 `docs/assets/roadmap-data.js`。

## 部署

`.github/workflows/pages.yml`：push 到 `main` 时构建 `docs/content/` 并发布。
仓库 Settings → Pages → Source 必须是 **GitHub Actions**（不是 Deploy from a branch）。

# java-agent-lab

Java 开发者补齐 Python + Agent 技术栈的 30 天学习仓库。路线基于 2026-11 BOSS 直聘杭州/上海「AI 应用 / Agent 开发」岗位数据搭建：Python + MySQL 是筛选线，LangGraph / MCP / RAG(pgvector) / agent 评测是拉开薪资的部分。

执行区间 2026-11-13 ~ 2026-12-12，每天 6-8 小时，每天一个可运行产出，目标岗位 15-30K。

**学习路径站点**：<https://chayu163.github.io/java-agent-lab/>

## 阶段

| 阶段 | 天数 | 内容 |
|---|---|---|
| 1 | Day 1-5 | Python 定向迁跃（只补 Java→Python 差异） |
| 2 | Day 6-8 | LLM 应用基础（function calling / RAG / 评测） |
| 3 | Day 9-13 | OpenManus 深读（agent harness） |
| 4 | Day 14-20 | MaxKB 深读（企业平台 + pgvector RAG） |
| 5 | Day 21-30 | 复刻垂直版（LangGraph + pgvector + MCP + deepeval） |

计划原文与岗位调研：[research/2026-11-12/](research/2026-11-12/)。当前进度只记在 [AGENTS.md](AGENTS.md)，站点路线图按天显示已产出的内容——README 不重复维护进度。

## 目录

```text
curriculum.json   # 站点每日任务、产出与节点关联的唯一数据源

phaseN/
└── dayNN/
    ├── README.md   # 当天知识树（从 day03 起）
    ├── java/       # 对照阅读用的 Java 原版
    └── python/     # Python 练习与当天产出

notes/
└── phaseN/
    └── dayNN/
        ├── *.md      # 当天笔记（Obsidian 可直接打开）
        └── assets/   # 笔记引用的交互图，构建时随笔记一起发布

research/
└── YYYY-MM-DD/   # 调研、计划、路线图，按日期归档，重做不覆盖旧结论

tools/
└── build_site.py # 站点内容构建

docs/             # GitHub Pages 站点源码；content/ 是生成物，不入库
```

`dayNN` 编号在仓库内全局唯一；阶段 5 结束时会得到 `phase1/` 到 `phase5/` 五个目录。

根目录是唯一的 uv 项目，30 天共享一个 `.venv`；依赖统一在 `pyproject.toml` 声明。

站点路线图的每日任务、产出和节点关联维护在 `curriculum.json`；完成状态由当天笔记 frontmatter 的 `status: done` 生成。

## 常用命令

```bash
uv sync --group docs              # 首次，或改了依赖之后
uv run phase1/day03/python/05_fetch.py   # 跑当天脚本
uv run pytest -q                  # 跑全部测试，从仓库根收集
```

质量门，与 CI 完全一致：

```bash
uv run ruff check . && uv run ruff format --check .
uv run --group docs mypy .
uv run --group docs python tools/build_site.py
```

本地预览站点：

```bash
uv run python -m http.server 8765 --directory docs
```

该机器的 Python 与 uv 由 mise 管理，非交互终端里需写成 `mise exec -- uv ...`。

## 约定

- 每天一个目录，必须留下可运行产出，不接受"只看不写"。
- 笔记写在 `notes/dayNN/`，按"5 分钟能讲清楚"验收。
- `~/repos` 下的第三方仓库（boss-agent-cli、OpenManus、MaxKB）是学习材料，不算自有项目。
- 站点内容不单独维护：笔记取自 `notes/`，代码取自 `dayNN/`，调研取自 `research/`，推送后由 CI 重建。

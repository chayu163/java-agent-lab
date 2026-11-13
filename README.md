# java-agent-lab

Java 开发者补齐 Python + Agent 技术栈的 30 天学习仓库。路线基于 2026-11 BOSS 直聘杭州/上海「AI 应用 / Agent 开发」岗位数据搭建：Python + MySQL 是筛选线，LangGraph / MCP / RAG(pgvector) / agent 评测是拉开薪资的部分。

执行区间 2026-11-13 ~ 2026-12-12，每天 6-8 小时，每天一个可运行产出，目标岗位 15-30K。

**学习路径站点**：<https://chayu163.github.io/java-agent-lab/>

## 阶段

| 阶段 | 天数 | 内容 | 状态 |
|---|---|---|---|
| 1 | Day 1-5 | Python 定向迁跃（只补 Java→Python 差异） | 进行中 |
| 2 | Day 6-8 | LLM 应用基础（function calling / RAG / 评测） | 未开始 |
| 3 | Day 9-13 | OpenManus 深读（agent harness） | 未开始 |
| 4 | Day 14-20 | MaxKB 深读（企业平台 + pgvector RAG） | 未开始 |
| 5 | Day 21-30 | 复刻垂直版（LangGraph + pgvector + MCP + deepeval） | 未开始 |

计划原文与岗位调研：[research/2026-11-12/](research/2026-11-12/)。

## 目录

```text
dayNN/
├── java/     # 对照阅读用的 Java 原版
└── python/   # Python 练习与当天产出

notes/
└── dayNN/    # 当天笔记（Obsidian 可直接打开）

research/
└── YYYY-MM-DD/   # 调研、计划、路线图，按日期归档

tools/
└── build_site.py # 站点内容构建

docs/           # GitHub Pages 站点，content/ 是生成物
```

根目录是唯一的 uv 项目，30 天共享一个 `.venv`；依赖统一在 `pyproject.toml` 声明。

## 常用命令

```bash
uv sync --group docs
uv add <package>
uv run day01/python/order.py
uv run ruff check day01/python
uv run ruff format day01/python
uv run mypy day01/python
```

重建并预览学习路径站点：

```bash
uv run --group docs python tools/build_site.py
```

```bash
uv run python -m http.server 8765 --directory docs
```

该机器的 Python 与 uv 由 mise 管理，非交互终端里需写成 `mise exec -- uv ...`。

## 约定

- 每天一个目录，必须留下可运行产出，不接受"只看不写"。
- 笔记写在 `notes/dayNN/`，按"5 分钟能讲清楚"验收。
- `~/repos` 下的第三方仓库（boss-agent-cli、OpenManus、MaxKB）是学习材料，不算自有项目。
- 站点内容不单独维护：笔记取自 `notes/`，代码取自 `dayNN/`，调研取自 `research/`，推送后由 CI 重建。

## 进度

- [x] Day 1：环境、Java→Python 差异清单、订单状态机翻译
- [ ] Day 2：装饰器 / 生成器 / with / typing / Pydantic v2
- [ ] Day 3：asyncio
- [ ] Day 4：pytest
- [ ] Day 5：mini agent loop
- [ ] 阶段 2：LLM 应用基础（Day 6-8）
- [ ] 阶段 3：OpenManus 深读（Day 9-13）
- [ ] 阶段 4：MaxKB 深读（Day 14-20）
- [ ] 阶段 5：复刻垂直版（Day 21-30）

# java-agent-lab

Java 开发者补齐 Python + Agent 技术栈的 30 天学习仓库。学习路线基于 2026-11 最新 BOSS 直聘杭州/上海「AI 应用 / Agent 开发」岗位数据搭建：Python + MySQL 是筛选线，LangGraph / MCP / RAG(pgvector) / agent 评测是拉开薪资的部分。

执行区间 2026-11-13 ~ 2026-12-12，每天 6-8 小时，每天一个可运行产出，目标岗位 15-30K。

计划原文与岗位调研在 `boss-agent-cli` 仓库：

- `C:\Users\33170\repos\boss-agent-cli\AI-Agent学习计划-30天-2026-11-12.md`
- `C:\Users\33170\repos\boss-agent-cli\AI岗位调研-杭州上海-2026-11-12.md`

## 阶段

| 阶段 | 天数 | 内容 |
|---|---|---|
| 1 | Day 1-5 | Python 定向迁跃（只补 Java→Python 差异） |
| 2 | Day 6-8 | LLM 应用基础（function calling / RAG / 评测） |
| 3 | Day 9-13 | OpenManus 深读（agent harness） |
| 4 | Day 14-20 | MaxKB 深读（企业平台 + pgvector RAG） |
| 5 | Day 21-30 | 复刻垂直版（LangGraph + pgvector + MCP + deepeval） |

## 目录

```text
dayNN/
├── java/     # 对照阅读用的 Java 原版
└── python/   # Python 练习与当天产出

notes/
└── dayNN/    # 当天笔记，与代码分开存放
```

根目录是唯一的 uv 项目，30 天共享一个 `.venv`；依赖统一在 `pyproject.toml` 声明。

## 常用命令

```bash
uv sync
uv add <package>
uv run day01/python/order.py
uv run ruff check day01/python
uv run ruff format day01/python
uv run mypy day01/python
```

该机器的 Python 与 uv 由 mise 管理，非交互终端里需写成 `mise exec -- uv ...`。

## 约定

- 每天一个目录，必须留下可运行产出，不接受"只看不写"。
- 笔记写在 `notes/dayNN/`，按"5 分钟能讲清楚"验收。
- `~/repos` 下的第三方仓库（boss-agent-cli、OpenManus、MaxKB）是学习材料，不算自有项目。

## 进度

- [ ] 阶段 1：Python 定向迁跃（Day 1-5）
- [ ] 阶段 2：LLM 应用基础（Day 6-8）
- [ ] 阶段 3：OpenManus 深读（Day 9-13）
- [ ] 阶段 4：MaxKB 深读（Day 14-20）
- [ ] 阶段 5：复刻垂直版（Day 21-30）

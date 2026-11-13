# AGENTS.md

跨工具共享的项目上下文。

## 项目是什么

`java-agent-lab` 是 Java 开发者补齐 Python + Agent 技术栈的学习仓库，执行《AI Agent 工程 30 天学习计划》（2026-11-13 ~ 2026-12-12）。每个 `dayNN/` 是一次独立练习，根目录是唯一的 uv 项目，所有天共享一个 `.venv`。

## 目录约定

- `dayNN/java/`：对照阅读用的 Java 原版
- `dayNN/python/`：Python 练习与当天产出
- `notes/dayNN/`：当天笔记（markdown，Obsidian 可直接打开：frontmatter + callout + 双链）
- `research/YYYY-MM-DD/`：岗位调研、学习计划、路线图等决策依据，按日期分目录，重做调研不覆盖旧结论
- `tools/build_site.py`：站点内容构建脚本
- `docs/`：GitHub Pages 站点（纯静态，无框架）；`docs/content/` 是生成物，不入库

## 进度

阶段划分与每日内容以计划原文为准（[research/2026-11-12/AI-Agent学习计划-30天.md](research/2026-11-12/AI-Agent学习计划-30天.md)），这里只记状态，不重复抄内容。

| 阶段 | 天数 | 状态 |
|---|---|---|
| 1 | Day 1-5 | 进行中 |
| 2 | Day 6-8 | 未开始 |
| 3 | Day 9-13 | 未开始 |
| 4 | Day 14-20 | 未开始 |
| 5 | Day 21-30 | 未开始 |

已完成的天：

- **Day 1**（2026-11-13）Python 迁跃：`day01/python/order.py`（批注版）、`order_bean.py`（Java bean 风格标准版）、`day01/python/demos.py`（10 个坑的可运行演示）、`notes/day01/java-python-diff.md`。验收通过：12 项自测清单全勾。

## 已澄清的认知（避免重复踩）

- GIL 限制的是 CPython 线程执行字节码，不是"只能开一个线程"；asyncio 单线程 + `await` 让出，IO 密集场景不受影响。Agent 服务是 IO 密集型，不是 CPU 密集型。
- Python 无需在类体声明字段，`__init__` 里 `self.x = ...` 即创建实例属性；类体里的 `tags: list[str]` 只是类型注解，不创建属性。
- 装饰器是运行时函数替换（`f = deco(f)`），不是 Java 注解那样的反射元数据。
- `==` ↔ Java `equals()`，`is` ↔ Java `==`；`//` 向下取整、`%` 与除数同号（Java 是与被除数同号）。

## 工具链

- Python 3.11.9、uv 0.13.7，均由 mise 管理；非交互 shell 用 `mise exec -- uv ...`
- ruff（lint/format）、mypy（类型检查）为 dev 依赖
- Docker 只在 VMware 虚拟机里，Windows 宿主机没有 `docker` 命令

## 命令

- `uv sync --group docs`（首次或改了依赖后，含站点构建依赖 markdown-it-py）
- `uv run dayNN/python/xxx.py`
- `uv run ruff check dayNN/python`
- `uv run mypy dayNN/python`
- `uv run --group docs python tools/build_site.py`（重建站点内容；改了 notes/ 或代码后必跑）
- `uv run python -m http.server 8765 --directory docs`（本地预览站点）

## 站点

`docs/` 是学习路径站点，已上线：<https://chayu163.github.io/java-agent-lab/>
推到 `main` 由 `.github/workflows/pages.yml` 自动构建发布（Pages 的 Source 是 GitHub Actions，不是分支部署）。
它不单独维护内容：笔记取自 `notes/`，代码取自 `dayNN/`，调研取自 `research/`。
路线图的节点与每日计划手写在 `docs/assets/roadmap-data.js`——改计划时要同步改这里。

新建 `notes/dayNN/` 后，必须把 `dayNN` 加进 `roadmap-data.js` 对应节点的 `days` 数组，
否则构建脚本会报警并以非零退出（CI 会红）。这是唯一需要手动同步的地方。

## 质量门

`.github/workflows/ci.yml` 在每次 push 和 PR 上跑：`ruff check` → `ruff format --check` → `mypy` → 构建站点。
风格由 `pyproject.toml` 的 `[tool.ruff]` 锁定：4 空格缩进、行宽 100、双引号。

本地复现 CI（`mypy` 和构建都要带 `--group docs`，否则 `markdown_it` 不可见）：

- `uv run ruff check . && uv run ruff format --check .`
- `uv run --group docs mypy .`

## 协作约定

- 这是学习仓库：默认讲解思路、review 代码、指出错误，不代写当日练习，除非用户明确要求。
- 用户是 Java 背景、Python 初学者；解释优先用 Java 概念类比（`equals` ↔ `__eq__`、classpath ↔ venv、`record` ↔ `dataclass`）。
- 每天必须留下可运行产出，只读不写视为不合格。
- 第三方仓库（boss-agent-cli、OpenManus、MaxKB）是学习材料，不能算自有项目写进简历。

## 计划依据

- 计划：[research/2026-11-12/AI-Agent学习计划-30天.md](research/2026-11-12/AI-Agent学习计划-30天.md)
- 调研：[research/2026-11-12/AI岗位调研-杭州上海.md](research/2026-11-12/AI岗位调研-杭州上海.md)
- 路线图原稿：[research/2026-11-12/学习路径图-original.html](research/2026-11-12/学习路径图-original.html)

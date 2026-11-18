# AGENTS.md

跨工具共享的项目上下文。

## 项目是什么

`java-agent-lab` 是 Java 开发者补齐 Python + Agent 技术栈的学习仓库，执行《AI Agent 工程 30 天学习计划》（2026-11-13 ~ 2026-12-12）。每个 `dayNN/` 是一次独立练习，根目录是唯一的 uv 项目，所有天共享一个 `.venv`。

## 目录约定

- `dayNN/README.md`：当天知识树（从 day03 起），讲结构与取舍，不是题解
- `dayNN/java/`：对照阅读用的 Java 原版
- `dayNN/python/`：Python 练习与当天产出
- `notes/dayNN/`：当天笔记（markdown，Obsidian 可直接打开：frontmatter + callout + 双链）
- `notes/dayNN/assets/`：笔记引用的交互图（archify 生成的独立 HTML），构建时拷进站点
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

- **Day 1**（2026-11-13）Python 迁跃：`day01/python/order.py`（批注版）、`order_bean.py`（Java bean 风格标准版）、`day01/python/demos.py`（十项语义差异的可运行演示）、`notes/day01/java-python-diff.md`。验收通过：12 项自测清单全勾。
- **Day 2**（2026-11-14）函数是一等公民：`day02/python/` 下 `decorators.py`、`generators.py`、`context.py`、`typing_practice.py`、`tool_schema.py`（主产出，Pydantic → OpenAI tools schema）；`notes/day02/python-functions-typing.md`，含两幅 archify 交互图（`notes/day02/assets/`）。验收：15 题诊断全部批改，五脚本运行通过。
- **Day 3**（2026-11-17）asyncio 并发：`day03/python/` 下 `00_trace.py`（协程状态机实测）、`01_coroutine.py`~`04_resources.py`（概念/调度/控制/资源四层）、`05_fetch.py`（主产出，httpx 并发调 5 个 API）；`day03/README.md`（知识树）、`notes/day03/asyncio-concurrency.md`，含三幅 archify 交互图。验收：五个脚本全部跑通，ruff/mypy 全绿。
- **Day 4**（2026-11-18）pytest：`day04/python/` 下 `01_fixtures_test.py`、`02_parametrize_test.py`、`03_mock_test.py`、`test_fetch.py`（主产出，给 Day 3 写 5 个测试）；`day04/README.md`（知识树）、`notes/day04/pytest.md`。验收：34 个测试全绿，ruff/format/mypy/构建全过。

进行中的天：暂无。

## 已澄清的认知（避免重复出错）

- GIL 限制的是 CPython 线程执行字节码，不是"只能开一个线程"；asyncio 单线程 + `await` 让出，IO 密集场景不受影响。Agent 服务是 IO 密集型，不是 CPU 密集型。
- Python 无需在类体声明字段，`__init__` 里 `self.x = ...` 即创建实例属性；类体里的 `tags: list[str]` 只是类型注解，不创建属性。
- 装饰器是**定义时**（模块导入时）的函数替换（`f = deco(f)`），不是 Java 注解那样的反射元数据。被装饰函数调 N 次：装饰器函数体只跑 1 次，wrapper 跑 N 次。
- 生成器函数调用后执行 0 行，`next()` 才推进到第一个 `yield`；生成器里的 `return value` 只结束迭代，不产出元素。
- `@contextmanager` 是 `contextlib` 里的标准库函数，不是语言语法；`with` 认的是 `__enter__`/`__exit__` 协议，不要求是类实例。
- 类型注解在运行时**完全不生效**，只有默认值生效；`Any` 是关闭类型检查，不是 Java 的 `Object`。
- `==` ↔ Java `equals()`，`is` ↔ Java `==`；`//` 向下取整、`%` 与除数同号（Java 是与被除数同号）。
- 协程的栈帧是**堆上的对象**，不是线程栈上的一块内存；"挂起"= 帧从栈上摘下、由 coroutine 对象持有。这是 Java 线程无法挂起而 Python 协程可以的物理原因。
- `create_task` 只把 `__step` 放入 loop 的 ready 队列，**不执行**；main 不让出控制权，任务一步都不跑。
- `await` 是"可能挂起"：被等的对象已就绪时不挂起。`await coro()` 就地驱动（同一 Task、嵌套栈），`await task` 只是等（不同 Task、独立栈）。
- `gather` 按**参数顺序**交付并丢弃完成顺序；`as_completed` 按**完成顺序**透传，且产出的是协程不是 Task，必须再 `await` 一次。
- 进出成对的操作（计数、名额），"出"那一半必须放 `finally`，否则取消/异常时泄漏。

## 工具链

- Python 3.11.9、uv 0.13.7，均由 mise 管理；非交互 shell 用 `mise exec -- uv ...`
- dev 组：ruff（lint/format）、mypy（类型检查）、pytest + pytest-asyncio + pytest-cov
- 运行期依赖：httpx、pydantic；站点构建单独在 docs 组（markdown-it-py）
- Docker 只在 VMware 虚拟机里，Windows 宿主机没有 `docker` 命令

## 命令

- `uv sync --group docs`（首次或改了依赖后，含站点构建依赖 markdown-it-py）
- `uv run dayNN/python/xxx.py`（跑单个脚本）
- `uv run pytest -q`（跑全部测试，从仓库根收集，不需要逐个指定目录）
- `uv run --group docs python tools/build_site.py`（重建站点内容；改了 notes/ 或代码后必跑）
- `uv run python -m http.server 8765 --directory docs`（本地预览站点）

## 站点

`docs/` 是学习路径站点，已上线：<https://chayu163.github.io/java-agent-lab/>
推到 `main` 由 `.github/workflows/pages.yml` 自动构建发布（Pages 的 Source 是 GitHub Actions，不是分支部署）。
它不单独维护内容：笔记取自 `notes/`，代码取自 `dayNN/`，调研取自 `research/`，笔记里的 `assets/` 会一起拷进站点。
路线图的节点与每日计划手写在 `docs/assets/roadmap-data.js`——改计划时要同步改这里。

新建 `notes/dayNN/` 后，必须把 `dayNN` 加进 `roadmap-data.js` 对应节点的 `days` 数组，
否则构建脚本会报警并以非零退出（CI 会红）。这是唯一需要手动同步的地方。

## 质量门

`.github/workflows/ci.yml` 在每次 push 和 PR 上跑五步：`ruff check` → `ruff format --check` → `mypy` → `pytest` → 构建站点。
风格由 `pyproject.toml` 的 `[tool.ruff]` 锁定：4 空格缩进、行宽 100、双引号；`notes/` 被排除在外，笔记里的代码围栏按讲解排版，不交给 formatter 重排。

本地复现 CI（`mypy` 和构建都要带 `--group docs`，否则 `markdown_it` 不可见）：

- `uv run ruff check . && uv run ruff format --check .`
- `uv run --group docs mypy .`
- `uv run --group docs python tools/build_site.py`

测试配置在 `pyproject.toml` 的 `[tool.pytest.ini_options]`：`testpaths` 限定收集目录，`asyncio_mode = "auto"` 让异步测试函数不必逐个挂装饰器。

## 协作约定

- 这是学习仓库：默认讲解思路、review 代码、指出错误，不代写当日练习，除非用户明确要求。
- 用户是 Java 背景、Python 初学者；解释优先用 Java 概念类比（`equals` ↔ `__eq__`、classpath ↔ venv、`record` ↔ `dataclass`）。
- 每天必须留下可运行产出，只读不写视为不合格。
- 第三方仓库（boss-agent-cli、OpenManus、MaxKB）是学习材料，不能算自有项目写进简历。

## 写作规范

代码注释、文档说明、笔记一律遵循 `zh-dev-writing` skill（`~/.claude/skills/zh-dev-writing/`），落笔前先读对应细则。

要点：

- 注释只写两件事：What（这是什么，一行）与 Why（为什么这样写，须落到具体后果）。复述代码字面意思的注释不写。
- 用说明文，不用口语。不写「把它」「靠它」「坑」「搞」「塞进去」「一下」「先不用管」这类措辞。
- 理由要可核对：写「否则会怎样」「改回原方案会坏在哪」，「为了性能」「历史原因」不算理由。
- 不引用文档章节号、错误码、内部字段名；把内容本身写出来。
- 注释内统一半角标点，标识符与类型名不翻译。
- 不写行尾注释，不保留注释掉的代码，不为凑覆盖率写模板文档。

既有文字已按此规范整理完毕，无需回头批量改写；发现新的不合规处，先列出再改。

## 计划依据

- 计划：[research/2026-11-12/AI-Agent学习计划-30天.md](research/2026-11-12/AI-Agent学习计划-30天.md)
- 调研：[research/2026-11-12/AI岗位调研-杭州上海.md](research/2026-11-12/AI岗位调研-杭州上海.md)
- 路线图原稿：[research/2026-11-12/学习路径图-original.html](research/2026-11-12/学习路径图-original.html)

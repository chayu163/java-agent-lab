# AGENTS.md

跨工具共享的项目上下文。

## 项目是什么

`java-agent-lab` 是 Java 开发者补齐 Python + Agent 技术栈的学习仓库，执行《AI Agent 工程 30 天学习计划》（2026-11-13 ~ 2026-12-12）。代码按阶段归在 `phaseN/dayNN/` 下，根目录是唯一的 uv 项目，所有天共享一个 `.venv`。

## 目录约定

- `phaseN/dayNN/README.md`：当天知识树（从 day03 起），讲结构与取舍，不是题解
- `phaseN/dayNN/java/`：对照阅读用的 Java 原版
- `phaseN/dayNN/python/`：Python 练习与当天产出
- `notes/phaseN/dayNN/`：当天笔记（markdown，Obsidian 可直接打开：frontmatter + callout + 双链）
- `notes/phaseN/dayNN/assets/`：笔记引用的交互图（archify 生成的独立 HTML），构建时拷进站点
- `research/YYYY-MM-DD/`：岗位调研、学习计划、路线图等决策依据，按日期分目录，重做调研不覆盖旧结论
- `tools/build_site.py`：站点内容构建脚本
- `docs/`：GitHub Pages 站点（纯静态，无框架）；`docs/content/` 是生成物，不入库

目录名里的 `dayNN` 编号在仓库内全局唯一，站点索引与 `curriculum.json` 都按它匹配，新增阶段只建 `phaseN/` 目录、不改编号。

## 进度

计划原文（[research/2026-11-12/AI-Agent学习计划-30天.md](research/2026-11-12/AI-Agent学习计划-30天.md)）记录制定时的决策依据，站点当前每日任务、产出与节点归属以根目录 `curriculum.json` 为准。这里仅记录学习进度。

| 阶段 | 天数 | 状态 |
|---|---|---|
| 1 | Day 1-5 | 完成 |
| 2 | Day 6-8 | 未开始 |
| 3 | Day 9-13 | 未开始 |
| 4 | Day 14-20 | 未开始 |
| 5 | Day 21-30 | 未开始 |

已完成的天：

- **Day 1**（2026-11-13）Python 迁跃：`phase1/day01/python/order.py`（批注版）、`order_bean.py`（Java bean 风格标准版）、`phase1/day01/python/demos.py`（十项语义差异的可运行演示）、`notes/phase1/day01/java-python-diff.md`。验收通过：12 项自测清单全勾。
- **Day 2**（2026-11-14）函数是一等公民：`phase1/day02/python/` 下 `decorators.py`、`generators.py`、`context.py`、`typing_practice.py`、`tool_schema.py`（主产出，Pydantic → OpenAI tools schema）；`notes/phase1/day02/python-functions-typing.md`，含两幅 archify 交互图（`notes/phase1/day02/assets/`）。验收：15 题诊断全部批改，五脚本运行通过。
- **Day 3**（2026-11-17）asyncio 并发：`phase1/day03/python/` 下 `00_trace.py`（协程状态机实测）、`01_coroutine.py`~`04_resources.py`（概念/调度/控制/资源四层）、`05_fetch.py`（主产出，httpx 并发调 5 个 API）；`phase1/day03/README.md`（知识树）、`notes/phase1/day03/asyncio-concurrency.md`，含三幅 archify 交互图。验收：五个脚本全部跑通，ruff/mypy 全绿。
- **Day 4**（2026-11-18）pytest：`phase1/day04/python/` 下 `01_fixtures_test.py`、`02_parametrize_test.py`、`03_mock_test.py`、`test_fetch.py`（主产出，给 Day 3 写 5 个测试）；`phase1/day04/README.md`（知识树）、`notes/phase1/day04/pytest.md`。验收：34 个测试全绿，ruff/format/mypy/构建全过。
- **Day 5**（2026-11-19）mini agent loop：`phase1/day05/python/` 下 `01_messages.py`（消息协议）、`02_registry.py`（工具注册表与 `@tool` 装饰器）、`mini_loop.py`（主产出，脚本化假模型驱动的完整循环）；`phase1/day05/README.md`（知识树）、`notes/phase1/day05/mini-agent-loop.md`。验收：三条验收断言全过（单工具、只读并发、未知工具回填、步数上限），质量门五步全绿。阶段 1 完成。

进行中的天：暂无。阶段 1（Day 1-5）全部完成，下一步是阶段 2 的 Day 6（function calling）。

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
路线图的视觉节点与说明维护在 `docs/assets/roadmap-data.js`，每日任务、产出和节点关联维护在根目录 `curriculum.json`。完成状态由笔记 frontmatter 的 `status: done` 生成。

新建笔记后，必须把对应 `dayNN` 加入 `curriculum.json`，
否则构建脚本会报警并以非零退出（CI 会红）。

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

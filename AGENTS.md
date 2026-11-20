# AGENTS.md

跨工具共享的项目上下文。写作或修改学习文档时，阅读 [LEARNING_DOCS.md](LEARNING_DOCS.md)；设计或修改练习时，阅读 [CODE_PRACTICE.md](CODE_PRACTICE.md)。

## 项目目标

`java-agent-lab` 是 Java 开发者补齐 Python 与 Agent 工程能力的学习仓库，执行 2026-11-13 至 2026-12-12 的 30 天计划。学习者有 Java 后端经验，Python 与 Agent 工程经验较少。解释应以 Python 的实际机制为主，再用边界清楚的 Java 类比辅助迁移。

## 目录约定

- `phaseN/dayNN/README.md`：当天的学习地图、概念关系、代码入口与验收路径。
- 当天 Python 练习直接放在 `phaseN/dayNN/`，不另建 `python/` 子目录。
- `phaseN/dayNN/java/`：必要的 Java 对照。已有日期目录保持原状。
- `notes/phaseN/dayNN/*.md`：当天的详细知识笔记，Obsidian 可直接打开。
- `notes/phaseN/dayNN/assets/`：笔记引用的图表，构建时复制到站点。
- `curriculum.json`：站点每日任务、产出与路线图节点关联的唯一数据源。
- `research/YYYY-MM-DD/`：调研、计划等决策记录，按日期归档。
- `tools/build_site.py`：将笔记、代码、调研和课程索引构建为静态站点内容。
- `docs/`：GitHub Pages 站点源码；`docs/content/` 是忽略的生成物。

`dayNN` 编号在仓库内全局唯一。新增笔记日时，将对应编号加入 `curriculum.json`，构建会检查笔记覆盖情况。路线图节点说明维护在 `docs/assets/roadmap-data.js`。

## 当前进度

阶段 1（Day 1-5）已完成。阶段 2 的 Day 6（function calling）正在进行；阶段 3-5 尚未开始。阶段内容以 [30 天计划](research/2026-11-12/AI-Agent学习计划-30天.md)为依据，阶段 1 的产出记录在对应目录与笔记中。

## 学习文档

- 日 README 和详细笔记的分工、教学顺序、准确性标准与验收要求见 [LEARNING_DOCS.md](LEARNING_DOCS.md)。
- 练习的粒度、README 对应关系、运行和测试要求见 [CODE_PRACTICE.md](CODE_PRACTICE.md)。
- 不确定的语言或库行为先用当前环境验证，再写成结论。标明语言保证、版本行为、实现细节和项目约定的区别。
- 每天需要有可运行产出。不要只留下概念说明。
- 第三方仓库（boss-agent-cli、OpenManus、MaxKB）是学习材料，不是自有项目。

## 已确认的关键语义

- 类型注解本身不强制运行时类型；mypy 等静态检查器与 Pydantic 等运行时校验器是不同机制。注解仍可能保存在运行时并被库读取。
- 装饰器表达式在执行 `def` 语句时求值。模块顶层函数通常在导入时完成装饰，但装饰器不是专属的导入阶段机制。
- 生成器函数调用只创建生成器对象，迭代操作才执行函数体。生成器中的 `return value` 结束迭代；手动捕获 `StopIteration` 时可以读取其 `value`。
- `asyncio.create_task` 创建并排期 Task，不会在调用处内联运行。事件循环在当前 Task 让出控制权后运行已排期任务。
- `await` 可能挂起，也可能直接取得已就绪结果。`await coro()` 不创建新 Task；`await task` 等待另一个 Task。
- `asyncio.gather` 的结果按参数顺序排列。默认情况下某个 awaitable 抛异常时，异常传播给调用方，其他 awaitable 不会因此自动取消。
- `asyncio.as_completed` 在 Python 3.11 中迭代产出 awaitable，需再次 `await` 才得到结果。较新 Python 版本的异步迭代能力不同，相关说明应标版本。
- 对称资源操作的清理放在 `finally` 或上下文管理器中，以覆盖异常和取消路径。

## 工具链

- Python 3.11.9、uv 0.13.7 由 mise 管理；常规命令使用 `mise exec -- uv ...`。
- `dev` 依赖组：ruff、mypy、pytest、pytest-asyncio、pytest-cov。
- 运行期依赖：httpx、pydantic、pgvector、psycopg。站点构建依赖 markdown-it-py，位于 `docs` 依赖组。
- Docker 仅安装在 VMware 虚拟机中，Windows 宿主机没有 Docker 命令。

## 常用命令

- `uv sync --group docs`：首次安装或依赖变更后同步环境。
- `uv run phaseN/dayNN/example.py`：运行直接放在日期目录下的练习脚本。
- 有包内导入时使用 `uv run python -m phaseN.dayNN.module`。
- `uv run pytest -q`：运行全仓库测试。
- `uv run ruff check . && uv run ruff format --check .`：静态检查与格式检查。
- `uv run --group docs mypy .`：类型检查。
- `uv run --group docs python tools/build_site.py`：构建站点内容。
- `uv run python -m http.server 8765 --directory docs`：本地预览站点。

`.github/workflows/ci.yml` 执行 lint、format、mypy、pytest 与站点构建。修改笔记或代码后重建站点。

## 协作约定

- 默认讲解思路、review 代码并指出错误。用户明确要求实现练习或改写材料时，按请求执行。
- 注释、文档和笔记遵循 `zh-dev-writing` skill。注释写必要的 What/Why，不复述代码；理由要描述可验证的具体后果。
- 计划原文记录制定时的决策依据。站点当前日程以 `curriculum.json` 为准，学习进度在本文件维护。

## 计划依据

- 计划：[research/2026-11-12/AI-Agent学习计划-30天.md](research/2026-11-12/AI-Agent学习计划-30天.md)
- 岗位调研：[research/2026-11-12/AI岗位调研-杭州上海.md](research/2026-11-12/AI岗位调研-杭州上海.md)
- 路线图原稿：[research/2026-11-12/学习路径图-original.html](research/2026-11-12/学习路径图-original.html)

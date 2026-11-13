# AI Agent 工程 30 天学习计划

制定日期：2026-11-12 ｜ 执行区间：2026-11-13 ~ 2026-12-12 ｜ 每日 6-8 小时
依据：[AI岗位调研-杭州上海-2026-11-12.md](AI岗位调研-杭州上海-2026-11-12.md)（同目录）

## 一、目标与依据

求职目标：杭州/上海 AI应用·Agent 开发岗（15-30K）。报告结论：Python+MySQL 是筛选线，**LangGraph / MCP / RAG(pgvector) / agent 评测 / Harness** 是薪资分水岭。

现状盘点（2026-11-12 技术测验校准）：

| 维度 | 水平 |
|---|---|
| Java 后端 | 扎实，深读过 Java 源码，读代码方法论可迁移 |
| Python | 仅基础语法；asyncio / GIL / 装饰器不熟；未读过 Python 开源源码 |
| LLM 应用 | function calling 循环理解正确；MCP 概念正确且实际用过 MCP（未自己写过 server） |
| RAG | 概念空白（chunk / embedding 细节 / rerank 不懂） |
| 可展示项目 | 无自有 Agent 项目——boss-agent-cli 是第三方工具，只用过，简历上不能算自己的产出 |

本计划要补的缺口：**LangGraph 编排、RAG+pgvector、agent 评测，以及一个完全属于自己的 Agent 项目**（当前为零，阶段 5 的复刻项目就是它）。产出物不是"看完了"，而是"能讲清 + 有可运行复刻项目"。

## 二、总览

| 阶段 | 天数 | 内容 | 对应 JD 关键词 |
|---|---|---|---|
| 1 | Day 1-5 | Python 定向迁跃（只补 Java→Python 差异点） | Python |
| 2 | Day 6-8 | LLM 应用基础（function calling / RAG / 评测概念） | Tool Calling、RAG |
| 3 | Day 9-13 | OpenManus 深读（agent harness） | Harness、主流智能体框架 |
| 4 | Day 14-20 | MaxKB 深读（企业智能体平台 + pgvector RAG） | Agent 平台/中台、pgvector |
| 5 | Day 21-30 | 复刻垂直版（LangGraph + pgvector + MCP + deepeval） | LangGraph、MCP、agent 质量评测 |

参考仓库：

- OpenManus：https://github.com/FoundationAgents/OpenManus（59k，Python）
- MaxKB：https://github.com/1Panel-dev/MaxKB（23.1k，Python/Django）
- LangGraph：https://github.com/langchain-ai/langgraph（44.8k）+ 官方课程 https://github.com/langchain-ai/langchain-academy
- DeepEval：https://github.com/confident-ai/deepeval（19.5k）
- MCP 官方 servers：https://github.com/modelcontextprotocol/servers
- pgvector：https://github.com/pgvector/pgvector
- MCP 规范：https://modelcontextprotocol.io

## 三、每日结构

- 上午 2h：概念学习（文档/源码/白板）
- 下午 4-5h：动手（写代码、跑实验、读源码）
- 晚上 1h：笔记 + 自测（用"5 分钟讲清楚"标准验收当天内容）
- 每周留半天机动，用于补课或还债

## 四、阶段 1：Python 定向迁跃（Day 1-5）

原则：**不啃语法书**，只学 Java 背景下的差异点；每天产出一个可运行的小东西。

| Day | 内容 | 产出 |
|---|---|---|
| 1 | 环境：uv、项目结构、ruff/mypy 简介；Java→Python 差异清单（默认参数可变对象、`is` vs `==`、真值判断、类属性 vs 实例属性、模块导入、包管理） | 差异笔记；把一个小 Java 类（如订单状态机）翻译成 Python |
| 2 | 函数是一等公民：装饰器（手写 @retry、@timer）、生成器 yield、with 上下文管理器、typing（Protocol / Generic / dataclass / Pydantic v2） | 用 Pydantic 定义一套 Tool schema |
| 3 | asyncio：event loop、coroutine、Task、gather、Semaphore、timeout、async with | asyncio + httpx 并发调 5 个公共 API（带超时和并发上限） |
| 4 | pytest：fixture vs JUnit @BeforeEach、参数化、mock、覆盖率；ruff/mypy 跑通 | 给 Day 3 代码写 5 个测试（3 成功路径 + 2 错误路径） |
| 5 | mini agent loop 预热：不用 LLM，用 mock 的 tool_calls JSON 写 50-100 行循环：解析 → 路由 → 执行（asyncio 并发只读工具）→ 回填 → 终止条件 | mini_loop.py |

验收：能不看教程手写 asyncio.gather 并发调用 + pytest 测试；能说出 Python 默认参数与 Java 默认参数的区别。

## 五、阶段 2：LLM 应用基础（Day 6-8）

| Day | 内容 | 产出 |
|---|---|---|
| 6 | function calling 协议细节：tools schema、tool_calls 返回结构、多轮消息回填、stop_reason、并行工具调用；实际调一次兼容 OpenAI 协议的 API | 一次完整工具调用会话的抓包/日志笔记 |
| 7 | embedding 原理（向量、余弦相似度、HNSW/IVF 索引）、chunk 策略（固定窗口/按结构切/按语义切、overlap）、rerank；Docker 起 pgvector，写 ingestion + top-k 查询 | 本地 pgvector 检索 demo |
| 8 | 白板 RAG 全链路；评测概念（golden set、召回/命中、LLM-as-judge、回归）；读 MCP 规范（架构、tools/resources/prompts、transport） | RAG 链路白板图 + "为什么 MCP 在 function calling 之上"的 500 字解释 |

**Checkpoint**：Day 8 画不出 RAG 全链路 → 加 1 天，不带病进入阶段 3。

必须搞懂的三处认知（测验中暴露的偏差）：

1. RAG 不是"治模型输出不稳定"，是解决模型不知道私有/最新知识 + 上下文窗口上限。
2. chunk 太大：噪声稀释、检索不准、token 贵；太小：语义碎片、指代丢失；rerank 是检索后第二道筛。
3. 装饰器是定义时的高阶函数替换（`f = deco(f)`），不是 Java 注解那样的运行时反射元数据；GIL 对 IO 密集的 agent 服务无影响，asyncio 就是为此而生。

## 六、阶段 3：OpenManus 深读（Day 9-13）

| Day | 内容 | 产出 |
|---|---|---|
| 9 | clone 仓库；目录结构、pyproject.toml、依赖关系；入口：main.py → app/agent/manus.py → BaseAgent | 30 分钟画出"目录地图" |
| 10 | agent loop：BaseAgent.run/step；ToolCallAgent 的 think/act；tool registry（BaseTool、工具集合）与并发执行 | loop 时序图 |
| 11 | planner（PlanningFlow）、memory、prompt 组织方式 | 规划/记忆模块笔记 |
| 12 | sandbox 工具、browser 工具集成、异常与重试、终止条件 | 工具系统笔记 |
| 13 | 综合：输出《OpenManus 架构导读》（2000 字）+ 架构图；对照你用过的第三方工具 boss-agent-cli，列出 3 个可借鉴到复刻项目里的设计点 | 导读文档 + 架构图 + 借鉴清单 |

**Checkpoint**：能 5 分钟讲清"一次任务从用户输入到工具执行再回到模型的完整链路"。

## 七、阶段 4：MaxKB 深读（Day 14-20）

Django 与 Spring 的类比先建立：MTV ↔ MVC，ORM ↔ JPA，migration ↔ Flyway，settings.py ↔ application.yml。

| Day | 内容 | 产出 |
|---|---|---|
| 14 | Django 项目结构：apps/、urls、settings、ASGI 启动链路、依赖（DRF） | 启动链路图 |
| 15 | 文档 ingestion：解析（pdf/docx）、分块、embedding 调模型、pgvector 表结构（models 定义） | ingestion 数据流 |
| 16 | 检索链路：向量检索 SQL/ORM、混合检索、rerank、prompt 组装、相似度阈值 | 检索链路图 |
| 17 | 应用编排：工作流引擎、节点类型、函数库、agent 模式 | 编排模块笔记 |
| 18 | 工程细节：权限/租户、异步任务、日志、模型管理 | 工程笔记 |
| 19-20 | 综合：架构图 + RAG 数据流 + 3 个设计取舍；做"JD 关键词 → MaxKB 实现位置"映射表 | 导读文档 + 映射表 |

**Checkpoint**：能回答"MaxKB 的检索链路怎么走、为什么这么设计、pgvector 表怎么建"。

## 八、阶段 5：复刻垂直版（Day 21-30）

场景建议：**电商售后知识库客服 Agent**（报告里电商类需求多；也可换企业 IT 运维知识库，看哪个素材好找）。Scope 收敛：单轮问答 + 2 个工具（订单查询 mock、工单创建 mock）+ 敏感操作 human-in-the-loop。

注意：这是你**唯一**的自有 Agent 项目（boss-agent-cli 不是你的），按作品集标准做：架构图、eval 数字、README、Docker 一键可跑，四样缺一不可。

| Day | 内容 | 产出 |
|---|---|---|
| 21-22 | 架构设计：LangGraph 状态图（意图 → 检索 → 回答 → 工具 → 升级人工）、pgvector schema、FastAPI 目录结构；写一页 ADR | 架构图 + ADR |
| 23-24 | 知识 ingestion：文档 → chunk → embedding → pgvector；检索 API + 测试 | 可用的检索服务 |
| 25-26 | LangGraph 编排：StateGraph、节点、条件边；2 个 MCP 工具；human-in-the-loop 确认；接入 LLM | 主链路可跑通 |
| 27-28 | deepeval：30-50 条 eval set（答案正确性、工具选择、该拒答就拒答）；pytest 集成；跑回归修问题 | eval 报告 |
| 29 | Docker Compose 一键起（pg + api）；README + 架构图 | 可复现的仓库 |
| 30 | 简历三段话（STAR 化，对齐报告 JD 关键词）+ 20 题面试自测 + 复盘 | 简历素材 + 自测清单 |

**Checkpoint**：demo 跑通 3 条主链路；eval 报告有数字；能 5 分钟讲架构、能答"为什么用 LangGraph 而不是手写循环"。

## 九、产出物清单（最终交付）

1. Python 差异笔记 + mini_loop.py
2. RAG 白板图 + pgvector 检索 demo
3. OpenManus 架构导读（2000 字）+ 架构图 + 与 boss-agent-cli 对照表
4. MaxKB 架构导读 + JD 关键词映射表
5. 复刻项目仓库（Docker 可跑、含 eval 报告，简历核心资产）
6. 简历三段话 + 面试 20 题

## 十、放弃线（止损规则）

- Day 8 画不出 RAG 全链路 → 加 1 天，不进入 MaxKB。
- Day 13 讲不清 OpenManus 链路 → 回读 2 天，或降级为"只读 loop + 工具系统"。
- Day 20 MaxKB 读不完 → 砍掉工作流引擎，只保 ingestion + 检索链路。
- Day 28 eval 指标不理想 → 收敛场景和 eval 集，不追指标、不扩功能。

## 十一、风险与应对

| 风险 | 应对 |
|---|---|
| Python 生态踩坑（依赖冲突、版本） | 每个实验独立目录 + uv 管理，不污染全局环境 |
| LLM API 成本 / 网络 | 开发用便宜模型或本地 ollama，仅 eval 用强模型；注意代理（Clash 7897） |
| MaxKB 代码量大（生产级产品） | 只追"请求进来 → 检索 → 回答"一条线，其余跳过 |
| 时间碎片 | 每天固定上午 2h "学习块"不可挪用；当日任务超时就按放弃线砍 |
| 只读不写（最大的坑） | 每个阶段都有可运行产出物，读完必须落到代码或文档 |

## 附：Java→Python 必踩的 10 个坑（自查表）

1. 默认参数在 `def` 时求值一次，可变对象被所有调用共享
2. `is` 比较 identity，`==` 比较值
3. 空列表/空字典/空字符串为假，`if []:` 会走 False 分支
4. 类属性被所有实例共享，实例属性要在 `__init__` 里赋值
5. GIL：字节码单线程，CPU 密集用多进程，IO 密集用 asyncio
6. 装饰器是定义时的函数替换，不是运行时注解
7. 模块导入基于 `sys.path`，没有 classpath 概念
8. 依赖管理用 uv/pyproject.toml，不是 maven/gradle
9. 除法 `/` 是浮点，整除用 `//`
10. 缩进即语法，tab/空格混用直接报错

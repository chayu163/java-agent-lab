/**
 * 路线图数据：节点、分带、对应天数与产出。
 * 结构照搬 research/2026-11-12/学习路径图-original.html 的 4 带 10 节点，
 * 内容取自 research/2026-11-12/AI-Agent学习计划-30天.md 与岗位调研。
 */
window.ROADMAP = {
  bands: [
    {
      id: "foundation",
      name: "底座",
      note: "过简历筛选",
      accent: "foundation",
      collapsible: false,
    },
    {
      id: "agent",
      name: "Agent 工程",
      note: "决定薪资上限",
      accent: "agent",
    },
    {
      id: "retrieval",
      name: "检索与评测",
      note: "可不可用、好不好用",
      accent: "retrieval",
    },
    {
      id: "delivery",
      name: "作品与投递",
      note: "可验证产出",
      accent: "delivery",
    },
  ],

  nodes: [
    {
      id: "python",
      band: "foundation",
      name: "Python 工程化",
      sub: "34/50 岗位点名",
      badge: "筛选线",
      lead: "从 Java 思维迁跃：不是重学语言，只补差异点。",
      desc:
        "目标岗位里 34/50 点名 Python，两个城市并列第一。计划不啃语法书，" +
        "只处理 Java 背景下的真实差异：可变默认参数、is 与 ==、类属性、装饰器、asyncio、打包管理。" +
        "每天必须留下可运行的小东西，读完不写等于没读。",
      skills: ["uv / pyproject", "ruff + mypy", "asyncio", "pytest", "Pydantic v2"],
      days: ["day01", "day02", "day03", "day04", "day05"],
      plan: [
        { day: "Day 1", task: "环境、项目结构、Java→Python 差异清单", out: "差异笔记 + 订单状态机翻译", done: true },
        { day: "Day 2", task: "装饰器 / 生成器 / with / typing / Pydantic v2", out: "一套 Pydantic Tool schema" },
        { day: "Day 3", task: "asyncio：event loop、Task、gather、Semaphore、timeout", out: "httpx 并发调 5 个 API（带超时与并发上限）" },
        { day: "Day 4", task: "pytest：fixture、参数化、mock、覆盖率", out: "给 Day 3 代码写 5 个测试" },
        { day: "Day 5", task: "mini agent loop：解析 → 路由 → 执行 → 回填 → 终止", out: "mini_loop.py（不用真 LLM）" },
      ],
    },
    {
      id: "sql",
      band: "foundation",
      name: "MySQL 建模与调优",
      sub: "24/50 岗位点名",
      badge: "筛选线",
      lead: "第二刚需，但当前计划没有单独排期。",
      desc:
        "调研里 MySQL 出现 24 次，仅次于 Python。你 Java 后端的索引、事务、执行计划底子可以直接迁移。" +
        "计划正文没有为它划出独立的天数，实际会在阶段 5 建 pgvector schema 时同步练习——" +
        "这是一处已知缺口，不是遗漏。",
      skills: ["索引与执行计划", "事务隔离级别", "慢查询", "分库分表概念"],
      days: [],
      gap: "计划未单列天数，靠阶段 5 的 pgvector schema 补。",
      plan: [
        { day: "复用", task: "Java 后端的 MySQL 经验直接迁移，不需要重学", out: "—" },
        { day: "Day 21-22", task: "设计 pgvector schema（向量表 + 元数据表）", out: "schema 设计写进 ADR" },
      ],
    },
    {
      id: "deploy",
      band: "foundation",
      name: "Docker + Redis",
      sub: "部署与缓存基本功",
      badge: "筛选线",
      lead: "Docker 9 次、Redis 8 次，上海要求更高。",
      desc:
        "容器化与缓存是工程基本功，也是作品能不能「一键跑起来」的前提。" +
        "计划里它不占独立天数，而是嵌在 pgvector 起库和最终 Docker Compose 两个节点上。" +
        "注意：你的 Docker 装在 VMware 虚拟机里，宿主机没有 docker 命令。",
      skills: ["Dockerfile", "docker compose", "Redis 缓存", "卷与网络"],
      days: [],
      plan: [
        { day: "Day 7", task: "Docker 起 pgvector，写 ingestion + top-k 查询", out: "本地 pgvector 检索 demo" },
        { day: "Day 29", task: "Docker Compose 一键起（pg + api）", out: "可复现的仓库" },
      ],
    },
    {
      id: "fastapi",
      band: "foundation",
      name: "FastAPI 服务层",
      sub: "接口 / 鉴权 / 日志",
      badge: "支撑",
      lead: "把能力包成服务，作品的门面。",
      desc:
        "FastAPI 之于 Flask 更像 Spring Boot：自带 Pydantic 校验、依赖注入、OpenAPI 文档。" +
        "你在 Java 侧的服务分层、鉴权、日志经验可以直接搬过来，只是注解换成了类型注解 + 装饰器。",
      skills: ["路由与依赖注入", "Pydantic 校验", "中间件", "OpenAPI"],
      days: [],
      plan: [
        { day: "Day 21-22", task: "FastAPI 目录结构、依赖注入、配置", out: "架构图 + ADR" },
        { day: "Day 23-24", task: "检索 API + 测试", out: "可用的检索服务" },
      ],
    },
    {
      id: "toolcall",
      band: "agent",
      name: "Tool Calling / MCP",
      sub: "结构化函数调用",
      badge: "涨薪项",
      lead: "15-30K 顶部岗位明确点名，MCP 是 2026 的新标准。",
      desc:
        "中安智联的 15-30K 岗位直接写了 Tool Calling + LangGraph + MCP + Pydantic。" +
        "你用过 MCP 客户端，但没写过 server——简历上「自己实现一个 MCP server」是强信号。" +
        "Protocol 从协议层解决「工具怎么被发现和调用」，是在 function calling 之上的一层。",
      skills: ["tools schema", "tool_calls 回填", "并行工具调用", "MCP server"],
      days: ["day06", "day25", "day26"],
      plan: [
        { day: "Day 6", task: "function calling 协议细节 + 调一次兼容 OpenAI 协议的 API", out: "完整工具调用会话的日志笔记" },
        { day: "Day 8", task: "读 MCP 规范：tools / resources / prompts / transport", out: "「为什么 MCP 在 function calling 之上」500 字" },
        { day: "Day 25-26", task: "实现 2 个 MCP 工具，接进 LangGraph 主链路", out: "主链路可跑通" },
      ],
    },
    {
      id: "langgraph",
      band: "agent",
      name: "LangGraph 多 Agent 编排",
      sub: "状态机 / 人机协同",
      badge: "涨薪项",
      lead: "面试里最高频的追问点：为什么用图而不是手写循环。",
      desc:
        "LangGraph 把 Agent 循环显式建模成状态图：节点、条件边、检查点、human-in-the-loop。" +
        "对 Java 背景来说它非常眼熟——就是一个可持久化的状态机，和 Day 1 写的 Order 是同一类东西，" +
        "只是状态转移由模型决定而不是由事件决定。",
      skills: ["StateGraph", "条件边", "checkpointer", "human-in-the-loop", "多 Agent 协作"],
      days: ["day21", "day22", "day25", "day26"],
      plan: [
        { day: "Day 21-22", task: "设计状态图：意图 → 检索 → 回答 → 工具 → 升级人工", out: "架构图 + ADR" },
        { day: "Day 25-26", task: "StateGraph、节点、条件边、接入 LLM、人工确认", out: "主链路可跑通" },
      ],
    },
    {
      id: "rag",
      band: "retrieval",
      name: "RAG 全链路",
      sub: "分块 / pgvector / rerank",
      badge: "核心",
      lead: "从入库到回答，每个环节都要能讲清取舍。",
      desc:
        "RAG 解决的不是「模型输出不稳」，是模型不知道你的私有数据、以及上下文窗口有上限。" +
        "全链路：解析 → 分块 → embedding → 向量库 → 检索 → rerank → 拼 prompt。" +
        "pgvector 在调研里出现 5 次，Agent 岗常配。",
      skills: ["chunk 策略", "embedding", "pgvector / HNSW", "rerank", "相似度阈值"],
      days: ["day07", "day08", "day23", "day24"],
      plan: [
        { day: "Day 7", task: "embedding 原理、chunk 策略、rerank；Docker 起 pgvector", out: "本地 pgvector 检索 demo" },
        { day: "Day 8", task: "白板 RAG 全链路", out: "RAG 链路白板图" },
        { day: "Day 23-24", task: "知识 ingestion：文档 → chunk → embedding → pgvector", out: "可用的检索服务" },
      ],
    },
    {
      id: "eval",
      band: "retrieval",
      name: "Agent 质量评测",
      sub: "评测集 / 回放 / 回归",
      badge: "核心",
      lead: "agent 质量评测已经单独成岗（15-25K）。",
      desc:
        "赛思泰克把「agent 质量评测」直接写进了岗位要求。这是最容易拉开差距也最容易被忽略的一块：" +
        "没有 eval 数字的 Agent 项目，在面试里只能算 demo。三件事：golden set 构建、" +
        "LLM-as-judge、回归不退化。",
      skills: ["golden set", "LLM-as-judge", "deepeval", "回归测试"],
      days: ["day08", "day27", "day28"],
      plan: [
        { day: "Day 8", task: "评测概念：召回 / 命中 / judge / 回归", out: "概念笔记" },
        { day: "Day 27-28", task: "deepeval：30-50 条 eval set，pytest 集成", out: "eval 报告（带数字）" },
      ],
    },
    {
      id: "proj",
      band: "delivery",
      name: "三件作品",
      sub: "编排 / RAG / 垂直场景",
      badge: "作品集",
      lead: "唯一属于自己的 Agent 项目，四样缺一不可。",
      desc:
        "boss-agent-cli 是第三方工具，不能算你的产出。所以阶段 5 的复刻项目是简历核心资产。" +
        "场景收敛为电商售后知识库客服 Agent：单轮问答 + 2 个工具（订单查询、工单创建）+ 敏感操作人工确认。" +
        "架构图、eval 数字、README、Docker 一键可跑——四样缺一不可。",
      skills: ["LangGraph", "pgvector", "MCP", "deepeval", "Docker Compose"],
      days: ["day21", "day22", "day23", "day24", "day25", "day26", "day27", "day28", "day29", "day30"],
      plan: [
        { day: "Day 21-22", task: "架构设计：状态图、schema、目录结构", out: "架构图 + ADR" },
        { day: "Day 23-24", task: "知识 ingestion + 检索 API", out: "可用的检索服务" },
        { day: "Day 25-26", task: "LangGraph 编排 + MCP 工具 + 人机协同", out: "主链路跑通" },
        { day: "Day 27-28", task: "deepeval 评测集与回归", out: "eval 报告" },
        { day: "Day 29", task: "Docker Compose + README + 架构图", out: "可复现的仓库" },
        { day: "Day 30", task: "简历三段话 + 面试自测", out: "简历素材" },
      ],
    },
    {
      id: "resume",
      band: "delivery",
      name: "简历与投递",
      sub: "缺口补齐 + 面试",
      badge: "出口",
      lead: "把 30 天变成三句话和 20 道能答的题。",
      desc:
        "调研显示 54% 的岗位要 3-5 年经验，你是应届——所以简历不能靠年限，要靠可验证的产出。" +
        "最后一天做两件事：把项目写成 STAR 三段话并对齐 JD 关键词；把 20 道高频追问过一遍。",
      skills: ["STAR 叙事", "JD 关键词对齐", "面试自测", "复盘"],
      days: ["day30"],
      plan: [
        { day: "Day 30", task: "简历三段话（STAR 化，对齐 JD 关键词）", out: "简历素材" },
        { day: "Day 30", task: "20 题面试自测 + 复盘", out: "自测清单" },
      ],
    },
  ],

  stops: [
    { day: "Day 8", text: "画不出 RAG 全链路 → 加 1 天，不带病进入阶段 3" },
    { day: "Day 13", text: "讲不清 OpenManus 链路 → 回读 2 天，或降级为只读 loop + 工具系统" },
    { day: "Day 20", text: "MaxKB 读不完 → 砍掉工作流引擎，只保 ingestion + 检索链路" },
    { day: "Day 28", text: "eval 指标不理想 → 收敛场景和 eval 集，不追指标、不扩功能" },
  ],
};

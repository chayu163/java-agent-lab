# 杭州/上海 AI应用·Agent岗 15-30K 市场调研

数据来源：BOSS 直聘本地缓存（2026-11-12 09:09–09:12 抓取，共 59 条去重，与 15-30K 有交叠的 50 条）。
抓取后平台命中环境风控（code 37），详情页 JD 正文未能拉取；本文基于列表页字段（标题/薪资/skills 标签/行业/规模）分析。

## 一、市场概况（50 条命中样本）

- 城市分布：杭州 26 / 上海 24
- 经验要求：3-5 年 27 条（54%）为主，1-3 年 10 条，5-10 年 6 条，经验不限 5 条 → **3-5 年是主战场**
- 学历：本科 94%，大专仅 4 条 → 本科即可，不卡硕士
- 公司规模：100-499 人占 38%，20-99 人 + 0-20 人占 34%，大厂（1000+）占 28% → **中小公司是主力需求方**
- 行业：计算机软件 11、互联网 9、人工智能 4，其余分散在智能硬件/医疗器械/物流/电商等 → **AI 应用岗已渗透到传统行业，不只在 AI 公司**
- 岗位标题：Agent/智能体相关 30/50 = 60%，纯"AI应用"30%，AIGC/算法各 1 → **"Agent 落地"就是当前主叙事**

## 二、技术栈需求词频（15-30K 样本，按城市）

| 技能 | 杭州(26) | 上海(24) | 全量 | 备注 |
|---|---|---|---|---|
| Python | 17 | 17 | **34** | 绝对刚需，两个城市并列第一 |
| MySQL | 14 | 10 | **24** | 第二刚需 |
| Java | 7 | 9 | 16 | 上海略多；Spring/SpringCloud 系大公司多见 |
| Docker | 3 | 6 | 9 | 上海要求更高 |
| Redis | 3 | 5 | 8 | |
| Spring/SpringCloud | 3+2 | 5+2 | 12 | Java 生态配套 |
| PyTorch | 2 | 5 | 7 | 上海偏多（偏算法的 Agent 岗） |
| 分布式/微服务经验 | 3+1 | 3+3 | 10 | 中大厂标配 |
| Flask | 3 | 2 | 5 | 轻量服务框架 |
| PostgreSQL | 3 | 2 | 5 | Agent 岗常配（pgvector） |
| C++/C | 4 | 4 | 9 | 大厂 ICT/端侧岗 |
| LLM 专属技能 | LangGraph、MCP、Tool Calling、Pydantic、agent质量评测、RAG、主流智能体框架、Harness | | | 每项 1-2 次，但**出现在薪资最高的岗位** |

LLM 专属技能虽然词频低，但集中出现在 15-30K 顶部区间（中安智联 15-30K 要 LangGraph+MCP+Tool Calling；企顺 16-17K 要 RAG；赛思泰克 15-25K 要 agent 质量评测）。这是拉开薪资差距的部分。

## 三、需求项目类型（从行业 × 岗位标题推断）

1. **通用 Agent 平台/中台**（最多）：企业内部智能体搭建，Tool Calling、MCP、多 Agent 编排（LangGraph）。代表：中安智联、赛思泰克（agent 质量评测）、西信科技（CLI 开发、智能体框架）
2. **垂直行业 Agent**：
   - 电商：卿林科技（电商 AI Agent）
   - 医疗：黑焰医疗、智慧树（医疗健康）
   - 物流：先达国际（跨境物流 AI Agent 后端）
   - 制造业：羚数智能（离散装备制造）
   - 金融：度小满金融
   - 日化/旅游/家居：念妆、玩点科技、梓晨
3. **AIGC 应用**：生图/生视频/ComfyUI 工作流（杭州凌沫）
4. **AI 原生应用/端侧**：佳量脑科学（AI 原生移动端）、智能硬件公司（炽云、益积、OutIn、术也）
5. **外包/驻场**：万宝盛华、佰钧成（华为外包）、盖硕（农夫山泉外包）、外企德科 → 门槛低但薪资天花板低，慎选

## 四、给你的简历/学习路线建议

### 必须有（简历筛选线）
- **Python + MySQL**：34/50 与 24/50，无讨论余地
- **Docker + Redis**：部署与缓存基本功
- FastAPI/Flask 任一服务框架 + 一套完整后端项目经验
- 本科 + 3-5 年经验叙述（1-3 年可投的岗位也存在，见明细表）

### 拉开差距（决定你落在 15K 还是 30K）
1. **Agent 工程框架**：LangGraph / LangChain，重点掌握状态机编排、多 Agent 协作、human-in-the-loop
2. **Tool Calling / MCP 协议**：15-30K 顶部岗位明确点名；MCP 是 2026 年的新标准，简历上写一个自己实现的 MCP server 是强信号
3. **RAG 全链路**：向量库（pgvector/PostgreSQL 出现 5 次）、分块策略、rerank、评估
4. **Agent 评测**：agent 质量评测已单独成岗（15-25K），掌握 eval 集构建、回放、回归测试
5. **PyTorch 基础**（上海岗位偏重要）：不必会训练，能讲清 fine-tune/LoRA 与推理部署即可

### 简历项目类型建议（对应上面五类需求）
- 一个 **多 Agent 编排项目**（如用 LangGraph 做带工具调用的研究/运维 Agent，接 MCP 工具）
- 一个 **RAG 知识库项目**（PostgreSQL + pgvector，讲清评估指标）
- 一个 **垂直场景落地项目**（电商客服/医疗问答等，体现业务理解）
- 有你的 boss-agent-cli 这类 CLI/工具项目本身就是"Agent 工程能力"的直接证明（Tool Calling、MCP server、子进程隔离、风控熔断——全是 JD 高频词）

## 五、明细表（50 条，按城市/薪资排序）

| 城市 | 薪资 | 职位 | 公司 | 区域 | 经验 | 学历 | 行业 | 规模 | 技能标签 | 链接 |
|---|---|---|---|---|---|---|---|---|---|---|
| 上海 | 18-30K | AI Agent 工程师 | 智慧树 | 徐汇区 | 3-5年 | 本科 | 互联网 | 1000-9999人 | 搭建AI智能体、PyTorch、Agent 工程师、Docker、PostgreSQL、MySQL、机器学习经验、MongoDB、Spark、Python | [链接](https://www.zhipin.com/job_detail/057a5147148c816d0nZ82ty0EVpV.html) |
| 上海 | 18-22K | AI Agent开发工程师 | 黑焰医疗 | — | 3-5年 | 本科 | 医疗器械 | 100-499人 | 全栈侧重后端、Golang、Node.js、Python、计算机相关专业、全栈项目经验、前端开发经验、后端开发经验、英语读写能力良好 | [链接](https://www.zhipin.com/job_detail/4142333a6514c0bd0nJ92tm7FVRV.html) |
| 上海 | 17-22K·13薪 | AI应用开发工程师 | 益积智能 | 浦东新区 | 3-5年 | 本科 | 通信/网络设备 | 0-20人 | C#、Nginx、PyTorch、分布式经验、Docker、Pandas、MySQL、机器学习经验、Redis、架构设计经验、Python、Flask | [链接](https://www.zhipin.com/job_detail/0140c45871a71d6903xz3d65FVZU.html) |
| 上海 | 16-26K | AIAgent后端工程师 | 先达国际 | — | 3-5年 | 本科 | 跨境物流 | 1000-9999人 | Python、Golang、MySQL、Oracle、AIagent、AI | [链接](https://www.zhipin.com/job_detail/0f2f01088ae717380nxy2tq_GVBT.html) |
| 上海 | 16-20K | AI Agent开发工程师 | 可利邦 | 浦东新区 | 3-5年 | 本科 | 大数据 | 100-499人 | Java、SpringCloud、MySQL、Spring | [链接](https://www.zhipin.com/job_detail/c31b13664df22ddb0nx509-9E1BV.html) |
| 上海 | 16-17K | AI Agent应用开发 | 企顺 | 浦东新区 | 1-3年 | 本科 | 计算机服务 | 1000-9999人 | 企业 AI 应用、Django、Redis、RAG、Python | [链接](https://www.zhipin.com/job_detail/c321d3c5c47933a70nN73ti_FlpX.html) |
| 上海 | 16-24K·14薪 | AI Agent开发工程师 | 氦图科技 | 浦东新区 | 1年以内 | 本科 | 企业服务 | 100-499人 | 全栈侧重后端、Node.js、Python、Java、Spring/Spring Boot、MySQL/Redis/MongoDB、英语读写能力良好、后端开发经验、计算机相关专业、AI Agent | [链接](https://www.zhipin.com/job_detail/a795981636810b630nx72tW7ElpX.html) |
| 上海 | 16-28K·13薪 | 高级AI Agent研发工程师 | 向量涌现 | 杨浦区 | 3-5年 | 本科 | 人工智能 | 0-20人 | — | [链接](https://www.zhipin.com/job_detail/31d440ee710f36c20nV-29-1EFJS.html) |
| 上海 | 15-25K·14薪 | AI Agent 工程师 | 炽云科技 | 杨浦区 | 3-5年 | 本科 | 智能硬件 | 100-499人 | PyTorch、Python | [链接](https://www.zhipin.com/job_detail/332bcf9873e329140nB429S-F1FX.html) |
| 上海 | 15-30K·15薪 | 资深AI Agent应用工程师 | 远图未来 | 浦东新区 | 5-10年 | 本科 | 智能硬件/消费电子 | 1000-9999人 | 全栈项目经验、计算机相关专业、Agent、Harness | [链接](https://www.zhipin.com/job_detail/890693f8cf07695d0nx-3N-7E1tU.html) |
| 上海 | 15-30K | AI Agent开发工程师 | 谷斗科技(上海)... | 宝山区 | 1-3年 | 本科 | 计算机软件 | 100-499人 | Python | [链接](https://www.zhipin.com/job_detail/4dffe962a810a8430nV42dW5EFNY.html) |
| 上海 | 15-18K·13薪 | ai应用开发工程师/aiAgent开发应用工程师 | 抱朴 | 杨浦区 | 3-5年 | 本科 | 进出口贸易 | 20-99人 | Nginx、Docker、PostgreSQL、MySQL、Redis、架构设计经验、Python | [链接](https://www.zhipin.com/job_detail/fded437eabc192010nN53NS1EVtR.html) |
| 上海 | 15-20K | AI Agent 开发工程师 | 致拓科技 | 闵行区 | 3-5年 | 本科 | 计算机软件 | 100-499人 | PyTorch、MySQL、Python | [链接](https://www.zhipin.com/job_detail/25eb9b95134745530nN529S1EFdZ.html) |
| 上海 | 15-30K·14薪 | ai应用开发/agent开发/算法岗（接受应届） | 外企德科数字 | 浦东新区 | 经验不限 | 本科 | 互联网 | 10000人以上 | Python、C++、PyTorch、Kafka、MySQL | [链接](https://www.zhipin.com/job_detail/08432047591f6cc30nJy2dW8EVZX.html) |
| 上海 | 15-30K·14薪 | AI应用开发（java python c/c++） | 深圳某大型ICT基础设施与智能终端上市公司 | — | 经验不限 | 本科 | 计算机软件 | 10000人以上 | C++、C、Java、Python、分布式经验、微服务经验 | [链接](https://www.zhipin.com/job_detail/13874e2278be32130nN53Ni7EVZS.html) |
| 上海 | 15-25K·13薪 | AI 应用开发工程师 | OutIn | 虹口区 | 3-5年 | 本科 | 智能硬件/消费电子 | 100-499人 | Java、大数据经验、Python | [链接](https://www.zhipin.com/job_detail/b2afaa6125ca26150nx829q1EFJQ.html) |
| 上海 | 15-18K | ai应用开发工程师 | 上海海智智造科技 | 徐汇区 | 3-5年 | 本科 | 互联网 | 100-499人 | JVM、Java、Tomcat、分布式经验、Docker、微服务经验、MySQL、MyBatis、Redis、Spring | [链接](https://www.zhipin.com/job_detail/98f27368f469a35e0nx83di_EVFQ.html) |
| 上海 | 14-16K | AI Agent开发工程师 | 西信科技 | 嘉定区 | 3-5年 | 本科 | 计算机软件 | 100-499人 | Python、Java、团队管理经验、主流智能体框架、后端/智能化工具开发、Agent智能体开发、CLI开发 | [链接](https://www.zhipin.com/job_detail/11148a12404f984d0nN53dy0FVZZ.html) |
| 上海 | 14-17K | AI 应用开发工程师 | 艾天科技 | 浦东新区 | 5-10年 | 本科 | 大数据 | 100-499人 | Python、Spring、微服务经验 | [链接](https://www.zhipin.com/job_detail/4f234e252dbd12c30nx839S5E1RU.html) |
| 上海 | 12-16K | AI Agent项目实施工程师 | 上海云鸽信息科技 | 浦东新区 | 1-3年 | 大专 | 移动互联网 | 0-20人 | OA、计算机相关专业、CRM | [链接](https://www.zhipin.com/job_detail/5db548a57146c5690nx429q4EFRW.html) |
| 上海 | 12-20K | AI 应用开发工程师（离散装备制造业方向） | 上海羚数智能科技... | 浦东新区 | 1-3年 | 本科 | 计算机软件 | 20-99人 | Python、Java、C++、Flask、Docker | [链接](https://www.zhipin.com/job_detail/1956058099868d660nx43Nm0E1pY.html) |
| 上海 | 12-16K·13薪 | AI应用开发工程师 | 百联全渠道 | 黄浦区 | 在校/应届 | 本科 | 生活服务(O2O) | 500-999人 | Java、Spring、SpringCloud、MySQL、Redis、Oracle | [链接](https://www.zhipin.com/job_detail/1174cec60442d6d60nJ-3d29FVdQ.html) |
| 上海 | 10-15K·14薪 | AI Agent工程师 | 为恒智能 | — | 经验不限 | 本科 | 储能 | 500-999人 | — | [链接](https://www.zhipin.com/job_detail/066c6d435257c3230nNz0926ElZQ.html) |
| 上海 | 10-15K | Java开发工程师（AI应用开发） | 凯数 | 静安区 | 5-10年 | 本科 | 互联网 | 20-99人 | Java、Python、Spring、Docker、Kafka、MySQL、AI、后端开发 | [链接](https://www.zhipin.com/job_detail/5580d473ccffba390nBz2Nu4FVtT.html) |
| 杭州 | 20-30K·13薪 | AI应用开发 | 术也 | 西湖区 | 1-3年 | 本科 | 智能硬件 | 20-99人 | Python、MySQL | [链接](https://www.zhipin.com/job_detail/a81f4aabac547e820nx82t67F1VZ.html) |
| 杭州 | 18-26K | AI 应用开发工程师 | 梓晨 | 余杭区 | 3-5年 | 本科 | 家具/家居 | 500-999人 | — | [链接](https://www.zhipin.com/job_detail/ddbdcd9c0e82cc400nB90927FFNZ.html) |
| 杭州 | 18-30K | ai应用开发工程师 | 度小满金融 | 西湖区 | 3-5年 | 本科 | 互联网金融 | 1000-9999人 | Python、Selenium、MySQL、团队管理经验 | [链接](https://www.zhipin.com/job_detail/c21ef00aefcbfa0c0nx939W4ElZV.html) |
| 杭州 | 16-25K | ai应用开发工程师 | 海康威视 | 滨江区 | 3-5年 | 本科 | 计算机软件 | 10000人以上 | Python、Java、TensorFlow、MySQL、MongoDB | [链接](https://www.zhipin.com/job_detail/ef830cf6d16cb9d80nF92dS8FFJV.html) |
| 杭州 | 15-25K | AI Agent 工程师 | 风之末 | 萧山区 | 3-5年 | 本科 | 互联网 | 20-99人 | Scrapy、PyTorch、Docker、PostgreSQL、MySQL、Redis、Numpy、Python、Kubernetes | [链接](https://www.zhipin.com/job_detail/9a61680f5e87bf540nN60tq1FVVS.html) |
| 杭州 | 15-30K | AI Agent 开发工程师 | 中安智联 | 钱塘区 | 3-5年 | 本科 | 其他专业服务 | 0-20人 | Tool Calling、LangGraph、PostgreSQL、Pydantic、MCP、Linux开发/部署经验、Python、AI Agent | [链接](https://www.zhipin.com/job_detail/e447e6ddb9ac82730nx53964E1pT.html) |
| 杭州 | 15-25K | AI Agent平台工程师 | 杭州赛思泰克信息服务 | 拱墅区 | 3-5年 | 本科 | 咨询 | 20-99人 | agent质量评测 | [链接](https://www.zhipin.com/job_detail/4c66953b73aea1040nx90tu6GFBW.html) |
| 杭州 | 15-20K·13薪 | AI agent开发 | 浙江念妆品牌管理 | — | 1-3年 | 本科 | 日化 | 100-499人 | Python、Django、MySQL | [链接](https://www.zhipin.com/job_detail/7233c3a0536eecf60nx83t-_GFpX.html) |
| 杭州 | 15-20K | AI agent开发工程师 | 杭州玩点科技有限公司 | 西湖区 | 3-5年 | 本科 | 旅游 | 100-499人 | Java、Spring、SpringCloud、JVM、MySQL、Redis | [链接](https://www.zhipin.com/job_detail/fb756d60437718620nBy2tS-GVVQ.html) |
| 杭州 | 15-25K | 电商AI Agent 工程师 | 卿林科技 | 滨江区 | 1-3年 | 本科 | 电子商务 | 100-499人 | Python | [链接](https://www.zhipin.com/job_detail/a739b1a4bd0b69620nx-09W7E1dV.html) |
| 杭州 | 15-30K | AI Agent推广与开发工程师 | 腾展科技 | 西湖区 | 5-10年 | 本科 | 人工智能 | 100-499人 | Python、Golang、Java、TensorFlow、PyTorch、MySQL、机器学习经验、AI Agent | [链接](https://www.zhipin.com/job_detail/093a4b6bbb29e6af0nd43ty6FVpS.html) |
| 杭州 | 15-30K·14薪 | AI应用开发（python c/c++ java） | 深圳某大型ICT基础设施与智能终端上市公司 | — | 经验不限 | 本科 | 计算机软件 | 10000人以上 | C++、C、Java、Python、分布式经验 | [链接](https://www.zhipin.com/job_detail/b80bc2e78a5267a90nN53Ni-GFZQ.html) |
| 杭州 | 15-30K·13薪 | 高级 AI 应用开发工程师 | 枫清科技 | 西湖区 | 3-5年 | 本科 | 计算机软件 | 100-499人 | 分布式经验、Docker、PostgreSQL、MySQL、机器学习经验、Python | [链接](https://www.zhipin.com/job_detail/3325c9e2d0c650f70nx93dy6E1dZ.html) |
| 杭州 | 15-25K | AI 应用开发工程师（Agent） | 浙江海创运联网络科技 | 拱墅区 | 3-5年 | 本科 | 进出口贸易 | 100-499人 | Java、Python、Spring、SpringCloud、MySQL | [链接](https://www.zhipin.com/job_detail/30514e2a60c55a820nxy2tu7GVRX.html) |
| 杭州 | 15-30K·15薪 | AI 原生移动端应用开发工程师 | 杭州佳量脑科学 | 余杭区 | 5-10年 | 本科 | 医疗器械 | 100-499人 | — | [链接](https://www.zhipin.com/job_detail/1f85eecaadf987c50nF929W7FVBY.html) |
| 杭州 | 14-17K | AI agent开发 | 问顶科技 | 上城区 | 3-5年 | 本科 | 互联网 | 20-99人 | C++、C、MySQL、机器学习经验、Kafka、Spark、Python、Flask | [链接](https://www.zhipin.com/job_detail/32a0951493b7866c0nF93tu1FlFU.html) |
| 杭州 | 14-17K | AI Agent 开发工程师 | 智迅车联 | 余杭区 | 3-5年 | 本科 | 计算机软件 | 100-499人 | Java、Python、Spring、MySQL、爬虫经验、LLM应用开发经验、AI Agent应用 | [链接](https://www.zhipin.com/job_detail/acf134f9cbe921120nx639m_F1dR.html) |
| 杭州 | 12-24K·14薪 | ai agent | 上海万宝盛华信息科技 | 滨江区 | 经验不限 | 本科 | 人力资源服务 | 500-999人 | — | [链接](https://www.zhipin.com/job_detail/d4d7ef6918855c330nJ-09u7FFVV.html) |
| 杭州 | 12-15K·13薪 | ai agent工程师 | 杭州智能涌现人工... | 滨江区 | 3-5年 | 大专 | 人工智能 | 0-20人 | — | [链接](https://www.zhipin.com/job_detail/3811f0f834d42c500nR93dq9FlFZ.html) |
| 杭州 | 12-20K | AI应用开发【aigc应用】 | 杭州凌沫科技有限公司 | 拱墅区 | 3-5年 | 本科 | 计算机软件 | 20-99人 | 生图、生视频、aigc、comfyui | [链接](https://www.zhipin.com/job_detail/55113cdf65e6c4a50nNy2Ni7GFVQ.html) |
| 杭州 | 12-20K | AI 应用开发工程师 | 浙江实朴 | 萧山区 | 3-5年 | 本科 | 互联网 | 20-99人 | Python、Flask、Django、MySQL | [链接](https://www.zhipin.com/job_detail/b65a40d505e99b6f0nx40t64EFRR.html) |
| 杭州 | 12-20K·14薪 | AI应用开发工程师 | 亚信科技 | 西湖区 | 1-3年 | 本科 | 计算机软件 | 10000人以上 | Java | [链接](https://www.zhipin.com/job_detail/b5a9c33340ea449b0nN50t25EFtR.html) |
| 杭州 | 12-16K | ai应用开发工程师 | 浙江无央包装科技 | 钱塘区 | 3-5年 | 本科 | 文化艺术/娱乐 | 0-20人 | Docker、MySQL、运维开发经验、Redis、Linux开发/部署经验、Python | [链接](https://www.zhipin.com/job_detail/25057964662800580nd70tu_E1NU.html) |
| 杭州 | 11-15K | AI应用开发 （外包农夫山泉） | 盖硕网络 | 西湖区 | 5-10年 | 本科 | 互联网 | 100-499人 | 分布式经验、微服务经验、MySQL、Python、Flask | [链接](https://www.zhipin.com/job_detail/4d0cc766a7ac0cb00nF80tS0E1NU.html) |
| 杭州 | 10-15K | Ai agent | 杭州市滨江区萧尘... | 滨江区 | 1-3年 | 本科 | 人工智能 | 0-20人 | Python | [链接](https://www.zhipin.com/job_detail/37c1b2962bc548fb0nx-3d2_GVFV.html) |
| 杭州 | 10-15K | AI Agent 开发工程师 | 虾班人工智能 | 上城区 | 1-3年 | 本科 | 互联网 | 0-20人 | — | [链接](https://www.zhipin.com/job_detail/9ee7e5105775c4fb0nF62ti4EFpY.html) |

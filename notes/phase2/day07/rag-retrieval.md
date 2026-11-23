---
title: Day 7 · RAG 检索实测：chunk、embedding、top-k
date: 2026-11-23
day: 7
phase: 2
tags:
  - ai-agent-30d
  - rag
  - pgvector
  - embedding
status: done
---

# Day 7 · RAG 检索实测：chunk、embedding、top-k

## 学完后应能

- 说出一次检索前发生的三件事：切 chunk、逐块生成向量、连同文本入库；以及查询时的两件事：查询向量、按距离取 top-k。
- 解释 cosine distance 的数值含义，并用本日实测的 0.218 与 0.629 校准"相关 / 不相关"的区间手感。
- 指出 chunking 参数（size / overlap）如何决定检索单元，以及 size 过大或过小的具体后果。
- 说明 pgvector 侧的三层配置：扩展、带维度列的表、HNSW 索引；以及"重复运行不残留"由谁保证。

主产出是 [pgvector_demo.py](../../../phase2/day07/pgvector_demo.py)，切分实现在 [chunking.py](../../../phase2/day07/chunking.py)，数据库由 [compose.yaml](../../../phase2/day07/compose.yaml) 在 VMware 虚拟机中提供。本文引用的数据全部来自检索日志 [retrieval-example.json](../../../phase2/day07/logs/retrieval-example.json)——仓库保留的唯一实证，后续日志不入库；数字以它为准。

## 1. 全流程：入库与查询各发生什么

```mermaid
sequenceDiagram
    participant App as pgvector_demo
    participant Emb as Embedding API
    participant DB as pgvector (VM)
    Note over App,DB: 入库阶段（每次运行都执行）
    App->>App: chunk_text 按 size/overlap 切分
    App->>Emb: POST /embeddings，全部 chunks 一次请求
    Emb-->>App: 每个 chunk 一个向量
    App->>DB: 建扩展/表/HNSW 索引，按 source 删旧，插入
    Note over App,DB: 查询阶段
    App->>Emb: 查询句单独请求一次
    Emb-->>App: 查询向量
    App->>DB: ORDER BY embedding <=> query LIMIT 3
    DB-->>App: source, chunk_index, content, distance
```

入库与查询都必须经过同一个 embedding 模型：向量是模型对文本的表示，换了模型，新旧向量不在同一个空间里，算出的距离没有意义。日志里 `embedding_model` 与 `embedding_dimensions` 记录的正是这个前提。

## 2. chunk：size 与 overlap 决定检索单元

本日两篇文档各约 100 字符，`chunk_text(text, size=120, overlap=20)` 各产出 1 块——文本不足一个窗口，overlap 没有实际生效。日志 `chunks` 数组里的两条记录就是全部入库单元。

`chunking.py` 的断言钉住了四个边界，每个都对应一种真实文档会遇到的形状：

- 恰好等于窗口长度：只产出一个 chunk，尾块不重扫
- overlap=1、size=3 时切出 `abc/cde/efg`：下一个起点 = 本窗口终点 − overlap，相邻块共享 1 字符
- overlap=0 退化为普通固定窗口，尾部不足整窗也成块（不跳过字符）
- `overlap == size` 非法：步长为 0，循环永远推进不了，死循环

size 与 overlap 的取舍是本日的核心权衡。窗口过大时，一个 chunk 混入多个主题，检索命中的是"沾边的大块"，送进模型的上下文噪声多、token 贵；过小时句子和指代被切断——"它"指的是哪个商品，答案在上一个 chunk 里。overlap 是对窗口边界的补偿：相邻块共享 overlap 字符，跨边界的句子至少在一个块里是完整的，代价是存储重复与可能的重复召回。

本日两篇文档都短，这些差异体现不出来。阶段 5 ingestion 真实文档（几百到几千字）时，chunk 参数是要在 ADR 里定的决策，不是随手写死的常量。

## 3. embedding 与距离：0.218 与 0.629

日志的检索结果，模型 `BAAI/bge-large-zh-v1.5`，1024 维：

| 命中 | distance | 内容 | 判断 |
|---|---|---|---|
| shipping.md#0 | 0.2181 | 发货后在订单详情页查看物流，顺丰单号以 SF 开头 | 相关 |
| returns.md#0 | 0.6289 | 七天无理由退货、生鲜与个人护理除外 | 不相关 |

查询是"订单已经发货，在哪里查顺丰物流单号？"。cosine distance = 1 − 余弦相似度，越小越近。这组数字给出了一个可迁移的校准点：**同一模型下，0.2 量级是语义相关，0.6 量级是无关**。阶段 5 做相似度阈值过滤时（distance 高于阈值的结果不进上下文），这个区间就是起点——比如取 0.5，会滤掉 returns 这条、保留 shipping 这条。

两点边界要记住。其一，distance 是模型空间里的相似度信号，不是答案正确性的概率——查询"退货流程"与退货文档的 distance 也会是 0.2 左右，但内容可能是错的版本。其二，这两个数字绑定当前模型；换 embedding 模型后区间整体平移，校准要重做。日志里记录模型名与维度，就是为了在数字失效时能溯源。

## 4. pgvector 侧的三层配置

demo 在数据库里按顺序建了三层，缺一层都会在特定环节失败：

1. **扩展**：`CREATE EXTENSION IF NOT EXISTS vector`。compose 用的镜像 `pgvector/pgvector:pg17` 自带扩展二进制；换成官方 `postgres:17` 镜像，这一步直接报 `extension "vector" is not available`。VM 里旧的 postgres:18 容器就是这个原因无法用于本日练习。
2. **表**：`embedding vector(1024)` 列的维度写死为当批向量的维度。与模型维度不一致时 INSERT 报错。换 embedding 模型（维度变了）不会自动改列——阶段 5 的 schema 决策之一是"维度变更等于重建表"。
3. **索引**：`USING hnsw (embedding vector_cosine_ops)`。HNSW 是近似最近邻索引，查询不再逐行精确比较，换来大数据量下的查询速度；建索引本身消耗更多内存与时间。小数据量下没有它也一样跑（顺序扫描），它的价值在量级上去之后。

查询里的 `<=>` 是 cosine distance 运算符，`ORDER BY ... <=> ... LIMIT 3` 按距离升序取前 k。结果不足 k 条时返回全部——本日库里只有 2 条，top_k=3 返回 2 条，不报错。

"重复运行不残留"由 `store_chunks` 按 source 先删后插保证：两次运行之间数据库状态一致，验收时连续跑两次输出不翻倍。它是 demo 层面的幂等（按 source 全删），不是生产策略——真实 ingestion 不能全删重灌，增删改要按内容寻址。

## 5. 环境与运行

```text
虚拟机（VMware，SSH 连接）        宿主机（Windows）
┌─────────────────────────┐      ┌──────────────────────┐
│ docker compose up -d     │      │ uv run -m             │
│ pgvector/pgvector:pg17   │◄─────│ phase2.day07.         │
│ 端口 5432 → 宿主机        │ 5432 │ pgvector_demo         │
│ 卷 devops_pgvector_data  │      │ 环境变量三件套          │
└─────────────────────────┘      └──────────────────────┘
```

Docker 在虚拟机里，Python 在宿主机，中间走虚拟机的 5432 端口。compose 文件在虚拟机家目录（`~/compose.yaml`，从仓库 `phase2/day07/compose.yaml` 复制过去），宿主机侧需要三个环境变量：

```powershell
$env:PGVECTOR_DSN = "postgresql://agent:123456@192.168.2.21:5432/rag_lab"
$env:EMBEDDING_BASE_URL = "..."   # 兼容 OpenAI /embeddings 格式的服务
$env:EMBEDDING_MODEL = "BAAI/bge-large-zh-v1.5"
```

环境变量只对当前终端窗口生效，重开终端要重设。DSN 四段（用户、密码、主机、库名）与 compose.yaml 的 `POSTGRES_USER / POSTGRES_PASSWORD / ports / POSTGRES_DB` 一一对应。

## 6. RAG 特有的问题与定位

按检索链路的顺序，记 embedding 与向量库两侧会出的问题。环境类问题（容器未 healthy、DSN 密码不一致）是部署问题，查 compose 与 DSN 对应关系即可，不在此列。

**`extension "vector" is not available`**——镜像选错。`CREATE EXTENSION vector` 要求镜像自带扩展二进制，官方 `postgres:17/18` 镜像没有。RAG 用的镜像必须是 `pgvector/pgvector:pg17` 这一类。

**`embedding` 响应维度与表不匹配**——换了 `EMBEDDING_MODEL` 但表还是旧维度建的。pgvector 的 `vector(N)` 列在建表时锁定维度，模型换了维度就变，INSERT 直接失败。demo 的处理是手动 `DROP TABLE rag_chunks` 重跑；阶段 5 的 schema 设计要把它变成明确规则：维度变更等于重建表，新旧向量不可混存——不同模型的向量不在同一空间，即使维度巧合相同，算出的距离也没有意义。

**`同一批 embedding 的向量维度不一致` / `index 不完整或重复`**——embedding 服务返回的 data 数组与输入不对齐：条目数不符、index 缺失或乱序。demo 在拿到响应后先校验 index 序列完整、按 index 排序后再使用，坏的响应在入库前就失败。这一层校验来自对服务响应不可信的假设——与 Day 6 对模型输出不可信的处理是同一个原则：外部输入先校验形状再进数据。

**检索结果全不相关（distance 全在 0.6 以上）**——两个来源最常见。其一，入库与查询用了不同模型或同一模型的不同版本，向量不在同一空间；日志里的 `embedding_model` 就是为核对这一项。其二，chunk 太碎，语义被切断，任何 chunk 都不完整地表达一个主题——回到第 2 节的 size/overlap 权衡，调参数后重建表重灌。

**检索结果相关但内容被截断**——chunk 在句子中间被切开，top-1 命中的是半句话。overlap 的设计动机就是这里：相邻块共享 overlap 字符，被切断的句子至少在一个块里是完整的。另一种修法是按结构切（标题、段落边界），阶段 5 的 ingestion 再实现。

**top-k 返回了不相关的块**——k 太大或没有阈值过滤。LIMIT k 只保证数量，不保证质量；库里候选不足时会把不相关的也凑进来（本日库里只有 2 条，top_k=3 返回 2 条）。阶段 5 的检索服务要加相似度阈值：distance 超过阈值的不进上下文，校准起点是本日实测的 0.2 相关 / 0.6 不相关。

## 遗留与预告

rerank 在 README 提到但本日未实现：它是检索后的第二道筛，用更精细的模型对 top-k 重排，与向量库的距离排序是两回事。阶段 5 的检索服务会加这一层。Day 8 把 embedding、chunk、rerank 串成完整的 RAG 链路白板图，并回答"为什么 MCP 在 function calling 之上"。

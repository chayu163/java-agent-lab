---
title: Day 5 · 工具调用循环：模型提议，程序执行
date: 2026-11-19
day: 5
phase: 1
tags:
  - ai-agent-30d
  - agent-loop
  - tool-calling
status: done
---

# Day 5 · 工具调用循环：模型提议，程序执行

## 学完后应能

- 画出 assistant 工具请求、工具执行结果和下一轮模型输入的消息顺序。
- 解释工具注册表、参数解析、错误回填和步数上限各自负责什么。
- 说明并发执行策略的前提，以及当前实现的执行顺序边界。

主产出是 [mini_loop.py](../../../phase1/day05/python/mini_loop.py)。消息协议与装饰器注册分别由 [01_messages.py](../../../phase1/day05/python/01_messages.py) 和 [02_registry.py](../../../phase1/day05/python/02_registry.py) 独立演示。

## 1. 这个练习里的 Agent loop

“Agent”没有唯一的行业定义。本练习把它限定为一个工具调用循环：模型读取当前消息，提出工具调用或给出答案；程序负责执行工具、回填结果并判断是否继续。

```mermaid
sequenceDiagram
    actor User as 用户
    participant Loop as run_agent
    participant Model as 假模型
    participant Tool as 工具
    User->>Loop: 问题
    loop 最多 max_steps 轮
        Loop->>Model: 当前完整 history
        alt 响应包含 tool_calls
            Model-->>Loop: assistant 请求(call_1, call_2)
            Loop->>Tool: 按注册表执行每个调用
            Tool-->>Loop: role=tool，分别携带 call_id
            Loop->>Loop: 追加 assistant 响应与工具结果
        else 没有 tool_calls
            Model-->>Loop: assistant 最终回答
            Loop-->>User: 返回回答
        end
    end
    Note over Loop: 无 tool_calls 时立即返回；最后一轮仍要求工具时会在执行后抛 MaxStepsExceeded
```

本练习每次调用假模型时都传入完整历史。模型调用函数本身不保存跨请求记忆；调用方通过提交消息列表提供对话上下文。代码复制 `messages` 的外层列表到 `history`，循环只向 `history` 追加响应和工具结果。

## 2. 工具请求与结果如何配对

一个兼容 OpenAI 工具调用形状的项目示例：

```json
{
  "id": "call_1",
  "type": "function",
  "function": {
    "name": "query_order",
    "arguments": "{\"order_id\": \"A1001\"}"
  }
}
```

`arguments` 是 JSON 字符串。程序先解析，再用工具名查允许调用的注册表。JSON 能成功解析只说明语法正确，不代表字段、类型或业务规则已经验证。

每次工具响应使用 `role: "tool"`，并携带对应的 `tool_call_id`。一次 assistant 响应可以包含多个工具调用，每个调用都需要有自己的回填消息。响应的 `content` 与 `tool_calls` 在不同协议中可能同时存在或采用不同约束；本练习的 helper 为简化只构造其中一种形态。

## 3. 注册表是允许调用范围

工具表把模型可请求的名称映射到本地函数。分发表的白名单限制了可执行范围：模型返回的任意名称都不能直接当作模块属性访问。

`02_registry.py` 使用带参数的 `@tool` 装饰器登记函数与 schema。主产出 `mini_loop.py` 则直接维护 `TOOLS` 字典，用于聚焦循环本身；它不调用 `@tool`，也没有从注册表练习导入实现。

工具边界仍需要输入校验。当前循环把解析后的字典用 `fn(**arguments)` 展开，缺少参数、参数名错误或类型不匹配会触发异常。生产实现应使用 schema 校验或明确的参数模型，不能把模型生成的 JSON 直接视为可信输入。

## 4. 执行、错误与顺序

当前 `execute_calls` 将已登记的只读工具交给 `asyncio.gather` 并发执行，再按模型原始调用位置放回结果列表；写工具和未知工具在后续串行处理。未知工具由 `invoke` 转成带错误内容的 `tool` 消息，因此仍满足每个请求都有回填。

`gather` 的结果顺序与输入顺序相同，但这只是结果顺序，不是执行顺序。实现先执行只读组、再执行写入组；若同一响应里既有读又有写，代码不会保留两类调用之间的原始执行顺序。因此当前策略只适合彼此独立的只读操作和不会依赖其相对顺序的写操作。

“只读并发、写操作串行”是此练习选择的简化策略，不是所有工具系统都适用的规则。实际分类需要考虑副作用、幂等性、数据依赖、事务和人工审批。

工具执行异常会被转换成 `{"ok": false, ...}` 并作为工具结果回填，让循环可以继续。`except Exception` 不会捕获 Python 3.11 的 `asyncio.CancelledError`，因为取消信号继承自 `BaseException`。取消应继续传播，必要清理放在 `finally`。

## 5. 历史与终止条件

`run_agent` 每轮先把模型响应加入 `history`，再执行和回填工具，下一轮调用模型时传入更新后的 `history`。测试会确认第二轮看到 `role: "tool"` 和正确的 `tool_call_id`，并确认输入列表没有被循环追加。

无 `tool_calls` 时，本练习把响应视为最终答案。真实 API 还会提供 finish reason 等状态；达到 token 上限、内容过滤等情况不能当成正常答案处理，Day 6 会接入协议级判断。

`max_steps` 限制模型响应轮数。若最后允许的一轮仍返回工具调用，程序执行并回填工具后已经耗尽轮数，无法再请求模型生成最终答案，于是抛出 `MaxStepsExceeded`。因此配置上限时，要为“工具请求之后的总结响应”预留一轮。

## 6. 假模型与真实 API 的接口边界

本练习的 `Model` 是同步函数，立即从脚本中取出预设响应。它让循环能离线、无费用地测试。真实模型 API 通常通过异步 HTTP 请求调用，不能只把 `scripted_model` 替换成 `async def` 而保持循环不变；接口需要改为 await 模型请求，错误处理也要覆盖传输和协议层。

循环数据流和消息配对规则可以复用，模型适配器与结束条件需要按 API 协议实现。这正是 Day 6 从假模型走向真实兼容 API 时要验证的部分。

## 7. 验收测试验证什么

运行：

```bash
uv run phase1/day05/python/mini_loop.py
```

主脚本验证五条路径：

1. 单工具调用后返回答案。
2. 第二轮模型请求包含第一轮工具回填。
3. 独立只读工具并发执行，结果仍按调用 id 排列。
4. 未知工具得到错误回填，循环继续。
5. 模型持续请求工具时达到 `max_steps` 并停止。

并发测试使用任务耗时作为粗略验证。它适合确认示例实现是否真的重叠等待，不是稳定的性能基准；机器负载会影响具体毫秒数。

## Java 对照

可以把消息列表看成一次请求携带的上下文，把工具注册表看成白名单分发表，把 `max_steps` 看成循环的资源上限。但这不是传统业务状态机的同构模型：下一步由模型输出提出，程序仍需验证该提议并决定是否执行。

## 自测

- 为什么第二轮模型请求必须包括 assistant 工具请求和工具结果？
- `tool_call_id` 解决什么问题？一个响应有多个调用时要回填几条消息？
- JSON 解析成功能否证明参数合法？还需要哪些校验？
- `gather` 保证结果顺序，是否意味着工具按同一顺序执行？
- 当前实现混合读写调用时采用什么执行顺序？适用前提是什么？
- `max_steps=1` 时，若第一轮请求工具，程序能否再请求模型总结？
- 为什么真实异步模型 API 不能直接替换同步的 `scripted_model`？

## 阶段 1 回顾

Day 1 的对象与类型、Day 2 的函数和值、Day 3 的异步等待、Day 4 的替身测试，在今天组成了一个可离线验证的循环。进入 Day 6 后，需将同步假模型改为真实异步请求，并按实际协议处理响应状态。

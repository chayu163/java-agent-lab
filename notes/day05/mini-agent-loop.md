---
title: Day 5 · mini agent loop
date: 2026-11-19
day: 5
phase: 1
tags:
  - ai-agent-30d
  - agent-loop
  - tool-calling
status: done
---

# Day 5 · mini agent loop

> [!abstract] 今日产出
> - `day05/python/01_messages.py`：消息协议的构造与配对
> - `day05/python/02_registry.py`：工具注册表与 `@tool` 装饰器
> - `day05/python/mini_loop.py`：完整循环（主产出）
> - 本篇笔记

> [!tip] 一句话总结
> 模型只输出「下一步做什么」；执行动作、回填结果、判断终止，全部在你的程序里。这二十行循环就是 Agent 与普通 LLM 应用的全部差别。

---

## 一、循环图解

一次完整的对话经历「请求 → 判断 → 执行 → 回填」，直到模型不再要求调用工具。以「A1001 到哪了」为例，共两轮：

```text
 ┌─────────────────────────────────────────────────────┐
 │ messages 列表（模型的全部记忆）                       │
 │                                                     │
 │  [system]  你是电商售后助手…                         │
 │  [user]    A1001 到哪了？                            │
 └──────────────────────┬──────────────────────────────┘
                        │
             ① 请求 model(messages)
                        ▼
 ┌─────────────────────────────────────────────────────┐
 │ ② assistant 响应                                     │
 │    content: null                                    │
 │    tool_calls:                                      │
 │      call_1 → query_order(A1001)      ┐             │
 │      call_2 → get_logistics(A1001)    │ 有 tool_calls│
 └───────────────────────────────────────┼─────────────┘
                                         │
                        ③ 路由：名字 → 注册表里的函数
                                         │
                    ┌────────────────────┴──────────────────┐
                    │  ④ 执行（按副作用分组）                 │
                    │                                       │
                    │   只读 query_order ──┐                 │
                    │                     ├─ gather 并发     │
                    │   只读 get_logistics┘   （同时等待）     │
                    │                                       │
                    │   写操作 create_ticket → 依次执行       │
                    └────────────────────┬──────────────────┘
                                         │
                        ⑤ 回填 tool 消息（tool_call_id 配对）
                                         ▼
 ┌─────────────────────────────────────────────────────┐
 │ messages 变长了：                                    │
 │  [system] [user]                                    │
 │  [assistant + tool_calls]      ← 第一轮的响应         │
 │  [tool call_1] {"ok":true, data:…}  ← 执行结果       │
 │  [tool call_2] {"ok":true, data:…}                  │
 └──────────────────────┬──────────────────────────────┘
                        │
             再次请求 model(messages)
                        ▼
 ┌─────────────────────────────────────────────────────┐
 │ assistant 响应：                                     │
 │    content: "已发货，顺丰 SF1234567890"               │
 │    tool_calls: 无        → ⑥ 循环结束，返回答案       │
 └─────────────────────────────────────────────────────┘
```

三个要点：

1. **模型的记忆 = messages 列表。** 每一轮都把完整列表重新提交，模型本身无状态。
2. **判断终止的依据只有一条：响应里有没有 `tool_calls`。** 有就执行，没有就结束。
3. **回填靠 `tool_call_id` 配对。** 多个工具并发执行、完成顺序不定，`gather` 保序交付让回填顺序与请求顺序一致。

---

## 二、协议：四种角色与一次配对

| role | 谁写的 | 关键字段 |
|---|---|---|
| `system` | 你的程序 | 定角色与约束 |
| `user` | 用户 | 本次请求 |
| `assistant` | 模型 | `content` 或 `tool_calls`，互斥 |
| `tool` | 你的程序 | `tool_call_id`、`content` |

两个练习里验证过的细节：

- **`arguments` 是字符串。** 模型生成的是文本，必须 `json.loads` 之后才能展开成关键字参数。解析失败要回填而不是抛异常。
- **`tool_call_id` 是唯一线索。** 一次请求多个 `tool_calls` 时，模型靠这个字段把每条结果归位。写错或漏写，下一轮模型看到的就是一段没有归属的输出。

---

## 三、注册表：一张表决定两件事

```python
TOOLS = {"query_order": query_order, "get_logistics": get_logistics, …}
SCHEMAS = {"query_order": {"description": …, "parameters": …}, …}
```

- 模型**能看到**哪些工具：发给模型的 `tools` 数组由 `SCHEMAS` 生成
- 名字**解析到**哪个函数：循环里的路由查 `TOOLS`

一处维护，两处生效。工具增删时只改一个装饰器调用。

`@tool` 装饰器是 Day 2 带参数装饰器的直接应用：三层结构，`tool(...)` 返回 `decorator`，`decorator` 把函数登记进两张表后原样返回。

> [!danger] 路由必须是白名单
> `TOOLS.get(name)`，表里没有就报 `UnknownTool`。
> 不写 `getattr(module, name)`——那等于让模型可以调用模块里的任意函数。

---

## 四、执行策略：按副作用分组

模型一次可能返回多个 `tool_calls`。全部串行浪费等待时间，全部并发可能撞车。分组依据只有一个问题：**这个工具改变状态吗？**

| 类别 | 本例 | 执行方式 | 理由 |
|---|---|---|---|
| 只读 | `query_order`、`get_logistics` | `asyncio.gather` 并发 | 相互独立，重叠等待不改变结果 |
| 写 | `create_ticket` | 依次执行 | 顺序影响状态；阶段 5 还要加人工确认 |
| 未知 | 不在表内的名字 | 走串行路径，`invoke` 回填错误 | 必须回填，否则模型下一轮重复同一个请求 |

`execute_calls` 的实现模式：先按原顺序给每个 call 编号，只读的并发跑完按编号放回，写操作按编号依次执行放回。`gather` 保序 + 按索引回填 = 模型看到的顺序与请求一致。

实测数据：两个各睡 50ms 的只读工具，并发执行总耗时约 60ms，串行需要 100ms 以上。

---

## 五、错误处理：工具报错是信息，不是异常

`invoke` 把所有失败转成正常消息：

```python
try:
    fn = TOOLS.get(name)
    if fn is None:
        raise UnknownTool(f"未知工具: {name}")
    arguments = json.loads(call["function"]["arguments"])
    payload = await fn(**arguments)
    content = json.dumps({"ok": True, "data": payload}, ensure_ascii=False)
except Exception as exc:
    content = json.dumps({"ok": False, "error": f"{type(exc).__name__}: {exc}"}, …)
```

理由：模型看到「订单不存在」后会调整下一步，这是循环能处理的信息；抛异常则整轮对话终止。验收里的未知工具场景证明了这一点——`refund` 报错回填后，模型给出「已转人工处理」的答案，而不是崩溃。

唯一的例外是 `CancelledError`：它继承自 `BaseException`，`except Exception` 抓不到它，取消必须向上传播。这是 3.8+ 有意的设计，防止普通异常处理吞掉取消信号。

---

## 六、终止：一条正常路径，一条保底

**正常结束**：响应没有 `tool_calls`，`content` 就是答案。

**保底**：`max_steps`。模型完全可能反复请求同一个工具；没有上限时循环持续消耗 token 与工具配额，而调用方看不到任何进展。验收用脚本模拟了连续 10 次请求同一工具的场景，`max_steps=3` 时正确抛出 `MaxStepsExceeded`。

> [!danger] 没有步数上限的循环不是 Agent，是事故

---

## 七、批改实录

三个文件中暴露的问题，按严重程度排列：

### 1. 对字典做多项解包，取到的是键（练习 2）

```python
description, parameters = schema    # schema 是 dict
# 实际得到 description == "description"、parameters == "parameters"
```

对字典解包迭代的是**键**。工具的说明与参数约束全部丢失，模型收到一份无意义的 schema。改成 `{"name": name, **schema}` 按键展开。

### 2. 断言只查键存在，没查值（练习 2）

```python
assert "parameters" in schemas[0]["function"]   # 值变成字符串也能通过
```

上面那个错误因此完整通过了验收。修正后的断言落到具体值：`description` 是那句话、`required` 是那个列表。**断言要落到值上，不能停在结构上。**

### 3. 误导入第三方内部模块（练习 2 与主产出，共四处）

```python
from mypy.checkexpr import TooManyUnions
from ast import mod
from unittest import async_case
from urllib import response
```

IDE 自动补全带入。危害不只是多一行：mypy 是 dev 依赖，生产环境会直接 `ImportError`。`ruff` 的 `F401`（未使用导入）就是拦这类问题的。

### 4. 复制了 `messages` 却仍然追加原列表（主产出）

```python
history = list(messages)      # 复制了一份
history.append(response)      # ✅
messages.extend(calls_results) # ❌ 追加到了调用方的列表上
```

复制了 `history` 却把工具结果追加到原 `messages` 上，调用方持有的列表被污染，`RunResult.messages` 与 `history` 也不一致。docstring 里写了「传入的 messages 不被修改」，实现与注释矛盾。改为统一操作 `history`。

### 5. `zip` 缺 `strict` 参数（主产出）

`zip(read_items, read_results)` 在两个序列长度不一致时静默截断。加 `strict=True` 让长度不匹配直接抛 `ValueError`——这里两边的长度必须相等，不等就是 bug，宁可报错也不静默。

### 6. 缩进混用（主产出）

`run_agent` 循环体用了 3 空格缩进，其余部分是 4 空格。Python 允许同一个块内统一即可，但两个块缩进不同风格时 `ruff format` 会重排。已统一为 4 空格。

---

## 八、阶段 1 收尾

计划给阶段 1 的两条总验收：

- **不看教程手写 `asyncio.gather` 并发调用**：Day 3 达成，Day 5 在 `execute_calls` 里再应用了一次（只读并发 + 保序回填）。
- **Python 默认参数与 Java 默认参数的区别**：Python 的默认值在 `def` 执行时求值一次，可变对象被函数对象长期持有（Day 1 坑 1）；Java 不给参数默认值，只能重载。

阶段 1 的产出清单：

| 天 | 主题 | 主产出 |
|---|---|---|
| 1 | Java→Python 迁跃 | 订单状态机（批注版 + bean 版） |
| 2 | 函数是一等公民 | Pydantic Tool schema |
| 3 | asyncio | httpx 并发调 5 个 API |
| 4 | pytest | 给 Day 3 代码写的 5 个测试 |
| 5 | mini agent loop | 完整循环（不接真实模型） |

> [!note] 与阶段 2 的衔接
> 今天的循环是 Day 6 的骨架。差别只有一处：`scripted_model` 换成真实 API 调用，`tools` 数组里填上 Day 2 用 Pydantic 生成的 schema。协议、注册表、执行策略、终止条件全部复用。

> [!tip] 面试可用的一句话
> 「Agent 循环本身只有二十行；复杂度在上下文构造、工具注册表和终止条件三处。我实现过完整的循环，包括只读工具并发、错误回填让模型自行修正、以及步数上限防止死循环。」

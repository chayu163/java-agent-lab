# Day 9 · `agent.run(prompt)` 之后，谁在循环？

打开 `main.py`，用户交给程序的是一个目标：「核对订单 A、B，写一段交接摘要。」入口只调用一次 `agent.run(prompt)`，却没有规定先查 A 还是先查 B。**Agent 和普通的一次模型请求，区别就在这层循环**：程序保存上一步的结果，根据当前状态决定要不要再让模型选一次动作。

## 第一次读，只跟住同一个对象

[默认入口](https://github.com/FoundationAgents/OpenManus/blob/99eea8e/main.py#L16-L32)先 `await Manus.create()`，再取用户输入，最后在 `finally` 中清理资源。`Manus` 决定这个实例有哪些工具、最多做多少步。但在 `Manus` 类里搜索 `def run`，反而找不到入口调用的方法。原因不是另有一个 Agent 接手，而是这个实例使用了父类的方法。

先读 [摘抄 1：`run` 的委托与循环](01_run.md)。从 Java 的模板方法理解：父类写好循环，子类提供每一步的行为。这里多了一层容易漏掉的委托：先进入 `ToolCallAgent.run`，由它负责退出时清理；`super().run` 才进入 `BaseAgent.run`，把非空请求写成用户消息，然后计步。两处的 `self` 都是起初创建的那个 `Manus`，不是两个对象。

再读 [摘抄 2：一次 `step` 的决策](02_step.md)。`BaseAgent` 决定**是否还有下一步**；`ReActAgent.step` 决定**这一步要不要行动**。`think()` 返回假，只代表这次 `step()` 不进 `act()`。如果把一句 “no action needed” 理解为整个任务已经结束，就看错了 `return` 的作用范围：接收这个字符串的是外层循环，不是用户。

## 从行为反查文件

| 要改变的行为 | 应先看哪里 | 原因 |
|---|---|---|
| 给默认 Agent 换一组工具或调整步数上限 | `app/agent/manus.py` | 这是实例的配置；循环条件读取的是 `self.max_steps`。 |
| 改成某种状态下不再继续 | `app/agent/base.py` | 能否进入下一步由 `run` 的循环条件决定。 |
| 改模型能看见的描述，或工具结果怎样进入历史 | `app/agent/toolcall.py`、`app/tool/tool_collection.py` | 模型请求和工具分发发生在一步之内，不在 CLI 中。 |

## Phase 3 阅读顺序

[Day 10：一次回复里的两次工具调用](../day10/README.md) → [Day 11：计划步骤与 Agent 步骤](../day11/README.md) → [Day 12：工具返回与资源状态](../day12/README.md) → [Day 13：从执行记录判断任务是否完成](../day13/README.md)。订单是贯穿五天的说明用例，不是内置工具。摘抄固定到上游 `99eea8e`，对应本地 `e4ac21a` 的实现；不需要运行模型或配置密钥。

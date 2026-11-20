"""Day 5 产出：mini agent loop。

模型抽象成 ``model(messages) -> response``。本文件用脚本化的假模型驱动循环，
接入真实 API 时只替换这一个函数，循环本身不改动。

五个动作：请求 -> 解析 -> 路由 -> 执行 -> 回填 -> 判断终止。

运行：uv run phase1/day05/python/mini_loop.py
"""

import asyncio
import json
from collections.abc import Callable
from dataclasses import dataclass
from typing import Any

Message = dict[str, Any]
Response = dict[str, Any]
Model = Callable[[list[Message]], Response]
ToolFn = Callable[..., Any]


# ---------------------------------------------------------------------------
# 数据与工具实现
# ---------------------------------------------------------------------------

ORDERS: dict[str, dict[str, Any]] = {
    "A1001": {"status": "已发货", "carrier": "顺丰", "tracking": "SF1234567890"},
    "A1002": {"status": "待付款"},
}

TICKETS: list[dict[str, Any]] = []


async def query_order(order_id: str) -> dict[str, Any]:
    await asyncio.sleep(0.05)
    order = ORDERS.get(order_id)
    if order is None:
        raise KeyError(f"订单不存在: {order_id}")
    return {"order_id": order_id, "status": order["status"]}


async def get_logistics(order_id: str) -> dict[str, Any]:
    await asyncio.sleep(0.05)
    order = ORDERS.get(order_id)
    if order is None:
        raise KeyError(f"订单不存在: {order_id}")
    if "tracking" not in order:
        return {"order_id": order_id, "logistics": "尚未发货"}
    return {
        "order_id": order_id,
        "carrier": order["carrier"],
        "tracking": order["tracking"],
    }


async def create_ticket(order_id: str, reason: str) -> dict[str, Any]:
    await asyncio.sleep(0.05)
    ticket = {"ticket_id": f"T{len(TICKETS) + 1:04d}", "order_id": order_id, "reason": reason}
    TICKETS.append(ticket)
    return ticket


TOOLS: dict[str, ToolFn] = {
    "query_order": query_order,
    "get_logistics": get_logistics,
    "create_ticket": create_ticket,
}

# 本练习并发执行只读工具，并按调用顺序串行执行写工具。
READ_ONLY = {"query_order", "get_logistics"}
WRITE = {"create_ticket"}


class AgentError(Exception):
    """循环层面的错误。"""


class MaxStepsExceeded(AgentError):
    """达到步数上限仍未结束。"""


class UnknownTool(AgentError):
    """请求的工具不在注册表内。"""


# ---------------------------------------------------------------------------
# 消息构造
# ---------------------------------------------------------------------------


def assistant_call(call_id: str, name: str, **arguments: Any) -> Response:
    """构造"要求调用工具"的 assistant 消息。"""
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
        ],
    }


def assistant_multi_call(calls: list[tuple[str, str, dict[str, Any]]]) -> Response:
    """构造一次返回多个 tool_calls 的 assistant 消息。

    calls 的每一项是 (call_id, 工具名, 参数字典)。
    """
    return {
        "role": "assistant",
        "content": None,
        "tool_calls": [
            {
                "id": call_id,
                "type": "function",
                "function": {
                    "name": name,
                    "arguments": json.dumps(arguments, ensure_ascii=False),
                },
            }
            for call_id, name, arguments in calls
        ],
    }


def assistant_answer(text: str) -> Response:
    return {"role": "assistant", "content": text}


def start_messages(question: str) -> list[Message]:
    return [
        {
            "role": "system",
            "content": "你是电商售后助手。查询类信息必须先调用工具获取，不要凭空回答。",
        },
        {"role": "user", "content": question},
    ]


def scripted_model(script: list[Response]) -> Model:
    """按顺序回放预设响应，脚本用尽后返回终止响应。

    模型这一层被抽象成计划性的函数，循环才能在不联网、不计费的前提下
    被完整测试。接入真实 API 时，替换的是这个函数，循环不感知差异。
    """
    pending = list(script)

    def call(messages: list[Message]) -> Response:
        if pending:
            return pending.pop(0)
        return assistant_answer("脚本已用尽")

    return call


# ---------------------------------------------------------------------------
# 循环
# ---------------------------------------------------------------------------


@dataclass
class Step:
    """一轮迭代的记录：模型要求了什么，工具返回了什么。"""

    index: int
    calls: list[dict[str, Any]]
    results: list[Message]


@dataclass
class RunResult:
    answer: str
    messages: list[Message]
    steps: list[Step]
    stopped_by: str


async def invoke(call: dict[str, Any]) -> Message:
    """执行单个 tool_call，返回回填用的 tool 消息。

    任何失败都转成正常消息而不是抛出：工具报错是循环可以处理的信息，
    模型看到"订单不存在"后会调整下一步，而抛异常会直接终止整轮对话。
    唯一不捕获的是 CancelledError——它属于 BaseException，取消必须向上传播。
    """
    call_id = call["id"]
    name = call["function"]["name"]

    try:
        fn = TOOLS.get(name)
        if fn is None:
            raise UnknownTool(f"未知工具: {name}")
        arguments = json.loads(call["function"]["arguments"])
        payload = await fn(**arguments)
        content = json.dumps({"ok": True, "data": payload}, ensure_ascii=False)
    except Exception as exc:
        content = json.dumps(
            {"ok": False, "error": f"{type(exc).__name__}: {exc}"},
            ensure_ascii=False,
        )

    return {"role": "tool", "tool_call_id": call_id, "content": content}


async def execute_calls(calls: list[dict[str, Any]]) -> list[Message]:
    """执行一批 tool_calls，返回与 calls 顺序一致的 tool 消息。

    只读工具用 asyncio.gather 并发，写工具依次执行。分组的依据是副作用：
    只读请求之间没有依赖，重叠等待时间不改变结果；写请求的顺序影响状态。
    gather 保序，因此能按原顺序回填，模型看到的 call_id 与结果一一对应。

    未知工具名不在任何一组，但同样要回填：交给 invoke 生成错误消息即可，
    否则模型的这次请求得不到任何回应，下一轮会重复同一个错误。
    """
    results: list[Message | None] = [None] * len(calls)
    read_items: list[tuple[int, dict[str, Any]]] = []
    write_items: list[tuple[int, dict[str, Any]]] = []
    for index, call in enumerate(calls):
        name = call["function"]["name"]

        if name in READ_ONLY:
            read_items.append((index, call))
        else:
            # 写工具和未知工具都走串行路径。
            write_items.append((index, call))

    # 只读工具并发执行。
    read_results = await asyncio.gather(*(invoke(call) for _, call in read_items))

    # gather 的结果顺序与 read_items 一致，再根据原始索引放回去。
    for (index, _), result in zip(read_items, read_results, strict=True):
        results[index] = result

    # 写工具依次执行，保证状态变化顺序稳定。
    for index, call in write_items:
        results[index] = await invoke(call)

    # 此时 results 的顺序已经恢复为模型原始顺序。
    return [result for result in results if result is not None]


async def run_agent(
    model: Model,
    messages: list[Message],
    *,
    max_steps: int = 6,
) -> RunResult:
    """驱动循环直到模型给出答案。

    每一轮做四件事：请求模型、把响应加入 messages、执行 tool_calls 并回填、
    判断是否结束。没有 tool_calls 即为正常结束。

    循环只向复制出的列表追加消息，不会向调用方的列表追加；该复制是浅拷贝。

    步数上限不是可选参数：模型可能反复请求同一个工具，缺少上限时循环
    会持续消耗 token 与工具配额，而调用方看不到任何进展。
    """
    steps: list[Step] = []
    history = list(messages)
    for step in range(max_steps):
        response = model(history)
        history.append(response)
        calls = response.get("tool_calls", [])
        if not calls:
            return RunResult(response.get("content", ""), history, steps, "answer")
        calls_results = await execute_calls(calls)
        history.extend(calls_results)
        steps.append(Step(step, calls, calls_results))
    raise MaxStepsExceeded(f"达到最大步数上限: {max_steps}")


# ---------------------------------------------------------------------------
# 验收
# ---------------------------------------------------------------------------


async def check_single_tool() -> None:
    script = [
        assistant_call("call_1", "query_order", order_id="A1001"),
        assistant_answer("订单 A1001 已发货。"),
    ]
    result = await run_agent(scripted_model(script), start_messages("A1001 发货了吗"))

    assert result.stopped_by == "answer"
    assert result.answer == "订单 A1001 已发货。"
    assert len(result.steps) == 1
    assert result.steps[0].results[0]["role"] == "tool"
    assert '"已发货"' in result.steps[0].results[0]["content"]


async def check_history_replayed() -> None:
    original_messages = start_messages("A1001 发货了吗")
    observed_histories: list[list[Message]] = []
    responses = [
        assistant_call("call_1", "query_order", order_id="A1001"),
        assistant_answer("订单 A1001 已发货。"),
    ]

    def model(messages: list[Message]) -> Response:
        observed_histories.append(list(messages))
        return responses.pop(0)

    await run_agent(model, original_messages)

    assert len(original_messages) == 2, "run_agent 不应修改调用方的列表"
    assert observed_histories[1][-1]["role"] == "tool", "后续请求必须包含工具结果"
    assert observed_histories[1][-1]["tool_call_id"] == "call_1"


async def check_parallel_reads() -> None:
    script = [
        assistant_multi_call(
            [
                ("call_1", "query_order", {"order_id": "A1001"}),
                ("call_2", "get_logistics", {"order_id": "A1001"}),
            ]
        ),
        assistant_answer("已发货，顺丰 SF1234567890。"),
    ]

    loop = asyncio.get_running_loop()
    started = loop.time()
    result = await run_agent(scripted_model(script), start_messages("A1001 到哪了"))
    elapsed = loop.time() - started

    ids = [m["tool_call_id"] for m in result.steps[0].results]
    assert ids == ["call_1", "call_2"], f"回填顺序必须与请求一致: {ids}"

    # 两个工具各睡 0.05 秒；串行需要 0.10 秒以上
    assert elapsed < 0.09, f"只读工具应并发执行，实际耗时 {elapsed:.3f}s"


async def check_unknown_tool() -> None:
    script = [
        assistant_call("call_1", "refund", order_id="A1001"),
        assistant_answer("无法自助退款，已转人工处理。"),
    ]
    result = await run_agent(scripted_model(script), start_messages("我要退款"))

    tool_message = result.steps[0].results[0]
    assert '"ok": false' in tool_message["content"], f"未知工具要回填为错误: {tool_message}"
    assert "UnknownTool" in tool_message["content"]
    assert result.answer == "无法自助退款，已转人工处理。"


async def check_max_steps() -> None:
    script = [assistant_call(f"call_{i}", "query_order", order_id="A1001") for i in range(10)]
    try:
        await run_agent(scripted_model(script), start_messages("死循环测试"), max_steps=3)
    except MaxStepsExceeded as exc:
        assert "3" in str(exc), f"异常消息应包含上限: {exc}"
    else:
        raise AssertionError("超过步数上限必须抛 MaxStepsExceeded")


async def main() -> None:
    await check_single_tool()
    await check_history_replayed()
    await check_parallel_reads()
    await check_unknown_tool()
    await check_max_steps()
    print("mini_loop: 全部通过")


if __name__ == "__main__":
    asyncio.run(main())

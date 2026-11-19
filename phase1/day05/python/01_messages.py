"""Day 5 · 练习 1：消息协议的构造与配对。

本文件确认三件事：
1. assistant 消息要么给出 content，要么要求 tool_calls
2. tool_calls 里的 arguments 是 JSON 字符串，不是对象
3. tool 消息靠 tool_call_id 与请求配对

运行：uv run phase1/day05/python/01_messages.py
"""

import json
from typing import Any


def make_tool_call(call_id: str, name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """构造一个 tool_call 条目。

    arguments 以 JSON 字符串形式存放：模型生成的是文本，协议要求原样回传，
    解析由调用方负责。写成对象会让下一轮请求无法序列化。
    """
    return {
        "id": call_id,
        "type": "function",
        "function": {
            "name": name,
            "arguments": json.dumps(arguments, ensure_ascii=False),
        },
    }


def parse_arguments(call: dict[str, Any]) -> dict[str, Any]:
    """取出 tool_call 的参数对象。

    解析失败时抛 ValueError，消息中包含原始字符串。这段内容来自模型，
    排查问题时需要看到原文，只报"解析失败"无法定位。
    """
    # ❌ 原本这里留了一行过程笔记："json字符串 json.dumps(...)"。
    #    注释只写读者需要的信息：这句话记录的是当时怎么想的，对之后改代码没有帮助。
    #    arguments 是字符串这一点，下面的异常处理已经说明了。
    raw = call["function"]["arguments"]
    try:
        result = json.loads(raw)
    except json.JSONDecodeError as e:
        raise ValueError(f"arguments 不是合法 JSON: {raw}") from e

    if not isinstance(result, dict):
        raise ValueError(f"arguments 必须是 JSON 对象: {raw}")

    return result


def make_tool_message(call_id: str, content: str) -> dict[str, Any]:
    """构造回填用的 tool 消息。

    call_id 必须与请求时的 id 一致：模型一次可能返回多个 tool_calls，
    回填靠这个字段把结果归到对应的请求上。
    """
    return {"role": "tool", "tool_call_id": call_id, "content": content}


def make_assistant_message(
    content: str | None,
    calls: list[dict[str, Any]] | None = None,
) -> dict[str, Any]:
    """构造 assistant 消息。

    只给答案时 content 有值、calls 为空；要求调用工具时 content 通常为 None。
    两种形态互斥，混在一起会让下一轮解析无从判断。
    """
    message: dict[str, Any] = {"role": "assistant", "content": content}
    if calls:
        message["tool_calls"] = calls
    return message


if __name__ == "__main__":
    calls = [
        make_tool_call("call_1", "query_order", {"order_id": "A1001"}),
        make_tool_call("call_2", "get_logistics", {"order_id": "A1001"}),
    ]

    assert calls[0]["type"] == "function"
    assert calls[0]["function"]["name"] == "query_order"
    assert isinstance(calls[0]["function"]["arguments"], str), "arguments 必须是字符串"

    assert parse_arguments(calls[0]) == {"order_id": "A1001"}

    try:
        parse_arguments({"function": {"arguments": "{不是合法 JSON"}})
    except ValueError as exc:
        assert "不是合法 JSON" in str(exc), "错误消息要包含原始内容"
    else:
        raise AssertionError("非法 JSON 必须抛 ValueError")

    assistant = make_assistant_message(None, calls)
    assert assistant["role"] == "assistant"
    assert assistant["tool_calls"] == calls
    assert "tool_calls" not in make_assistant_message("最终答案")

    messages = [
        assistant,
        make_tool_message("call_1", '{"status": "已发货"}'),
        make_tool_message("call_2", '{"tracking": "SF1234567890"}'),
    ]
    tool_ids = [m["tool_call_id"] for m in messages if m["role"] == "tool"]
    assert tool_ids == ["call_1", "call_2"], f"回填顺序应与请求一致: {tool_ids}"

    request_ids = [c["id"] for c in assistant["tool_calls"]]
    assert request_ids == tool_ids, "每个请求都要有对应的回填"

    print("01_messages: 全部通过")

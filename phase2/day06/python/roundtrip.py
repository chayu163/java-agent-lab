"""Day 6 练习 2：构造工具结果并校验 call_id 配对。"""

from __future__ import annotations

import json
from typing import Any

Message = dict[str, Any]
ToolCall = dict[str, Any]


def make_tool_result(
    call_id: str,
    *,
    data: Any = None,
    error: str | None = None,
) -> Message:
    """构造 role=tool 消息；error 为 None 表示成功结果。"""
    raise NotImplementedError("TODO: 生成含 role、tool_call_id 和 JSON content 的消息")


def validate_roundtrip(calls: list[ToolCall], results: list[Message]) -> list[str]:
    """返回所有配对问题；完整且合法时返回空列表。

    检查项：
    - 请求 id 唯一，回填 role 均为 tool
    - 回填 id 唯一
    - 每个请求 id 恰有一个回填，不能缺少或多出
    """
    raise NotImplementedError("TODO: 检查请求与回填的 ID 集合及重复项")


def check_examples() -> None:
    calls = [{"id": "call_1"}, {"id": "call_2"}]
    results = [
        make_tool_result("call_1", data={"status": "已发货"}),
        make_tool_result("call_2", error="订单不存在"),
    ]

    assert validate_roundtrip(calls, results) == []
    assert json.loads(results[0]["content"]) == {
        "ok": True,
        "data": {"status": "已发货"},
    }
    assert json.loads(results[1]["content"]) == {
        "ok": False,
        "error": "订单不存在",
    }

    assert validate_roundtrip(calls, results[:1]), "缺少回填必须被发现"
    assert validate_roundtrip(calls, [*results, make_tool_result("call_3", error="extra")])

    wrong_role = [dict(results[0], role="assistant"), results[1]]
    assert validate_roundtrip(calls, wrong_role), "role 错误必须被发现"

    duplicate_result = [*results, dict(results[0])]
    assert validate_roundtrip(calls, duplicate_result), "重复 ID 必须被发现"

    duplicate_call = [*calls, dict(calls[0])]
    assert validate_roundtrip(duplicate_call, results), "重复请求 ID 必须被发现"


if __name__ == "__main__":
    check_examples()
    print("roundtrip: all checks passed")

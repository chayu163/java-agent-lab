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
    """构造 role=tool 消息；error 为 None 表示成功结果。

    成功与失败走同一个 JSON 形状，差别只在 ok 字段。content 必须是字符串：
    协议上 tool 消息的 content 是文本，直接传 dict 会让下一轮请求无法序列化，
    部分 API 也会直接拒绝。

    ❌ 原写法把两个分支写反了：error is None（成功）时塞进 content 的是 error
    （None），失败时塞的是 data。成功路径的 content 是 null，失败路径丢掉错误
    文本，两个方向都错。
    """
    payload = {"ok": True, "data": data} if error is None else {"ok": False, "error": error}
    return {
        "role": "tool",
        "tool_call_id": call_id,
        "content": json.dumps(payload, ensure_ascii=False),
    }


def validate_roundtrip(calls: list[ToolCall], results: list[Message]) -> list[str]:
    """返回所有配对问题；完整且合法时返回空列表。

    检查项：
    - 请求 id 唯一，回填 role 均为 tool
    - 回填 id 唯一
    - 每个请求 id 恰有一个回填，不能缺少或多出

    ❌ 原写法的四个问题：
    1. 四处 `raise` 都是裸的——`raise` 只能在 except 块里重新抛出当前异常，
       函数体里直接写会抛 RuntimeError: No active exception to reraise。
       本函数的契约是"返回问题列表"，任何一条检查失败都应该 append 一条
       描述并继续检查，而不是中断——调用方需要看到全部问题。
    2. `call.get("call_id")` 取错了键。tool_call 条目里的键是 `id`
       （协议字段），`call_id` 只存在于回填消息里。取出来全是 None。
    3. `if unique_call_ids or unique_result_ids:` 逻辑反了。去重后列表
       非空是常态（有 id 就非空），非空不代表有重复。判断重复应该比较
       去重前后的数量：len(set(ids)) != len(ids)。
    4. `len(calls) != len(results)` 只能发现数量不等，发现不了"数量相等
       但 id 不对应"（比如两条回填都填了 call_1）。配对必须按 id 集合比。
    """
    problems: list[str] = []

    call_ids = [call.get("id") for call in calls]
    result_ids: list[str | None] = []
    for index, message in enumerate(results):
        if message.get("role") != "tool":
            problems.append(f"results[{index}] 的 role 是 {message.get('role')!r}，应为 tool")
        result_ids.append(message.get("tool_call_id"))

    if len(set(call_ids)) != len(call_ids):
        problems.append(f"请求 id 有重复: {call_ids}")
    if len(set(result_ids)) != len(result_ids):
        problems.append(f"回填 id 有重复: {result_ids}")

    missing = {cid for cid in call_ids if cid is not None} - {
        rid for rid in result_ids if rid is not None
    }
    if missing:
        problems.append(f"缺少回填: {sorted(missing)}")
    extra = {rid for rid in result_ids if rid is not None} - {
        cid for cid in call_ids if cid is not None
    }
    if extra:
        problems.append(f"多出的回填: {sorted(extra)}")

    return problems


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
    print("roundtrip：全部断言通过")

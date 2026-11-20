"""Day 6 练习 1：构造请求 schema 并归一化模型响应。"""

from __future__ import annotations

from typing import Any

from pydantic import BaseModel, Field


class QueryOrderArgs(BaseModel):
    """按订单号查询订单状态。"""

    order_id: str = Field(description="订单号，例如 A1001")


class GetLogisticsArgs(BaseModel):
    """按订单号查询物流信息。"""

    order_id: str = Field(description="订单号，例如 A1001")


FINISH_ACTIONS = {
    "stop": "answer",
    "tool_calls": "execute",
    "length": "truncated",
    "content_filter": "filtered",
}


def tool_schema(name: str, args_model: type[BaseModel]) -> dict[str, Any]:
    """构造一个工具定义，工具名由可执行函数名提供。"""
    schema = args_model.model_json_schema()
    schema.pop("title", None)
    for property_schema in schema.get("properties", {}).values():
        property_schema.pop("title", None)

    return {
        "type": "function",
        "function": {
            "name": name,
            "description": (args_model.__doc__ or "").strip(),
            "parameters": schema,
        },
    }


def finish_action(finish_reason: str) -> str:
    """将兼容 OpenAI 的结束原因映射成调用方动作。"""
    try:
        return FINISH_ACTIONS[finish_reason]
    except KeyError as exc:
        raise ValueError(f"未知 finish_reason: {finish_reason}") from exc


def assistant_message(response: dict[str, Any]) -> dict[str, Any]:
    """从 Chat Completions 响应中取第一条 assistant message。"""
    choices = response.get("choices")
    if not isinstance(choices, list) or not choices:
        raise ValueError("响应缺少 choices")

    choice = choices[0]
    if not isinstance(choice, dict):
        raise ValueError("choices[0] 格式错误")

    message = choice.get("message")
    if not isinstance(message, dict):
        raise ValueError("响应缺少 assistant message")
    return message


def tool_calls_from(message: dict[str, Any]) -> list[dict[str, Any]]:
    """没有工具调用时返回空列表，错误形状则显式失败。"""
    calls = message.get("tool_calls")
    if calls is None:
        return []
    if not isinstance(calls, list) or any(not isinstance(call, dict) for call in calls):
        raise TypeError("tool_calls 必须是列表或 null")
    return calls


def check_examples() -> None:
    schemas = [
        tool_schema("query_order", QueryOrderArgs),
        tool_schema("get_logistics", GetLogisticsArgs),
    ]
    assert [item["function"]["name"] for item in schemas] == [
        "query_order",
        "get_logistics",
    ]
    assert schemas[0]["function"]["parameters"]["required"] == ["order_id"]

    expected_actions = {
        "stop": "answer",
        "tool_calls": "execute",
        "length": "truncated",
        "content_filter": "filtered",
    }
    for reason, action in expected_actions.items():
        assert finish_action(reason) == action

    try:
        finish_action("unknown")
    except ValueError:
        pass
    else:
        raise AssertionError("未知 finish_reason 必须报错")

    message = assistant_message(
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": None,
                        "tool_calls": [
                            {
                                "id": "call_1",
                                "type": "function",
                                "function": {
                                    "name": "query_order",
                                    "arguments": '{"order_id": "A1001"}',
                                },
                            }
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        }
    )
    calls = tool_calls_from(message)
    assert calls[0]["id"] == "call_1"
    assert calls[0]["function"]["name"] == "query_order"
    assert tool_calls_from({"role": "assistant", "content": "answer"}) == []


if __name__ == "__main__":
    check_examples()
    print("protocol：全部断言通过")

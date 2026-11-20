"""使用假模型或真实 API 执行两轮 function calling 会话。"""

from __future__ import annotations

import argparse
import asyncio
import json
import os
import time
from collections.abc import Awaitable, Callable
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
from pydantic import BaseModel, Field

from phase2.day06.protocol import (
    assistant_message,
    finish_action,
    tool_calls_from,
    tool_schema,
)
from phase2.day06.roundtrip import make_tool_result, validate_roundtrip

Message = dict[str, Any]
Response = dict[str, Any]
RequestBody = dict[str, Any]
Complete = Callable[[RequestBody], Awaitable[Response]]

ORDERS: dict[str, dict[str, Any]] = {
    "A1001": {"status": "已发货", "carrier": "顺丰", "tracking": "SF1234567890"},
    "A1002": {"status": "待付款"},
}

SYSTEM_PROMPT = "你是电商售后助手。查询类信息必须先调用工具获取，不要凭空回答。"
LOGS_DIR = Path(__file__).resolve().parent / "logs"


class QueryOrderArgs(BaseModel):
    """按订单号查询订单状态。"""

    order_id: str = Field(description="订单号，例如 A1001")


class GetLogisticsArgs(BaseModel):
    """按订单号查询物流信息。"""

    order_id: str = Field(description="订单号，例如 A1001")


async def query_order(order_id: str) -> dict[str, Any]:
    order = ORDERS.get(order_id)
    if order is None:
        raise KeyError(f"订单不存在: {order_id}")
    return {"order_id": order_id, "status": order["status"]}


async def get_logistics(order_id: str) -> dict[str, Any]:
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


TOOL_ARGUMENTS: dict[str, type[BaseModel]] = {
    "query_order": QueryOrderArgs,
    "get_logistics": GetLogisticsArgs,
}
TOOL_HANDLERS: dict[str, Callable[..., Awaitable[dict[str, Any]]]] = {
    "query_order": query_order,
    "get_logistics": get_logistics,
}
TOOL_SCHEMAS = [tool_schema(name, model) for name, model in TOOL_ARGUMENTS.items()]


def request_body(model: str, messages: list[Message]) -> RequestBody:
    return {
        "model": model,
        "messages": messages,
        "tools": TOOL_SCHEMAS,
        "tool_choice": "auto",
        "parallel_tool_calls": True,
        "max_tokens": 512,
    }


async def invoke_tool(call: dict[str, Any]) -> Message:
    call_id = call.get("id")
    function = call.get("function")
    if not isinstance(call_id, str) or not isinstance(function, dict):
        raise ValueError(f"工具调用格式错误: {call!r}")

    name = function.get("name")
    if not isinstance(name, str):
        return make_tool_result(call_id, error="工具调用缺少字符串 name")
    args_model = TOOL_ARGUMENTS.get(name)
    handler = TOOL_HANDLERS.get(name)
    if args_model is None or handler is None:
        return make_tool_result(call_id, error=f"未知工具: {name}")

    try:
        raw_arguments = json.loads(function["arguments"])
        arguments = args_model.model_validate(raw_arguments)
        data = await handler(**arguments.model_dump())
    except Exception as exc:
        return make_tool_result(call_id, error=f"{type(exc).__name__}: {exc}")

    return make_tool_result(call_id, data=data)


async def execute_calls(calls: list[dict[str, Any]]) -> list[Message]:
    results = await asyncio.gather(*(invoke_tool(call) for call in calls))
    problems = validate_roundtrip(calls, results)
    if problems:
        raise ValueError("工具回填不完整: " + "; ".join(problems))
    return results


async def run_session(
    complete: Complete,
    question: str,
    *,
    model: str,
    max_turns: int = 3,
) -> tuple[str, list[Message], list[dict[str, Any]]]:
    messages: list[Message] = [
        {"role": "system", "content": SYSTEM_PROMPT},
        {"role": "user", "content": question},
    ]
    exchanges: list[dict[str, Any]] = []

    for _turn in range(max_turns):
        body = request_body(model, messages)
        response = await complete(body)
        exchanges.append({"request": body, "response": response})

        message = assistant_message(response)
        action = finish_action(response["choices"][0].get("finish_reason", ""))
        messages.append(message)

        if action == "answer":
            return message.get("content") or "", messages, exchanges
        if action == "truncated":
            raise RuntimeError("模型响应因长度限制被截断")
        if action == "filtered":
            raise RuntimeError("模型响应被内容过滤策略拦截")

        calls = tool_calls_from(message)
        if not calls:
            raise ValueError("finish_reason=tool_calls，但响应没有工具调用")
        messages.extend(await execute_calls(calls))

    raise RuntimeError(f"达到模型请求轮数上限: {max_turns}")


def scripted_completion() -> Complete:
    responses: list[Response] = [
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
                            },
                            {
                                "id": "call_2",
                                "type": "function",
                                "function": {
                                    "name": "get_logistics",
                                    "arguments": '{"order_id": "A1001"}',
                                },
                            },
                        ],
                    },
                    "finish_reason": "tool_calls",
                }
            ]
        },
        {
            "choices": [
                {
                    "message": {
                        "role": "assistant",
                        "content": "A1001 已发货，承运方是顺丰，单号 SF1234567890。",
                    },
                    "finish_reason": "stop",
                }
            ]
        },
    ]

    async def complete(body: RequestBody) -> Response:
        if not responses:
            raise AssertionError("假模型响应已用尽")
        if body["tools"] != TOOL_SCHEMAS:
            raise AssertionError("每轮请求都必须包含工具定义")
        expected_message_count = 2 if len(responses) == 2 else 5
        if len(body["messages"]) != expected_message_count:
            raise AssertionError("后续请求必须带上 assistant 请求和两条 tool 回填")
        return responses.pop(0)

    return complete


def openai_completion(
    client: httpx.AsyncClient,
    base_url: str,
    api_key: str,
) -> Complete:
    async def complete(body: RequestBody) -> Response:
        response = await client.post(
            f"{base_url.rstrip('/')}/chat/completions",
            json=body,
            headers={"Authorization": f"Bearer {api_key}"},
        )
        response.raise_for_status()
        return response.json()

    return complete


def save_log(
    answer: str,
    messages: list[Message],
    exchanges: list[dict[str, Any]],
    elapsed_s: float,
) -> Path:
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S-%f")
    path = LOGS_DIR / f"session-{stamp}.json"
    path.write_text(
        json.dumps(
            {
                "answer": answer,
                "elapsed_s": round(elapsed_s, 3),
                "messages": messages,
                "exchanges": exchanges,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


async def run_offline() -> None:
    started = time.perf_counter()
    answer, messages, exchanges = await run_session(
        scripted_completion(),
        "A1001 发货了吗？发的什么快递？",
        model="scripted-model",
    )
    elapsed = time.perf_counter() - started

    assert len(exchanges) == 2
    assert exchanges[0]["response"]["choices"][0]["finish_reason"] == "tool_calls"
    assert exchanges[1]["response"]["choices"][0]["finish_reason"] == "stop"
    path = save_log(answer, messages, exchanges, elapsed)
    print(f"离线会话通过：{len(exchanges)} 轮，日志写入 {path}")
    print(answer)


async def run_real() -> None:
    base_url = os.environ.get("OPENAI_BASE_URL")
    api_key = os.environ.get("OPENAI_API_KEY")
    model = os.environ.get("OPENAI_MODEL", "deepseek-chat")
    if not base_url or not api_key:
        raise SystemExit("真机模式需要 OPENAI_BASE_URL 与 OPENAI_API_KEY")

    started = time.perf_counter()
    async with httpx.AsyncClient(timeout=60.0) as client:
        complete = openai_completion(client, base_url, api_key)
        answer, messages, exchanges = await run_session(
            complete,
            "A1001 发货了吗？发的什么快递？",
            model=model,
        )
    elapsed = time.perf_counter() - started
    path = save_log(answer, messages, exchanges, elapsed)
    print(f"真机调用通过：{len(exchanges)} 轮，日志写入 {path}")
    print(answer)


def main() -> None:
    parser = argparse.ArgumentParser()
    parser.add_argument("--real", action="store_true", help="访问真实兼容 OpenAI 的 API")
    args = parser.parse_args()
    asyncio.run(run_real() if args.real else run_offline())


if __name__ == "__main__":
    main()

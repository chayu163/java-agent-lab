"""Day 5 · 练习 2：工具注册表。

注册表同时决定两件事：模型能看到哪些工具，名字解析时落到哪个函数。
本文件确认四点：
1. 登记进表的名字是函数名，不需要额外声明
2. 发给模型的 schema 由表生成，一处维护
3. 解析参数失败与未知工具名要分别处理
4. 路由只认表内的名字，不做动态查找

运行：uv run day05/python/02_registry.py
现在运行会抛 NotImplementedError。
"""

import asyncio
import json
from collections.abc import Awaitable, Callable
from typing import Any

# ❌ from mypy.checkexpr import TooManyUnions
#    IDE 自动补全误加的导入，本文件没有用到它。
#    更严重的是它把运行时依赖指向了 mypy 的内部模块：mypy 装在 dev 组，
#    生产环境或只装运行期依赖的环境里会直接 ImportError，而循环本身不需要类型检查器。
#    ruff 报 F401（未使用），这条规则存在的意义就是拦这类误导入。

Tool = Callable[..., Awaitable[dict[str, Any]]]

TOOLS: dict[str, Tool] = {}
SCHEMAS: dict[str, dict[str, Any]] = {}


class UnknownTool(Exception):
    """请求的工具不在注册表内。"""


def tool(
    description: str,
    parameters: dict[str, Any],
) -> Callable[[Tool], Tool]:
    """把函数登记进注册表，并记录它的描述与参数 schema。

    返回原函数，因此注册不会改变调用方式。描述与参数在登记时一并给出，
    而不是运行时反射签名：模型看到的说明必须是给人写的那句话，
    参数约束也常常比类型注解更严格（例如枚举取值）。

    ★ 这是带参数的装饰器，结构是三层：tool(...) -> decorator -> wrapper。
      与 Day 2 的 retry 同形。
    """

    def decorator(fn: Tool) -> Tool:
        TOOLS[fn.__name__] = fn
        SCHEMAS[fn.__name__] = {
            "description": description,
            "parameters": parameters,
        }
        return fn

    return decorator


@tool(
    description="按订单号查询订单状态",
    parameters={
        "type": "object",
        "properties": {"order_id": {"type": "string", "description": "订单号，例如 A1001"}},
        "required": ["order_id"],
    },
)
async def query_order(order_id: str) -> dict[str, Any]:
    return {"order_id": order_id, "status": "已发货"}


@tool(
    description="创建售后工单",
    parameters={
        "type": "object",
        "properties": {
            "order_id": {"type": "string"},
            "reason": {"type": "string"},
        },
        "required": ["order_id", "reason"],
    },
)
async def create_ticket(order_id: str, reason: str) -> dict[str, Any]:
    return {"ticket_id": "T0001", "order_id": order_id, "reason": reason}


def schemas_for_model() -> list[dict[str, Any]]:
    """生成发给模型的 tools 数组。

    从注册表推导而不是手写第二份：工具增删时只需要改一处，
    手写的副本一定会与实现脱节。
    """
    # ❌ 原写法：
    # ❌     for name, schema in SCHEMAS.items():
    # ❌         description , parameters = schema
    # ❌         tools.append({..., "description": description, "parameters": parameters})
    #
    #    问题：对字典做多项解包，迭代的是【键】而不是值。
    #    实测输出 description == "description"、parameters == "parameters"，
    #    工具说明和参数约束全部丢失，模型收到的是一份无意义的 schema。
    #
    #    断言没抓到的原因：原断言只检查了 "parameters" in schemas[0]["function"]，
    #    键存在即通过，没有校验值。下面把断言补成校验具体内容。
    #
    # ✅ 按名字取值，或者直接把 schema 展开。
    tools: list[dict[str, Any]] = []
    for name, schema in SCHEMAS.items():
        tools.append(
            {
                "type": "function",
                "function": {"name": name, **schema},
            }
        )
    return tools


def parse_arguments(arguments: str) -> dict[str, Any]:
    """解析模型给出的参数文本。

    解析失败时转成 ValueError 并保留原文：这段内容由模型生成，
    排查时需要看到实际收到了什么。
    """
    try:
        return json.loads(arguments)
    except json.JSONDecodeError as exc:
        raise ValueError(f"参数不是合法 JSON: {arguments!r}") from exc


async def dispatch(name: str, arguments: str) -> dict[str, Any]:
    """按名字调用工具，返回结果。

    三处失败要区分对待：
    - 名字不在表内：抛 UnknownTool，这类请求不该被执行
    - arguments 不是合法 JSON：抛 ValueError，消息带原文
    - 参数缺失或类型不符：由函数调用本身抛出 TypeError，原样上抛

    三种情况都属于"模型输出不可靠"，但处理策略不同：前两种可以在循环里
    回填成错误消息让模型自行修正，第三种通常说明 schema 与实现不一致。
    """
    if name not in TOOLS:
        raise UnknownTool(f"未知工具: {name}")
    tool_fn = TOOLS[name]
    parameters = parse_arguments(arguments)
    return await tool_fn(**parameters)


async def main() -> None:
    assert set(TOOLS) == {"query_order", "create_ticket"}, f"注册表内容不对: {set(TOOLS)}"

    schemas = schemas_for_model()
    assert len(schemas) == 2
    names = {item["function"]["name"] for item in schemas}
    assert names == {"query_order", "create_ticket"}
    assert schemas[0]["type"] == "function"
    assert "parameters" in schemas[0]["function"], "schema 必须带 parameters"

    # 只验证"键存在"不足以发现值错误：把 description 和 parameters 的实际内容也纳入断言
    by_name = {item["function"]["name"]: item["function"] for item in schemas}
    assert by_name["query_order"]["description"] == "按订单号查询订单状态", by_name["query_order"]
    assert by_name["query_order"]["parameters"]["required"] == ["order_id"]
    assert by_name["create_ticket"]["parameters"]["properties"]["reason"]["type"] == "string"

    result = await dispatch("query_order", '{"order_id": "A1001"}')
    assert result == {"order_id": "A1001", "status": "已发货"}

    try:
        await dispatch("refund", "{}")
    except UnknownTool as exc:
        assert "refund" in str(exc)
    else:
        raise AssertionError("未知工具必须抛 UnknownTool")

    try:
        await dispatch("query_order", "{坏掉的 JSON")
    except ValueError as exc:
        assert "坏掉的 JSON" in str(exc)
    else:
        raise AssertionError("非法参数必须抛 ValueError")

    try:
        await dispatch("query_order", "{}")
    except TypeError:
        pass
    else:
        raise AssertionError("缺少必填参数应由函数调用抛出 TypeError")

    print("02_registry: 全部通过")


if __name__ == "__main__":
    # ❌ 原写法把 import asyncio 放在这里。能跑，但导入位置随调用方式变化，
    #    且 ruff 的导入排序规则只看模块顶部。标准库导入统一放在文件开头。
    asyncio.run(main())

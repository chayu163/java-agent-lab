"""Day 2 产出【批注版】：用 Pydantic 定义一套 Tool schema，并转成模型 API 认的形状。

三层对应关系：
    Pydantic model   ->  JSON Schema        （model_json_schema()）
    $defs + $ref     ->  复用与递归的表达方式，模型 API 不一定认
    内联后的 schema   ->  OpenAI function calling 的 parameters 字段

标注约定：★ = 语法点，◆ = 设计理由。第一次读可以跳过注释，卡住再回来查。
"""

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 语法速查（对照 Java，卡住时回头看这张表）
# ---------------------------------------------------------------------------
# ★ import 分三段：标准库 → 第三方 → 本地，中间必须空行隔开，ruff 会按这个顺序检查。
#   `from typing import Any, Literal`：typing 是标准库（不用装）。
#   Any ≈ Java 的 Object（任意类型）；Literal["a","b"] = 只能是这几个值之一。
# ★ x: int = 10              带类型注解的赋值。注解【运行时完全不生效】，只给 mypy / IDE 看。
# ★ str | None               联合类型 = 可空，等价 typing.Optional[str]，≈ @Nullable String。
# ★ list[str] / dict[str, Any] / tuple[str, ...]
#                            泛型下标，Python 3.9+ 支持内置类型直接写。
#                            tuple 里的 ... 表示"任意长度的 str"。
# ★ [f(x) for x in xs]       列表推导式 ≈ stream().map().collect()；换成 {} 就是字典推导式。
# ★ (*xs, y)                 星号解包：把元组摊开再拼成【新元组】，不是加法。
# ★ f"a {b}"                 f-string，{} 里直接写表达式，≈ String.format("a %s", b)。
# ★ d.get(k, 默认值)         取字典的键，不存在时返回默认值，不会 KeyError。
# ★ s.rsplit("/", 1)[-1]     从右往左切一次取最后一段；[-1] 是负索引 = 最后一个元素。
# ★ isinstance(x, dict)      类型判断，≈ Java 的 x instanceof Map。
# ★ assert 条件              断言，给 mypy 做类型收窄用；不满足会抛 AssertionError。

# ---------------------------------------------------------------------------
# 1. 参数定义：schema 的唯一来源
# ---------------------------------------------------------------------------


# ★ class X(BaseModel): 继承。Pydantic 在【类创建的那一刻】扫描所有注解，生成 schema。
#   所以字段只需要写注解，不需要像 Java 那样声明成员变量再写 getter。
class OrderQueryArgs(BaseModel):
    """query_order 的参数。"""

    # ★ 类 docstring 会被 Pydantic 提到 schema 根上的 description 字段，所以保持一句话——
    #   写成两段，整段都会进 schema、进 token。
    # ★ 左边 `order_id: str` 是字段名 + 类型，右边 `= Field(...)` 是默认值和约束。
    #   没有默认值 → 生成 schema 时进 required（必填）。
    order_id: str = Field(description="订单号，例如 A1001")

    # ★ Literal[...] | None = 枚举 + 可空，默认值 None 让它成为"可选参数"。
    # ◆ 重点：让它可选的是【默认值】，不是 `| None`。Pydantic v2 里 `X | None` 但没有默认值
    #   仍然是必填的，只是允许你显式传 null。这条最容易记反。
    status: Literal["CREATED", "PAID", "SHIPPED", "CANCELLED"] | None = Field(
        default=None,
        description="按状态过滤，不传则不过滤",
    )

    # ★ ge = greater or equal，le = less or equal → 生成 schema 里的 minimum / maximum。
    #   这类约束在 Java 里是 @Min / @Max。
    limit: int = Field(default=10, ge=1, le=100, description="返回条数上限")


class TicketCreateArgs(BaseModel):
    """create_ticket 的参数。"""

    order_id: str = Field(description="关联订单号")

    # ★ min_length / max_length → 生成 minLength / maxLength（字符串长度，不是字节数）
    reason: str = Field(min_length=5, max_length=200, description="工单原因，5-200 字")

    # ★ 这个字段参数多，拆成多行写。括号内的换行不需要反斜杠，Python 靠括号续行。
    priority: Literal["low", "normal", "high"] = Field(
        default="normal",
        description="工单优先级",
    )


# ---------------------------------------------------------------------------
# 2. schema 加工：展开 $ref、剥掉噪音键
# ---------------------------------------------------------------------------
#
# $ref / $defs 什么时候出现？规律只有一条：
#     只要 schema 里出现"有名字的东西"（嵌套的 BaseModel、Enum 类），Pydantic 就把它
#     提到顶层 $defs 里存一份，原地留一个 {"$ref": "#/$defs/类名"} 指针。
#     普通类型（str / int / list[str] / Literal）直接内联展开，不产生 $ref。
#
# 为什么要内联：$ref 是 JSON Schema 2020-12 的语法，各家模型服务对它的支持不一致，
# 摊平成自足的结构最保险；顺带把 title（Pydantic 自动加的字段标题）一起剥掉省 token。

# ★ {...} 是 set（集合）字面量；空集合要写 set()，写 {} 会得到空 dict。
#   成员判断 `key in DROP_KEYS` 是 O(1) 哈希查找。
DROP_KEYS = {"title", "$defs"}


# ★ def 签名三段：参数注解、默认值、-> 返回值注解。
#   - `stack: tuple[str, ...] = ()`：默认值是空元组。元组不可变，所以这里【不会】踩
#     Day 1 那个"可变默认参数被共享"的坑（list/dict/set 当默认值才有那个问题）。
#   - 函数名以下划线开头 = "内部函数"的约定，不是语法限制，外部照样能调。
def _walk(node: Any, defs: dict[str, Any], stack: tuple[str, ...] = ()) -> Any:
    """递归遍历 schema：遇到 $ref 就展开，顺手丢掉 DROP_KEYS。"""

    # ★ 先处理 list。schema 里到处都是数组：required、enum、anyOf、allOf 都是。
    if isinstance(node, list):
        # ★ 列表推导式，等价于：
        #     out = []
        #     for item in node:
        #         out.append(_walk(item, defs, stack))
        #     return out
        return [_walk(item, defs, stack) for item in node]

    # ★ 既不是 list 也不是 dict → 是字符串 / 数字 / 布尔，原样返回。
    #   这一句就是递归的【终止条件】，没有它就会无限往下钻。
    if not isinstance(node, dict):
        return node

    # ★ dict.get(键)：键存在返回值，不存在返回 None，不会像 node["$ref"] 那样抛 KeyError。
    ref = node.get("$ref")

    # ★ isinstance(x, str) 判类型，比 type(x) is str 更好用（子类也算）。
    #   `is` 在这里比的是"是不是同一个对象"——str 是不可变对象，判断类型用 isinstance。
    if isinstance(ref, str):
        # ★ rsplit("/", 1)：从【右】往左只切一次。
        #   "#/$defs/OrderQueryArgs".rsplit("/", 1) → ["#/$defs", "OrderQueryArgs"]
        #   [-1] 取最后一个元素（负索引从末尾数）→ "OrderQueryArgs"
        name = ref.rsplit("/", 1)[-1]

        # ◆ stack 记录"我正在展开谁"。如果 A 的字段里又引用了 A，不拦就是无限递归。
        if name in stack:
            # ★ f-string 的 {} 里可以写任意表达式：这里先 (*stack, name) 拼元组，
            #   再 .join(...) 拼字符串。`{' -> '.join(...)}` 整体是一个表达式。
            raise ValueError(f"循环引用无法内联：{' -> '.join((*stack, name))}")

        if name not in defs:
            raise ValueError(f"$ref 指向不存在的定义：{ref}")

        # ◆ 整个函数最关键的一行。
        #   替换的单位是【节点】，不是"键"——所以这里直接 return 展开后的内容。
        #   而且展开出来的定义自身可能还带 $ref（A 引用 B，B 引用 C），
        #   所以必须【再走一遍 _walk】，这就是"递归"两个字的全部含义。
        return _walk(defs[name], defs, (*stack, name))

    # ◆ 字典推导式：重建一个【新】dict 并过滤 DROP_KEYS。
    #   注意括号：{k: v for ...} 是字典，[x for ...] 是列表，写成一样只是习惯。
    #   不用原地删 key 是因为 model_json_schema() 每次返回新对象，但改入参会污染调用方，
    #   重建更安全、也更好测试。
    return {key: _walk(value, defs, stack) for key, value in node.items() if key not in DROP_KEYS}


def inline_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """把 model_json_schema() 的输出变成自足的、不含 $ref 的 schema。"""
    # ★ get 的第二个参数是默认值：没有嵌套 model 时返回空 dict，
    #   后面 defs[name] 才不会 KeyError。
    result = _walk(schema, schema.get("$defs", {}))

    # ★ assert 在这里是【给 mypy 看的】：_walk 返回 Any，assert 之后 mypy 才认定它是 dict。
    #   运行时这一句几乎不可能失败（顶层一定是 dict）。
    assert isinstance(result, dict)
    return result


# ---------------------------------------------------------------------------
# 3. 组装成模型 API 认的形状
# ---------------------------------------------------------------------------


# ★ `type[BaseModel]` = "BaseModel 这个类本身"，≈ Java 的 Class<? extends BaseModel>。
#   注意传进来的是【类】不是实例，所以后面能调 args_model.model_json_schema()。
#   （model_dump() 才是给实例用的，返回的是数据不是 schema。）
def to_tool(name: str, description: str, args_model: type[BaseModel]) -> dict[str, Any]:
    """一个工具定义：name/description 给人看，parameters 给模型填。"""
    # ★ 返回嵌套 dict。键用引号是因为最终要变成 JSON（JSON 的键必须是字符串），
    #   这和调用函数时的关键字参数 name=... 是两回事。
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": inline_schema(args_model.model_json_schema()),
        },
    }


# ★ 列表字面量，元素是 to_tool(...) 的返回值。注意：模块被 import 时这段就会执行一次，
#   所以 TOOLS 是"导入即算好"的常量，不是每次用的时候才生成。
TOOLS = [
    # ★ 关键字参数：调用时写 name= / args_model= 比按位置传更安全，也更好读。
    to_tool(
        name="query_order",
        description="根据订单号查询订单状态与物流信息",
        args_model=OrderQueryArgs,
    ),
    to_tool(
        name="create_ticket",
        description="为订单售后创建工单，需要人工跟进时调用",
        args_model=TicketCreateArgs,
    ),
]


# ★ __name__ 是模块的内置变量：直接运行本文件时它的值是 "__main__"，被 import 时是模块名。
#   所以这段只在 `uv run day02/python/tool_schema.py` 时执行，≈ Java 的 main 方法。
if __name__ == "__main__":
    # ★ ensure_ascii=False 让中文原样输出（默认会转成 中 这种转义），
    #   indent=2 让 JSON 带缩进，方便人读。
    print(json.dumps(TOOLS, ensure_ascii=False, indent=2))

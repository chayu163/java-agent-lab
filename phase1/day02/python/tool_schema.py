"""Day 2 产出：用 Pydantic 定义一套 Tool schema，并转成模型 API 认的形状。

三层对应关系：
    Pydantic model    ->  JSON Schema          model_json_schema()
    $defs + $ref      ->  JSON Schema 引用；目标 API 的支持范围需单独确认
    内联后的 schema    ->  OpenAI function calling 的 parameters 字段

标注约定：★ 标注语法点，◆ 标注设计理由。首次阅读可跳过注释，查阅时再回看。
"""

import json
from typing import Any, Literal

from pydantic import BaseModel, Field

# ---------------------------------------------------------------------------
# 语法速查：与 Java 的对应关系
# ---------------------------------------------------------------------------
# ★ import 分三段：标准库 → 第三方 → 本地，段间空行，ruff 按此顺序检查。
#   typing 属于标准库，无需安装。
#   Any 让静态检查器不再约束该值，不等同于 Java 的 Object；Literal 描述允许的字面量集合。
# ★ x: int = 10              带类型注解的赋值。Python 不强制该值为 int；注解仍可供工具和库读取。
# ★ str | None               联合类型，表示可空，等价 typing.Optional[str]，对应 @Nullable String。
# ★ list[str] / dict[str, Any] / tuple[str, ...]
#                            泛型下标，Python 3.9+ 支持在内置类型上直接书写。
#                            tuple 中的 ... 表示元素类型相同、长度任意。
# ★ [f(x) for x in xs]       列表推导式，对应 stream().map().collect()；换成 {} 即字典推导式。
# ★ (*xs, y)                 星号解包：把元组摊开后拼成新元组，不是算术加法。
# ★ f"a {b}"                 f-string，花括号内可直接写表达式，对应 String.format("a %s", b)。
# ★ d.get(k, 默认值)         取字典键，不存在时返回默认值，不抛 KeyError。
# ★ s.rsplit("/", 1)[-1]     从右侧切分一次后取末段；[-1] 是负索引，指向最后一个元素。
# ★ isinstance(x, dict)      类型判断，对应 Java 的 x instanceof Map。
# ★ assert 条件              断言。此处用于给 mypy 收窄类型；不满足时抛 AssertionError。

# ---------------------------------------------------------------------------
# 1. 参数定义：schema 的唯一来源
# ---------------------------------------------------------------------------


# ★ class X(BaseModel): 继承。Pydantic 在类创建时扫描全部注解并生成 schema，
#   因此字段只需写注解，不必像 Java 那样先声明成员变量再写 getter。
class OrderQueryArgs(BaseModel):
    """query_order 的参数。"""

    # ★ 类 docstring 会被 Pydantic 写入 schema 根部的 description 字段。
    #   保持一句话：写成多段时整段都会进入 schema，占用 token。
    # ★ `order_id: str` 是字段名与类型，`Field(...)` 给出默认值与约束。
    #   没有默认值的字段，生成 schema 时进入 required。
    order_id: str = Field(description="订单号，例如 A1001")

    # ★ Literal[...] | None = 有限取值 + 可空。
    # ◆ 决定字段是否可选的是默认值，不是 `| None`。Pydantic v2 中仅写 `X | None`
    #   而未给默认值时，字段仍为必填，只是允许显式传入 null。
    status: Literal["CREATED", "PAID", "SHIPPED", "CANCELLED"] | None = Field(
        default=None,
        description="按状态过滤，不传则不过滤",
    )

    # ★ ge 与 le 分别生成 schema 的 minimum / maximum，对应 Java 的 @Min / @Max。
    limit: int = Field(default=10, ge=1, le=100, description="返回条数上限")


class TicketCreateArgs(BaseModel):
    """create_ticket 的参数。"""

    order_id: str = Field(description="关联订单号")

    # ★ min_length / max_length 生成 minLength / maxLength，计的是字符数而非字节数。
    reason: str = Field(min_length=5, max_length=200, description="工单原因，5-200 字")

    # ★ 该字段的约束较多，拆成多行书写。括号内的换行不需要反斜杠。
    priority: Literal["low", "normal", "high"] = Field(
        default="normal",
        description="工单优先级",
    )


# ---------------------------------------------------------------------------
# 2. schema 加工：展开 $ref、剥掉噪音键
# ---------------------------------------------------------------------------
#
# Pydantic 可将可复用的嵌套定义放入 $defs，并在属性位置用 $ref 引用；简单基础字段通常直接内联。
# 具体 schema 形状会受模型定义、Pydantic 版本与配置影响，不能只凭类型名称推断。
#
# 本练习只展开形如 #/$defs/Name 的本地引用，不实现完整 JSON Pointer 解析。
# DROP_KEYS 是本项目的转换选择，不代表所有模型 API 都拒绝这些 schema 字段。

# ★ {...} 是 set 字面量；空集合必须写作 set()，因为 {} 得到的是空 dict。
#   成员判断 `key in DROP_KEYS` 为 O(1) 哈希查找。
DROP_KEYS = {"title", "$defs"}


# ★ def 签名由三段组成：参数注解、默认值、返回值注解。
#   - `stack: tuple[str, ...] = ()` 的默认值是空元组。元组不可变，因此不会出现
#     Day 1 所述「可变默认参数被所有调用共享」的问题；list / dict / set 作默认值才有该问题。
#   - 下划线开头的函数名表示「内部使用」，属于约定而非语法限制。
def _walk(node: Any, defs: dict[str, Any], stack: tuple[str, ...] = ()) -> Any:
    """递归遍历 schema：展开 $ref，并丢弃 DROP_KEYS 中的键。"""

    # ★ 优先处理 list。schema 中的 required、enum、anyOf、allOf 都是数组。
    if isinstance(node, list):
        # ★ 列表推导式等价于显式循环加 append。
        return [_walk(item, defs, stack) for item in node]

    # ★ 既非 list 也非 dict 时，是字符串、数字或布尔值，原样返回。
    #   这一句是递归的终止条件，缺少它会无限下钻。
    if not isinstance(node, dict):
        return node

    # ★ dict.get 在键不存在时返回 None，不会像 node["$ref"] 那样抛 KeyError。
    ref = node.get("$ref")

    # ★ 判断类型用 isinstance 而非 type(x) is str，前者对子类同样成立。
    if isinstance(ref, str):
        # ★ rsplit("/", 1) 从右侧切分一次：
        #   "#/$defs/OrderQueryArgs" -> ["#/$defs", "OrderQueryArgs"]，[-1] 取末段。
        name = ref.rsplit("/", 1)[-1]

        # ◆ stack 记录当前正在展开的类型。若 A 的字段又引用 A，不做拦截会无限递归。
        if name in stack:
            raise ValueError(f"循环引用无法内联：{' -> '.join((*stack, name))}")

        if name not in defs:
            raise ValueError(f"$ref 指向不存在的定义：{ref}")

        # ◆ 本函数的核心。替换的单位是节点而非键，因此直接返回展开后的内容。
        #   展开结果自身可能仍含 $ref（A 引用 B，B 引用 C），所以必须再走一遍 _walk。
        return _walk(defs[name], defs, (*stack, name))

    # ◆ 字典推导式重建新 dict 并过滤 DROP_KEYS。
    #   不原地删除键，是因为修改入参会污染调用方。
    return {key: _walk(value, defs, stack) for key, value in node.items() if key not in DROP_KEYS}


def inline_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """把 model_json_schema() 的输出转成不含 $ref 的自足 schema。"""
    # ★ get 的第二个参数是默认值：没有嵌套 model 时返回空 dict，后续 defs[name] 才不会 KeyError。
    result = _walk(schema, schema.get("$defs", {}))

    # ★ 这里的 assert 供 mypy 使用：_walk 返回 Any，断言之后 mypy 才认定它是 dict。
    assert isinstance(result, dict)
    return result


# ---------------------------------------------------------------------------
# 3. 组装成模型 API 认的形状
# ---------------------------------------------------------------------------


# ★ `type[BaseModel]` 表示 BaseModel 这个类本身，对应 Java 的 Class<? extends BaseModel>。
#   传入的是类而非实例，因此后面可以调用 args_model.model_json_schema()；
#   model_dump() 用于实例，返回的是数据而不是 schema。
def to_tool(name: str, description: str, args_model: type[BaseModel]) -> dict[str, Any]:
    """构造一个工具定义：name 与 description 给人看，parameters 供模型填。"""
    # ★ 返回嵌套 dict。键加引号是因为最终要序列化为 JSON，而 JSON 的键必须是字符串；
    #   这与调用函数时的关键字参数 name=... 是两回事。
    return {
        "type": "function",
        "function": {
            "name": name,
            "description": description,
            "parameters": inline_schema(args_model.model_json_schema()),
        },
    }


# ★ 模块被 import 时这段代码即执行一次，因此 TOOLS 是导入时算好的常量。
# ★ 关键字参数写法比按位置传参更安全，也更易读。
TOOLS = [
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


# ★ __name__ 在直接运行本文件时为 "__main__"，被 import 时为模块名。
#   这段只在 `uv run phase1/day02/python/tool_schema.py` 下执行，对应 Java 的 main 方法。
if __name__ == "__main__":
    sample_with_ref = {
        "$defs": {
            "Address": {
                "type": "object",
                "properties": {"city": {"title": "City", "type": "string"}},
            }
        },
        "properties": {"address": {"$ref": "#/$defs/Address"}},
    }
    expanded = inline_schema(sample_with_ref)
    address_schema = expanded["properties"]["address"]
    assert address_schema["properties"]["city"]["type"] == "string"
    assert "$ref" not in json.dumps(expanded)
    assert "$defs" not in expanded
    assert "title" not in json.dumps(expanded)

    # ★ ensure_ascii=False 让中文原样输出，indent=2 生成带缩进的 JSON。
    print(json.dumps(TOOLS, ensure_ascii=False, indent=2))

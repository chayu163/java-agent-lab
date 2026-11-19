"""Day 4 · 练习 2：parametrize —— 一张表生成 N 条独立用例。

本文件确认三点：
1. 一个参数组合对应一条独立用例，在报告中分别列出
2. ids 使失败信息可读
3. pytest.raises 同样可以参数化：同一个函数、多种异常

运行：uv run pytest day04/python/02_parametrize_test.py -v
"""

import pytest


def parse_order_id(raw: str) -> str:
    """把用户输入规整成订单号。

    规则：
        去除首尾空格
        不能为空
        必须是大写字母开头的字母数字组合，例如 A1001、B2
    非法输入抛 ValueError。
    """
    text = raw.strip()
    if not text:
        raise ValueError("订单号不能为空")
    if not text[0].isalpha() or not text[0].isupper():
        raise ValueError(f"订单号必须以大写字母开头: {raw!r}")
    if not text.isalnum():
        raise ValueError(f"订单号只能包含字母和数字: {raw!r}")
    return text


# ---------------------------------------------------------------------------
# 1. 正常路径参数化
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("A1001", "A1001"),
        ("  A1001  ", "A1001"),
        ("B2", "B2"),
        ("C9999", "C9999"),
    ],
    ids=["plain", "with-spaces", "short", "long"],
)
def test_parse_ok(raw: str, expected: str) -> None:
    assert parse_order_id(raw) == expected


# ---------------------------------------------------------------------------
# 2. 异常路径参数化：同一个函数，多种非法输入
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "raw",
    ["", "   ", "1001", "a1001", "A-1001"],
    ids=["empty", "blank", "no-prefix", "lowercase-prefix", "has-dash"],
)
def test_parse_rejects(raw: str) -> None:
    """非法输入必须抛 ValueError。

    ★ pytest.raises 是上下文管理器，相当于 JUnit 的 assertThrows：
          with pytest.raises(ValueError):
              parse_order_id(raw)

    ★ 断言不能写在 with 块内部：块内语句在抛出异常后就中断了，永远执行不到。
      需要检查异常内容时，用 `as excinfo` 取出异常对象，在块外断言。
    """
    with pytest.raises(ValueError):
        parse_order_id(raw)


# ---------------------------------------------------------------------------
# 3. 同时校验异常消息
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    ("raw", "fragment"),
    [
        ("", "不能为空"),
        ("a1001", "大写字母"),
        ("A-1001", "只能包含"),
    ],
)
def test_parse_error_message(raw: str, fragment: str) -> None:
    """异常消息必须包含指定关键字。

    ★ pytest.raises 的返回值携带异常对象：
          with pytest.raises(ValueError) as excinfo:
              ...
          assert fragment in str(excinfo.value)
    """
    with pytest.raises(ValueError) as excinfo:
        parse_order_id(raw)

    assert fragment in str(excinfo.value), f"异常消息应包含 {fragment!r}: {excinfo.value}"


# ---------------------------------------------------------------------------
# 4. 边界：参数化同样可以只验证「不抛异常」
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("raw", ["A", "Z9", "  A  "])
def test_parse_accepts_edge_cases(raw: str) -> None:
    assert parse_order_id(raw) == raw.strip()

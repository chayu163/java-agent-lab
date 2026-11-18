"""Day 4 · 练习 3：Mock 与 patch。

Mock 生成一个假对象，返回值可控，并记录调用次数与参数。
patch 把被测代码引用的名字临时替换成假对象，退出时还原。

运行：uv run pytest day04/python/03_mock_test.py -v
"""

import sys
from unittest.mock import AsyncMock, Mock, patch

THIS = sys.modules[__name__]


def fetch_price(sku: str) -> float:
    """真实实现会发起网络请求。"""
    raise RuntimeError("真实实现")


def total_price(sku: str, quantity: int) -> float:
    return fetch_price(sku) * quantity


# ---------------------------------------------------------------------------
# 1. Mock：构造假对象直接使用
# ---------------------------------------------------------------------------


def test_mock() -> None:
    fake = Mock()
    fake.return_value = 9.9

    assert fake("A1") == 9.9
    fake.assert_called_once_with("A1")


# ---------------------------------------------------------------------------
# 2. patch：替换 total_price 内部引用的 fetch_price
# ---------------------------------------------------------------------------


def test_patch() -> None:
    """让 fetch_price 返回 9.9，断言 total_price("A1", 2) 等于 19.8。

    ★ patch 的目标是「查找的位置」，不是「定义的位置」。
      total_price 在本模块命名空间中查找 fetch_price，因此替换 THIS 上的属性。
    """
    with patch.object(THIS, "fetch_price", return_value=9.9):
        assert total_price("A1", 2) == 19.8

    # 退出 with 块后自动还原
    try:
        total_price("A1", 2)
    except RuntimeError:
        pass
    else:
        raise AssertionError("patch 应已还原为真实实现")


# ---------------------------------------------------------------------------
# 3. AsyncMock：被替换的是 async def 时使用
# ---------------------------------------------------------------------------


async def fetch_async(sku: str) -> float:
    raise RuntimeError("真实实现")


async def test_async_mock() -> None:
    """用 AsyncMock 替换 fetch_async，断言 await 得到 5.0。

    ★ AsyncMock(return_value=5.0) 的调用返回真实协程，await 才能取得结果；
      Mock 的返回值为普通对象，无法 await。
    ★ 测试函数本身要声明为 async def，才能使用 await。

    ❌ 原写法：
    ❌     fake = AsyncMock(return_value=5.0)
    ❌     await fake("A1")
    ❌     fake.assert_called_once_with("A1")
    ❌ 该测试全程未引用 fetch_async，验证对象与被测代码无关：
    ❌ 删除 fetch_async 后它依然通过。

    ✅ mock 的作用是替代被测代码引用的对象，因此被测代码必须实际使用到它。
    """
    with patch.object(THIS, "fetch_async", new=AsyncMock(return_value=5.0)):
        assert await fetch_async("A1") == 5.0

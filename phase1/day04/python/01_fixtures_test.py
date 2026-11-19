"""Day 4 · 练习 1：fixture —— 名称注入，而非自动执行

本文件确认三点：

1. fixture 通过参数名注入：只有声明了该参数的测试才能获得它。
2. fixture 可以依赖 fixture：pytest 依据参数自动按依赖顺序创建。
3. scope 决定 fixture 的创建次数：function（默认）每次测试新建，module 整文件共用一个实例。

运行：uv run pytest day04/python/01_fixtures_test.py -v
"""

from collections.abc import Iterator

import pytest


class FakeRepo:
    """内存仓库，用于观察 fixture 返回的实例是否独立。"""

    def __init__(self) -> None:
        self.items: dict[str, str] = {}

    def add(self, key: str, value: str) -> None:
        self.items[key] = value

    def get(self, key: str) -> str:
        return self.items[key]


class Counter:
    """累加计数器，用于观察 scope 对实例生命周期的影响。"""

    def __init__(self) -> None:
        self.value = 0

    def bump(self) -> int:
        self.value += 1
        return self.value


# 1. 最简单的 fixture：返回干净的 repo


@pytest.fixture
def repo() -> FakeRepo:
    """每个测试函数获得独立实例，function scope 下测试之间不共享状态。"""
    return FakeRepo()


@pytest.fixture
def seeded(repo: FakeRepo) -> FakeRepo:
    """在 repo 基础上预置两条数据：A1 -> paid，A2 -> shipped。

    依赖 repo fixture：声明 repo 参数后，pytest 先创建 repo 再传入，
    无需在函数体内调用。
    """
    repo.add("A1", "paid")
    repo.add("A2", "shipped")
    return repo


# 2. yield fixture：setup 与 teardown 写在同一函数内


@pytest.fixture
def checkout(repo: FakeRepo) -> Iterator[FakeRepo]:
    """测试执行前写入 order-1，结束后删除，teardown 在测试成功或失败时都执行。

    返回类型标注为 Iterator[FakeRepo] 而非 FakeRepo：含 yield 的函数返回生成器，
    pytest 依据此形状定位 setup 与 teardown 的分界。
    """
    repo.add("order-1", "pending")
    yield repo
    del repo.items["order-1"]


# 3. scope：function（默认）与 module


@pytest.fixture
def per_test_counter() -> Counter:
    """function scope：每个测试获得独立实例。"""
    return Counter()


@pytest.fixture(scope="module")
def per_module_counter() -> Counter:
    """module scope：整个文件共用一个实例，与 function scope 的差别仅在 scope 参数。"""
    return Counter()


# 测试


def test_repo_starts_empty(repo: FakeRepo) -> None:
    assert repo.items == {}


def test_each_test_gets_a_fresh_repo(repo: FakeRepo) -> None:
    # 上一个测试写入的数据不会残留，function scope 在每次测试前重建实例
    assert repo.items == {}


def test_seeded_has_two_items(seeded: FakeRepo) -> None:
    assert len(seeded.items) == 2
    assert seeded.get("A1") == "paid"
    assert seeded.get("A2") == "shipped"


def test_seeded_does_not_leak_into_plain_repo(repo: FakeRepo) -> None:
    assert repo.items == {}


def test_checkout_has_the_order(checkout: FakeRepo) -> None:
    assert checkout.get("order-1") == "pending"


def test_checkout_starts_with_exactly_one_item(checkout: FakeRepo) -> None:
    # checkout 在上一个测试中使用过，此处仍是独立实例，数据不累积
    assert len(checkout.items) == 1, f"期望只有一个元素: {checkout.items}"


def test_yield_fixture_teardown_actually_runs() -> None:
    """不经过 pytest 驱动 yield 生成器，验证 yield 之后的代码确实执行。

    next() 推进至 yield 完成 setup，再次 next() 触发 StopIteration 完成 teardown。
    这说明 yield fixture 本质是普通生成器，pytest 只负责驱动它。
    """
    events: list[str] = []
    holder: dict[str, str] = {}

    def gen() -> Iterator[dict[str, str]]:
        holder["order-1"] = "pending"
        events.append("setup")
        yield holder
        del holder["order-1"]
        events.append("teardown")

    g = gen()
    got = next(g)
    assert got == {"order-1": "pending"}
    assert events == ["setup"], "yield 之前只应执行 setup"

    with pytest.raises(StopIteration):
        next(g)
    assert events == ["setup", "teardown"], f"yield 之后必须执行: {events}"
    assert holder == {}, "teardown 必须清除数据"


def test_function_scope_is_fresh(per_test_counter: Counter) -> None:
    assert per_test_counter.bump() == 1


def test_function_scope_is_fresh_again(per_test_counter: Counter) -> None:
    # 返回 2 表示 fixture 复用了实例，未按 function scope 创建
    assert per_test_counter.bump() == 1


def test_module_scope_first(per_module_counter: Counter) -> None:
    assert per_module_counter.bump() == 1


def test_module_scope_second(per_module_counter: Counter) -> None:
    # module scope 复用同一实例，因此累计值为 2
    # 本测试依赖执行顺序，仅用于展示 scope 差异，生产代码不应依赖测试顺序
    assert per_module_counter.bump() == 2

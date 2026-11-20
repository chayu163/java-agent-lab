# Day 4 · pytest：用测试约束行为

## 学习目标

学习 pytest 收集与执行测试、按需创建 fixture、用参数化覆盖输入、替换外部依赖，并验证异步函数的行为。重点是让失败结果能说明“哪个约定被违反”。

## 1. 测试函数如何运行

pytest 默认按文件名 `test_*.py` / `*_test.py` 和函数名前缀 `test_` 收集测试。执行测试时可粗略看成 setup、call、teardown 三段。

```mermaid
flowchart LR
    collect[收集测试] --> setup[setup<br/>解析并创建 fixture]
    setup --> call[call<br/>执行测试函数]
    call --> teardown[teardown<br/>执行 fixture 清理]
    teardown --> report[生成结果报告]
    setup -. 失败 .-> error[ERROR]
    call -. 断言失败或异常 .-> failed[FAILED]
    teardown -. 清理失败 .-> error
```

`assert actual == expected` 使用 Python 的原生断言。pytest 会展示表达式中的实际值，便于定位差异。`FAILED` 常见于测试调用阶段断言失败或异常，`ERROR` 常见于 fixture 或清理阶段失败；应结合 traceback 判断。

## 2. fixture：按名称请求测试依赖

fixture 不是默认执行的 `@BeforeEach`。测试参数名与 fixture 名匹配时，pytest 才解析并注入它。

下面是说明注入关系的简化示例；`FakeRepo` 和 `pytest` 导入省略。

```python
@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()


def test_add(repo: FakeRepo) -> None:
    assert repo.add("A1") is True
```

`FakeRepo` 表示测试用的隔离对象。fixture 可以依赖其他 fixture。默认 `scope="function"`，每个测试函数各自创建；扩大作用域能复用昂贵资源，但需要显式重置状态或回滚事务，避免测试互相污染。

需要清理的资源可用 `yield` fixture：

下面的 `Connection` 类型与 `connect()` 由应用提供，`Iterator` 来自 `collections.abc`。

```python
from collections.abc import Iterator

import pytest


@pytest.fixture
def connection() -> Iterator[Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
```

`yield` 前是 setup，yield 的值传给测试，yield 后是 teardown。测试失败时 pytest 仍会执行 yield 后的清理；如果 setup 在到达 yield 前失败，该 fixture 的 yield 后代码不会运行。

## 3. 参数化与异常断言

多组输入共享同一行为时，用 `parametrize`，每组会成为独立测试用例：

```python
import pytest


@pytest.mark.parametrize(
    ("raw", "expected"),
    [("A1001", "A1001"), ("  A1001  ", "A1001")],
    ids=["plain", "with-spaces"],
)
def test_parse(raw: str, expected: str) -> None:
    assert parse_order_id(raw) == expected
```

假设 `parse_order_id` 是已定义的被测函数，异常也是它的行为契约，可以验证异常类型或消息：

```python
import pytest


with pytest.raises(ValueError, match="不能为空"):
    parse_order_id("")
```

异常出现后控制流会离开 `with` 块。需要检查异常对象时，使用 `as exc_info`，并在块外断言。

## 4. 外部依赖如何替换

优先使用显式依赖注入。Day 3 的 `fetch_all(..., transport=...)` 接受 httpx transport，测试可传入 `MockTransport` 模拟状态码、延迟、超时和连接异常。

```text
测试数据 ──> 被测 fetch_all ──> MockTransport ──> 可控响应
```

如果被测模块内部直接查找一个名称，`patch` 或 `monkeypatch` 可以临时替换该查找位置。目标是被测代码实际使用的绑定，不一定是函数最初定义的位置。

`Mock()` 用于同步调用，`AsyncMock()` 用于异步调用。网络、数据库等外部系统的单元测试应使用替身保持可重复；真实兼容性另由集成测试验证。

## 5. 异步测试与覆盖率

仓库配置 `asyncio_mode = "auto"`，因此异步测试可写成 `async def test_...`。pytest-asyncio 负责在事件循环中驱动测试，不要在其中嵌套调用 `asyncio.run()`。

覆盖率报告显示代码行或分支是否执行过，不证明断言有效，也不能证明输入情况充分。优先覆盖业务边界和错误路径，不需要追逐固定百分比。

```bash
uv run pytest phase1/day04 -q
uv run pytest phase1/day04 --cov=phase1/day03/python --cov-report=term-missing
```

## 练习入口

| 文件 | 目标 |
|---|---|
| `python/01_fixtures_test.py` | fixture 注入、作用域与资源清理 |
| `python/02_parametrize_test.py` | 多组输入和异常断言 |
| `python/03_mock_test.py` | Mock、patch、monkeypatch、AsyncMock |
| `python/test_fetch.py` | 给 Day 3 的 fetch 逻辑写五个行为测试 |

先运行 `uv run pytest phase1/day04 -q`，再看失败项对应哪个约定。练习完成后，用 [Day 4 笔记](../../notes/phase1/day04/pytest.md)复盘 fixture 失败阶段、替身边界和测试覆盖范围。

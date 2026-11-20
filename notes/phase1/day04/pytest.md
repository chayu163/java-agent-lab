---
title: Day 4 · pytest：把行为变成可重复验证
date: 2026-11-18
day: 4
phase: 1
tags:
  - ai-agent-30d
  - python
  - testing
status: done
---

# Day 4 · pytest：把行为变成可重复验证

## 学完后应能

- 根据测试函数签名判断 pytest 会注入哪些 fixture。
- 用参数化覆盖输入集合，用 `pytest.raises` 验证异常约定。
- 选择依赖注入、MockTransport、Mock 或 patch 隔离外部边界。
- 读懂异步测试的运行条件，并说明覆盖率能回答和不能回答的问题。

当天代码：[fixture 练习](../../../phase1/day04/python/01_fixtures_test.py)、[参数化练习](../../../phase1/day04/python/02_parametrize_test.py)、[mock 练习](../../../phase1/day04/python/03_mock_test.py)、[fetch 测试](../../../phase1/day04/python/test_fetch.py)。

## 1. pytest 如何发现和运行测试

pytest 按文件名、函数名和可选的测试类命名规则收集测试。仓库的 `pyproject.toml` 配置 `asyncio_mode = "auto"`，因此 pytest-asyncio 会处理符合约定的 `async def test_...`。

```bash
uv run pytest phase1/day04 -q
uv run pytest phase1/day04 -v
uv run pytest phase1/day04 -x
```

`-q` 显示简洁汇总，`-v` 显示逐项结果，`-x` 在第一个失败后停止。退出码 `0` 表示收集到的测试通过；非零表示存在失败、错误或收集问题。

pytest 的 `FAILED` 通常表示测试调用阶段断言失败或代码抛出未预期异常。`ERROR` 常见于 fixture setup/teardown 或插件阶段失败。teardown 错误发生时，测试函数可能已经执行过，因此不能把 ERROR 一概描述为“测试函数尚未开始”。

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

`FAILED` 和 `ERROR` 标识失败发生的阶段，不代表缺陷一定属于被测业务代码或 fixture。报告要结合具体 traceback 判断。

与 JUnit 对照，pytest 的 `assert` 通常能显示表达式中的实际值，不必为每种比较调用专用断言方法。pytest 仍可运行 `unittest.TestCase`，两种风格可以共存。

## 2. fixture 是按需请求的测试依赖

fixture 名称可作为测试函数参数：

下面的片段省略 `FakeRepo` 的业务实现，只展示 fixture 的声明与注入。

```python
@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()


def test_add(repo: FakeRepo) -> None:
    ...
```

测试函数声明 `repo` 后，pytest 才为该测试解析并注入它。fixture 也可以请求其他 fixture，pytest 按依赖关系安排创建和清理。这比 `@BeforeEach` 更像测试函数显式声明依赖，但 pytest 也提供 `autouse=True`、`usefixtures` 等自动使用方式。

默认 `scope="function"`，每个测试函数各自创建 fixture。更大的 scope 会跨测试复用对象，能减少昂贵 setup，但需要明确重置状态、事务回滚或其他隔离方式。共享资源不必只读，关键是测试之间不能互相污染。

### 用 yield 管理清理

下面的 `Connection` 类型与 `connect()` 由应用提供。

```python
@pytest.fixture
def connection() -> Iterator[Connection]:
    conn = connect()
    try:
        yield conn
    finally:
        conn.close()
```

`yield` 前是 setup，yield 的值注入测试，yield 后是 teardown。测试失败时 pytest 仍会执行 yield 后的清理；如果 setup 在到达 yield 前就抛异常，yield 后的代码不会运行，因此 setup 本身已分配的资源应有适当的异常清理。

`conftest.py` 里的 fixture 可供所在目录及子目录中的测试使用，无需测试模块显式 import。它是 pytest 的发现机制，不是 Python 的一般隐式导入规则；pytest 还支持插件提供 fixture。

## 3. 参数化让一组输入共享同一行为断言

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [("A1001", "A1001"), ("  A1001  ", "A1001")],
    ids=["plain", "with-spaces"],
)
def test_parse_order_id(raw: str, expected: str) -> None:
    assert parse_order_id(raw) == expected
```

每组参数是独立用例。某组失败不会阻止其他组运行，`ids` 让失败案例在报告中容易辨认。它与 JUnit 参数化测试用途相近，具体语法和插件能力不同。

假设 `parse_order_id` 是被测函数，异常是它的行为契约时，用 `pytest.raises`：

```python
import pytest


with pytest.raises(ValueError, match="不能为空"):
    parse_order_id("")
```

异常抛出后，控制流离开 `with` 块。因此检查捕获到的异常应写在块外：

```python
with pytest.raises(ValueError) as exc_info:
    parse_order_id("")

assert exc_info.type is ValueError
```

## 4. Mock、patch 与传入替身

`Mock()` 创建一个可配置的同步假对象；`AsyncMock()` 用于异步调用，调用后返回可等待对象；`patch()` 临时替换名称。它们解决的问题不同。

```python
from unittest.mock import Mock


fake_repo = Mock()
fake_repo.find.return_value = {"id": "A1"}

assert fake_repo.find("A1") == {"id": "A1"}
fake_repo.find.assert_called_once_with("A1")
```

当代码内部直接引用模块名称时，patch 必须作用于被测代码运行时查找的绑定位置。例如 `service.py` 使用 `from pricing import fetch_price`，之后调用的是 `service.fetch_price`，通常应 patch `service.fetch_price`。

若函数已经提供依赖注入点，优先直接传入替身。Day 3 的 `fetch_all(transport=...)` 使用 httpx `MockTransport`，可以模拟状态码、超时和连接错误，同时保留 httpx 请求流程。需要验证真实网络、数据库或服务兼容性时，另写集成测试。

## 5. pytest-asyncio 与当前仓库配置

仓库使用 `asyncio_mode = "auto"`。在该配置下，异步测试可直接写成 `async def test_...`。pytest-asyncio 的事件循环作用域由插件配置和 fixture scope 决定；本仓库显式设置 function scope，使普通异步测试分别运行在各自的循环中。

不要在由 pytest-asyncio 驱动的异步测试里再调用 `asyncio.run()`。此时已经有运行中的事件循环，`asyncio.run()` 会拒绝嵌套启动。

Day 3 的请求客户端也需要关闭。测试若创建真实 `AsyncClient`，应通过异步 fixture 或上下文管理器管理；使用 `MockTransport` 不代表可以省略 client 生命周期。

## 6. 覆盖率是观测数据，不是正确性证明

```bash
uv run pytest phase1/day04 --cov=phase1/day03/python --cov-report=term-missing
```

行覆盖率说明哪些行在本次测试中运行过；分支覆盖率进一步显示条件分支是否都走到。它们不能证明断言正确、输入空间充分或外部服务兼容。无需追求某个固定百分比，优先补充高风险行为和错误路径。

一个简单的断言质量检查方法是暂时破坏被测行为，确认相关测试会失败。测试没有失败时，检查断言是否真的约束了目标结果。

## 7. 五个 fetch 测试要锁定的行为

[test_fetch.py](../../../phase1/day04/python/test_fetch.py) 为 Day 3 抓取代码验证以下行为：

| 类别 | 输入情形 | 应验证 |
|---|---|---|
| 成功 | 多个 URL 均成功 | 每条结果正确，返回顺序与输入顺序相同 |
| 混合 | 一条请求超时，其余成功 | 超时转换为该请求的错误结果，不丢失其他结果 |
| 计时 | 单条请求超时 | 超时结果仍有可解释的耗时值 |
| HTTP 错误 | 服务返回 500 | 状态错误被表示为失败结果 |
| 连接错误 | 传输层无法连接 | 错误被归一化，不让整批请求异常退出 |

测试时重点确认错误标签与 Day 3 实际实现一致，而不是仅确认某个字段存在。

## 自测

- fixture 默认何时创建？一个测试不声明该 fixture 会发生什么？
- yield 前 setup 失败时，yield 后的 teardown 会运行吗？
- 参数化的一组数据失败后，其他参数组会继续吗？
- patch 应替换函数定义处的名称，还是被测模块查找的名称？
- `Mock` 和 `AsyncMock` 的调用结果有何区别？
- 行覆盖率达到 100% 能证明哪些事，又不能证明哪些事？
- 为什么 fetch 测试使用 MockTransport，而不是每次访问公共网络？

## 下一步

Day 5 会把 mock 模型、工具注册表、消息协议和异步执行组合成一个可测试的 Agent 工具调用循环。

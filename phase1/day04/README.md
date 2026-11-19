# Day 4 · pytest 知识树

Day 3 的代码只需能运行；Day 4 要求改动出错时能被发现。测试不是额外工作量，而是能够安全修改代码的前提，阶段 5 的项目每天都需要改动。

```text
pytest
│
├─ ① 心智模型：与 JUnit 的根本差别
│   ├─ 测试是普通函数，不继承 TestCase
│   ├─ 断言使用原生 assert，失败时 pytest 重写并打印差异
│   └─ 收集规则：文件名 test_*.py / *_test.py，函数名 test_*
│
├─ ② 测试替身：fixture
│   ├─ 与 @BeforeEach / @BeforeAll 的区别：不是自动执行，而是按名称注入
│   ├─ scope：function / class / module / session
│   ├─ yield fixture：setup 与 teardown 写在同一函数内
│   └─ conftest.py：跨文件共享，按目录层级生效
│
├─ ③ 数据驱动：parametrize
│   ├─ 对应 @ParameterizedTest + @CsvSource
│   └─ 每个参数组合是一条独立用例，单项失败不影响其余
│
├─ ④ 隔离外部：mock
│   ├─ unittest.mock 与 Mockito 的对应：Mock / MagicMock / AsyncMock
│   ├─ patch 装饰器、上下文管理器、monkeypatch
│   └─ 异步函数必须用 AsyncMock，Mock 的返回值不是协程
│
├─ ⑤ 异步测试：pytest-asyncio
│   ├─ asyncio_mode = "auto"，无需逐个挂装饰器
│   └─ 事件循环本身由 fixture 提供，可以替换
│
└─ ⑥ 度量：coverage
    ├─ 行覆盖与分支覆盖
    └─ 覆盖率是下限，不是目标
```

---

## 一、心智模型：与 JUnit 的根本差别

| JUnit 5 | pytest | 差别 |
|---|---|---|
| `class FooTest { @Test void x() }` | `def test_x():` | 不需要类，不需要继承 |
| `assertEquals(a, b)` | `assert a == b` | 使用 Python 原生 `assert` |
| `assertThrows(E.class, ...)` | `with pytest.raises(E):` | 上下文管理器 |
| `@BeforeEach` | fixture | 不是自动执行的钩子，而是按名称请求的依赖 |
| `@ParameterizedTest` | `@pytest.mark.parametrize` | 名称不同，语义一致 |
| Mockito `mock(Foo.class)` | `unittest.mock.Mock()` | Python 可 mock 任何对象，包括模块级函数 |
| `src/test/java` 固定目录 | 任意位置，只认文件名 | 收集依赖命名约定 |

第二项值得展开。JUnit 的断言失败只说明 "expected true but was false"。pytest 会重写 assert 语句，把中间值全部打印出来：

```text
E       assert {'a': 1} == {'a': 2}
E         Common items:
E         {'a': 1}
E         Differing items:
E         {'a': 1} != {'a': 2}
```

因此写 `assert result == expected` 即可，不需要 `assertEqual` / `assertContains` 之类的专用方法。

> [!note] 不使用 unittest 的原因
> 标准库的 `unittest` 是 Python 版的 JUnit：继承 `TestCase`、使用 `self.assertEqual`。
> 它可以运行，但样板代码多、断言信息弱、没有 fixture 注入。pytest 是行业默认选择。

---

## 二、fixture：最容易被误读的一节

初学者常把 fixture 等同于 `@BeforeEach`，这是错误的。差别在于：

- `@BeforeEach`：每个测试方法前自动执行，无法选择。
- fixture：测试函数在参数中声明才注入；未声明的测试不受影响。

```python
@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()


def test_add(repo):
    # 参数名匹配即注入
    ...
```

因此 fixture 的三要素是名称、作用域、依赖。一个 fixture 可以依赖另一个 fixture，pytest 按依赖图拓扑排序地创建它们。

### 三种写法

```python
# 1. 直接返回
@pytest.fixture
def client() -> httpx.AsyncClient:
    return httpx.AsyncClient()


# 2. setup 与 teardown 合一（yield 之前是 setup，之后是 teardown）
@pytest.fixture
def db():
    conn = connect()
    yield conn
    conn.close()  # 测试结束或失败都会执行


# 3. 工厂：一个 fixture 生成多个对象
@pytest.fixture
def make_order():
    def _make(order_id: str) -> Order:
        return Order(order_id)

    return _make
```

> [!tip] yield fixture 即 Day 2 的生成器
> `yield` 之前对应 `__enter__`，之后对应 `__exit__`，与 `@contextmanager` 是同一机制。
> Day 2 所述「yield 把函数切成两段」在这里直接复用。

### scope

| scope | 每个 scope 创建次数 | JUnit 对应 |
|---|---|---|
| `function`（默认） | 每个测试函数一次 | `@BeforeEach` |
| `class` | 每个测试类一次 | `@BeforeAll`（非 static 版） |
| `module` | 每个文件一次 | 无直接对应 |
| `session` | 整个测试运行一次 | `@BeforeAll` + static |

默认是 function scope，因此测试之间天然隔离。只有需要共享昂贵资源（数据库连接、容器）时才使用更大的 scope，并且要保证该资源只读，或每次自行清理，否则测试之间会互相污染。

### conftest.py

放在某一目录下的 `conftest.py`，其中的 fixture 对该目录及子目录下所有测试可见，无需 import。这是 pytest 唯一的隐式导入机制。

---

## 三、parametrize：数据驱动

```python
@pytest.mark.parametrize(
    ("text", "expected"),
    [
        ("a,b", ["a", "b"]),
        ("a", ["a"]),
        ("", []),
    ],
    ids=["two", "one", "empty"],
)
def test_split(text: str, expected: list[str]) -> None:
    assert text.split(",") == expected
```

对应 Java：

```java
@ParameterizedTest
@CsvSource({"a,b|a;b", "a|a"})
void testSplit(String text, String expected) { ... }
```

关键差异：每个参数组合是一条独立用例。5 条数据中第 3 条失败时，报告显示 `test_split[empty]` 失败、其余 4 条通过。JUnit 的 `@ParameterizedTest` 行为相同，但 pytest 的 `ids=` 可以控制显示名，报告可读性更高。

---

## 四、mock：隔离外部世界

测试的基本原则：只测自身逻辑，不测网络、数据库、时钟。

```python
from unittest.mock import AsyncMock, Mock, patch

# 1. 构造假对象
repo = Mock()
repo.find.return_value = {"id": "A1"}
repo.find("A1")  # {"id": "A1"}
repo.find.assert_called_once_with("A1")

# 2. 替换模块中的名称（patch）
with patch("myapp.service.fetch_price", return_value=9.9):
    assert myapp.service.total() == 9.9


# 3. pytest 风格的 monkeypatch（更轻量，自动还原）
def test_x(monkeypatch):
    monkeypatch.setattr("myapp.service.fetch_price", lambda: 9.9)
```

| 需求 | 使用 |
|---|---|
| 构造假对象并检查调用 | `Mock()` |
| 假对象的属性也需要可用 | `MagicMock()` |
| 伪造 `async def` | `AsyncMock()` |
| 替换模块级名称 | `patch()` 或 `monkeypatch.setattr` |
| 修改环境变量或时间 | `monkeypatch.setenv` / `monkeypatch.setattr(time, ...)` |

> [!danger] 异步函数必须使用 AsyncMock
> 用 `Mock()` 冒充协程时，`await mock_fn()` 得到的是 Mock 对象而非真实协程。
> `AsyncMock()` 的调用返回真实协程，`await` 才能取得结果。

> [!warning] patch 的路径是「查找的位置」，不是「定义的位置」
> 服务代码写 `from utils import fetch_price` 时，该名称已绑定到服务模块的命名空间，
> 必须 patch `myapp.service.fetch_price`；patch `utils.fetch_price` 不会生效。
> 习惯直接 mock 类的 Java 开发者最容易在此出错。

---

## 五、pytest-asyncio

Day 3 的代码是异步的，测试也必须是异步的。

```toml
[tool.pytest.ini_options]
asyncio_mode = "auto"
```

开启 `auto` 后，`async def test_xxx()` 可直接运行，无需为每个函数添加 `@pytest.mark.asyncio`。

两点需要注意：

1. **每个测试获得一个新的事件循环**（默认 function scope）。因此在一个测试中创建的资源不会延续到另一个测试，这正是所需的隔离。
2. **不要在测试中调用 `asyncio.run()`**。pytest-asyncio 已经在循环中运行测试，再套一层会报 "asyncio.run() cannot be called from a running event loop"。

---

## 六、coverage

```bash
uv run pytest phase1/day04 --cov=phase1/day03/python --cov-report=term-missing
```

`term-missing` 会列出未被执行的**行号**，比百分比更有参考价值。

| 指标 | 含义 | 用途 |
|---|---|---|
| 行覆盖 | 被执行过的行占比 | 定位遗漏 |
| 分支覆盖 | `if` 的两个分支是否都执行过 | 比行覆盖更容易发现漏测 |

> [!important] 覆盖率是下限，不是目标
> 100% 覆盖不等于没有缺陷。它只证明每行都执行过，不证明每种输入组合都正确。
> 实用目标：核心业务路径 80% 以上，错误分支必须覆盖（错误分支最容易写错）。
> 为提升覆盖率而写 `assert True` 没有实际意义。

---

## 七、当日产出

**为 Day 3 的 `05_fetch.py` 编写 5 个测试：3 个成功路径加 2 个错误路径。**

这 5 个测试覆盖 Day 3 该文件中的四类缺陷：

| # | 类型 | 验证内容 | 可发现的缺陷 |
|---|---|---|---|
| 1 | 成功 | 5 个 URL 全部成功，结果保持顺序 | `gather` 误用、顺序错乱、返回类型不符 |
| 2 | 成功 | 单个超时不影响其余 4 个 | 异常未捕获，整批失败 |
| 3 | 成功 | 超时项的 `elapsed_ms` 合理（约等于 timeout） | 计时写在 timeout 内部导致值为 None |
| 4 | 错误 | 500 被归一化为 `http_500` | 将非 200 计入成功 |
| 5 | 错误 | 连接失败被归一化为 `http_error: ...`，不抛异常 | 异常穿透到调用方 |

文件：`phase1/day04/python/test_fetch.py`。导入 Day 3 模块的样板代码已写好
（`05_fetch.py` 文件名以数字开头，不能直接 `import`，需使用 `importlib`），只需填写 5 个测试函数。

另外三个练习文件，按树的顺序：

| 文件 | 对应层 | 内容 |
|---|---|---|
| `python/01_fixtures_test.py` | ② fixture | 作用域、yield teardown、fixture 依赖 fixture |
| `python/02_parametrize_test.py` | ③ 数据驱动 | 参数化、`pytest.raises` 参数化 |
| `python/03_mock_test.py` | ④ mock | Mock / patch / monkeypatch / AsyncMock |

运行方式：

```bash
uv run pytest phase1/day04 -v
```

初始状态下大量用例失败，失败项即待填清单。

> [!tip] 先验证断言有效，再验证代码正确
> 写完测试后，故意修改被测代码的一行，再运行一次，观察测试是否失败。
> 测试未失败说明断言无效。这一步区分「写了测试」与「写了有效断言」。

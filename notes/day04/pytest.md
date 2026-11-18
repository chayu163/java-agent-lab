---
title: Day 4 · pytest 与测试替身
date: 2026-11-18
day: 4
phase: 1
tags:
  - ai-agent-30d
  - python
  - testing
status: done
---

# Day 4 · pytest 与测试替身

> [!abstract] 产出
> `day04/python/` 四个测试文件 · `day04/README.md`（知识树）· 本篇笔记
> 验收：`uv run pytest day04 -q` → 34 passed

> [!tip] 一句话
> **测试不是验证代码是否正确，而是把「应该没问题」这类假设，变成机器每次改动后都会重跑的断言。**

---

## 全景

```text
pytest
│
├─ 执行模型    没有 main 函数，pytest 是入口
├─ fixture     按名称注入的依赖，不是自动执行的钩子
├─ parametrize 一张表展开成 N 条独立用例
├─ mock        隔离外部世界：时间、网络、第三方服务
└─ coverage    下限而非目标
```

---

## 一、测试与一次性验证的区别

Day 3 完成 `05_fetch.py` 时的验证方式：打印结果，运行一次，人工判断正确与否，然后继续。

这已经是一次测试，只是存在三个缺陷：

| 缺陷 | 后果 |
|---|---|
| 只有人能判断对错 | 输出面向人，不面向机器 |
| 运行后即消失 | 后续改动不会触发重新验证 |
| 只覆盖当时想到的输入 | 未想到的场景永远不被检验 |

测试做的事只有一件：把那次临时的打印与人工判断，换成一行永久留在仓库中、机器可判定的断言。

> [!important] 判断标准：这段代码是否会被修改第二次
> 只运行一次的脚本不需要测试。会被反复修改、反复调用的代码，缺少测试的代价会随改动次数累积。
> 阶段 5 的项目连续修改十天，没有测试则第五天无法安全改动第一天的代码。

---

## 二、执行模型

### 没有 `main`，因为 pytest 就是入口

Day 1-3 的文件末尾都有 `if __name__ == "__main__"`，Day 4 的测试文件全部省略。这是刻意设计，不是遗漏。

| | Day 1-3 的文件 | Day 4 的文件 |
|---|---|---|
| 性质 | 脚本 | 测试 |
| 执行入口 | 文件自身 | `pytest` 命令 |
| 是否需要 `__main__` | 需要 | 不需要 |

Java 的对应关系一致：JUnit 测试类没有 `main`，由 Runner 扫描 `@Test` 注解执行。pytest 用命名约定替代注解。

| 收集对象 | 规则 |
|---|---|
| 文件 | `test_*.py` 或 `*_test.py` |
| 函数 | 函数名以 `test` 开头 |
| 类 | 类名以 `Test` 开头且无 `__init__`（本次未使用） |

### 三种状态的含义不同

| 状态 | 含义 | 排查方向 |
|---|---|---|
| `PASSED` | 函数执行完毕，所有断言成立 | — |
| `FAILED` | 函数已执行，某条断言不成立 | 被测代码或断言本身 |
| `ERROR` | 函数未开始执行 | fixture、导入、语法 |

> [!warning] ERROR 与 FAILED 的区分
> `ERROR` 发生在 setup 阶段。本次首次运行出现三个 error，原因是 `seeded` 与 `checkout` 中仍是
> `raise NotImplementedError`，pytest 在构造 fixture 时即失败，测试函数体一行未执行。
> 遇到 ERROR 应先检查 fixture，而非被测代码。

### 判断是否通过

```bash
uv run pytest day04 -q        # 汇总：34 passed in 0.42s
uv run pytest day04 -v        # 逐条显示 PASSED / FAILED
uv run pytest day04 -x        # 首个失败即停止
```

最终判定依据是退出码：`0` 表示全部通过，`1` 表示存在失败。CI 依据这个数值决定流水线状态。

---

## 三、fixture：按名称注入的依赖

### 机制

```python
@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()

def test_x(repo: FakeRepo):    # 参数名匹配即注入
    ...
```

要素有三项：名称、作用域、依赖。fixture 之间可以相互依赖，pytest 按依赖关系确定创建顺序。

### 与 `@BeforeEach` 的差别

| | JUnit `@BeforeEach` | pytest fixture |
|---|---|---|
| 执行时机 | 类中每个 `@Test` 方法前都执行 | 仅被执行到它的测试触发 |
| 获取方式 | 隐式，写入字段 | 显式，声明在参数中 |
| 能否跳过 | 不能 | 能 |

实测：定义一个记录调用的 fixture，七个测试中仅一个声明该参数，fixture 只执行一次。

> [!important] 这是依赖注入，不是钩子
> `@pytest.fixture` 的语义是注册一个可按名称请求的工厂，不是标记一个自动执行的钩子。
>
> 与 Spring 的对应关系是 `@Bean` 加 `@Autowired`。区别在于默认作用域相反：
> Spring 默认 singleton，pytest 默认每次新建，相当于 prototype。

### scope 决定创建次数

| scope | 创建次数 | 生命周期 | JUnit 近似 |
|---|---|---|---|
| `function`（默认） | 每个测试函数一次 | 用完即弃 | `@BeforeEach` |
| `class` | 每个测试类一次 | 类执行完毕 | — |
| `module` | 每个文件一次 | 文件执行完毕 | `@BeforeAll` |
| `session` | 整个 pytest 运行一次 | 全部执行完毕 | `@BeforeAll`（static） |

默认使用 `function` 的理由是测试之间必须互不影响。共享实例时，前一个测试写入的状态会成为后一个测试的起点，测试顺序改变即导致结果改变。

提升作用域的前提是两项同时成立：每次重建的成本显著，且能保证状态不互相污染。例如启动一个 PostgreSQL 需要数秒。其余情况一律使用 `function`。

### yield fixture

```python
@pytest.fixture
def db():
    conn = connect()
    yield conn          # setup 与 teardown 的分界
    conn.close()        # 测试成功、失败、异常时均执行
```

其机制是 Day 2 的生成器。手动驱动可以验证：首次 `next()` 执行到 `yield`，setup 完成；再次 `next()` 抛 `StopIteration`，teardown 执行。

---

## 四、parametrize：数据驱动

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [("A1001", "A1001"), ("  A1001  ", "A1001")],
    ids=["plain", "with-spaces"],
)
def test_parse_ok(raw, expected):
    assert parse_order_id(raw) == expected
```

对应 Java 的 `@ParameterizedTest` 与 `@CsvSource`。关键特性是每个参数组合作为独立用例执行，报告中分开显示，单条失败不影响其余。

`ids=` 控制显示名称，失败时可直接定位到具体数据。

### 异常断言

```python
with pytest.raises(ValueError):
    parse_order_id("")

with pytest.raises(ValueError, match="不能为空"):   # match 为正则，写片段即可
    parse_order_id("")

with pytest.raises(ValueError) as excinfo:
    parse_order_id("")
assert excinfo.type is ValueError
```

> [!danger] 断言不能写在 `with` 块内部
> ```python
> with pytest.raises(ValueError) as excinfo:
>     parse_order_id(raw)
>     assert excinfo.type is ValueError     # 不会执行
> ```
> 异常抛出后控制流立即跳出 `with` 块，块内后续语句全部跳过。实测中块内的 append 从未执行。
>
> 需要检查异常内容时，用 `as excinfo` 取出异常对象，在块外断言。

---

## 五、Mock 与 patch：名词与动词

| | 性质 | 词性 |
|---|---|---|
| `Mock()` | 一个对象，假替身 | 名词 |
| `patch(...)` | 一个动作，临时替换名称 | 动词 |

两者可以独立使用：

```python
# 仅使用 Mock：构造假对象后直接调用
fake = Mock(); fake.return_value = 9.9
assert fake("A1") == 9.9

# 仅使用 patch：替换对象与 Mock 无关
with patch.object(THIS, "fetch_price", lambda sku: 1.5):
    assert fetch_price("A1") == 1.5
```

> [!note] patch 替换的是名称，不是函数体
> 替换为整数 `42` 后，`fetch_price("A1")` 抛出 `TypeError: 'int' object is not callable`。
> 该名称此时指向 `42`，调用即等价于 `42("A1")`。

### 选择依据

| 场景 | 选择 | 依据 |
|---|---|---|
| 函数接受参数 | 直接传入 `Mock()` | 存在注入点 |
| 代码内写死了调用 | `patch()` | 只能从外部替换名称 |
| 目标是 `async def` | `AsyncMock()` | Mock 的返回值不是协程 |

判断顺序：先确认是否存在注入点，存在则传参，不存在才使用 patch。

Day 3 的 `fetch_all(transport=...)` 属于保留注入点的设计，测试时传入 `MockTransport`，无需 patch。

### Mock 的三项能力

```python
repo = Mock()                           # 任意属性自动存在
repo.find.return_value = {"id": "A1"}   # 桩：固定返回
repo.find.side_effect = [1.0, 2.0]      # 桩：按序返回或抛异常
repo.find.assert_called_once_with("A1") # 间谍：检查调用
```

`Mock()` 访问任意属性时现场生成子 Mock，因此 `repo.find`、`repo.save` 均"存在"。Java 的 `mock(Repo.class)` 需要 `.class` 才能确定方法集合，Python 不需要。这一差异使 Mock 更灵活，也更容易写出无效测试。

### patch 的路径规则

> [!danger] patch 的目标是查找位置，而非定义位置
> ```python
> # service.py
> from utils import fetch_price      # 名称被复制进 service 的命名空间
> def total(): return fetch_price()  # 使用 service 命名空间中的那一份
> ```
> 必须 `patch("service.fetch_price")`。patch `utils.fetch_price` 无效，service 已持有独立引用。
>
> Java 不存在这一问题：运行时按类加载，没有"复制进命名空间"的环节。

---

## 六、本次练习中的四处错误

四处均不是"不会写"，而是知识停留在可识别、未到达可重现的阶段。

### 错误一：遗漏 `await`，共四处

```python
results = fetch.fetch_all(URLS, timeout=0.1, transport=one_slow)   # 错误
```

`fetch_all` 是 `async def`，不加 `await` 只构造了协程对象，函数体一行未执行。后续 `len(results)` 抛 `TypeError`，进程退出时补充 `RuntimeWarning: coroutine 'fetch_all' was never awaited`。

> [!important] 这不是"已排期但未执行"，是未进入调度
> 实测结论：`await coro()` 不新建 Task；`create_task(coro)` 才把新 Task 的 `__step` 放入 ready 队列。
> 遗漏 `await` 时连 Task 都未创建，协程对象是死的。详见 Day 3 笔记「进入就绪队列的是 Task，不是协程」。

### 错误二：测试了一个与被测代码无关的 mock

```python
fake = AsyncMock(return_value=5.0)
await fake("A1")
fake.assert_called_once_with("A1")     # 全程未涉及 fetch_async
```

删除 `fetch_async` 后该测试仍然通过。它验证的是"刚构造的 mock 能否被调用"，与被测代码无关。

正确写法必须让被测代码使用替换后的对象：

```python
with patch.object(THIS, "fetch_async", new=AsyncMock(return_value=5.0)):
    assert await fetch_async("A1") == 5.0
```

> [!tip] 识别无效测试的方法
> 将被测代码改坏一处后重新运行。测试仍然通过，说明断言没有覆盖该行为。

### 错误三：断言写在 `with pytest.raises` 块内部

见第四节。块内语句在异常抛出后全部跳过。测试仍然通过，因为 `pytest.raises` 本身即是断言，但异常类型与消息实际未被验证。

### 错误四：在 `assert_called_once_with(...)` 前加 `assert`

该方法直接抛出 `AssertionError`，不返回布尔值。`assert <它>` 等价于 `assert None`，恒失败。

```python
repo.find.assert_called_once_with("A1")    # 正确写法，失败时自行抛出
```

---

## 七、测试设计的三个原则

**测行为，不测实现。** 验证"超时返回 `error='timeout'`"，不验证"内部调用了几次 `perf_counter`"。后者在重构时必然失败，而功能未变。

**一个测试只验证一件事。** 本次五个测试对应五个行为。单函数堆叠二十条断言时，失败后无法定位具体原因。

**错误路径必须覆盖。**

| 应当测试 | 理由 |
|---|---|
| 边界值 | 空字符串、零、空列表，缺陷集中区域 |
| 错误路径 | 超时、500、连接中断，最易写错且常规运行不触发 |
| 业务规则 | 状态机、格式校验 |
| 已修复的缺陷 | 每个缺陷配一条测试防止复发 |

不测试：第三方库行为、纯访问器、实现细节。

---

## 八、测试替身存在的两个约束

| | 使用真实外部服务 | 使用替身 |
|---|---|---|
| 耗时 | 五个真实请求约 2 秒，二十个测试约 40 秒 | 全部 0.42 秒 |
| 稳定性 | 断网、限流、服务异常均导致失败 | 仅在自身代码存在缺陷时失败 |

第二条更关键。测试若不能稳定复现，人会逐渐习惯"这条测试本来就会偶发失败"，随后全部测试失去意义。

`MockTransport` 比 `Mock()` 更接近真实：它执行完整的 httpx 请求流程，仅省略最后的网络传输。因此能够验证"超时归一化"这类真实逻辑。

---

## 九、自测清单

- [x] 能说明测试文件为何没有 `__main__`
- [x] 能说出 pytest 的文件名与函数名收集规则
- [x] 能区分 `FAILED` 与 `ERROR`
- [x] 知道退出码 0 与 1 的含义
- [x] 能说明 fixture 是依赖注入，不是 `@BeforeEach`
- [x] 知道 fixture 默认 scope 是 `function`
- [x] 能用 yield fixture 编写 setup 与 teardown
- [x] 知道 `parametrize` 的每个参数组合是独立用例
- [x] 知道 `pytest.raises` 的断言应写在块外
- [x] 能区分 Mock（对象）与 patch（动作）
- [x] 知道 patch 的目标是查找位置
- [x] 知道异步目标必须使用 `AsyncMock`
- [x] 能识别无效测试：改坏被测代码后仍然通过

---

## 十、明日

**Day 5 · mini agent loop**：不使用真实 LLM，用 mock 的 `tool_calls` JSON 编写 50-100 行的 agent 循环。

```text
解析 → 路由 → 执行（并发调用只读工具）→ 回填 → 终止条件
```

> [!note] 前四天在此汇合
> - Day 1 的**状态机**：循环的终止条件即状态流转
> - Day 2 的 **Pydantic → JSON Schema**：`tool_calls` 的解析依赖它
> - Day 3 的 **asyncio**：多个只读工具并发执行
> - Day 4 的 **pytest**：该循环适合以测试驱动的方式实现

> [!tip] 已知的可复用部分
> `tool_calls` 的 JSON 由自己构造，即 Day 4 的 mock 思想；循环的各段可以先写测试再写实现。
>
> 这是阶段 1 的最后一天，也是第一个具备 Agent 形态的程序。

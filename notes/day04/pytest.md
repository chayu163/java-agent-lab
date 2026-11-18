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

> [!abstract] 今日产出
> - `day04/python/01_fixtures_test.py`：fixture 的注入、yield teardown、scope
> - `day04/python/02_parametrize_test.py`：参数化与异常断言
> - `day04/python/03_mock_test.py`：Mock / patch / AsyncMock
> - `day04/python/test_fetch.py`：**主产出**，给 Day 3 的 `05_fetch.py` 写 5 个测试
> - `day04/README.md`：知识树
>
> 验收：`uv run pytest day04 -q` → 34 passed。ruff / format / mypy / 站点构建全绿。

> [!tip] 一句话总结
> 测试不是"验证代码对不对"，而是**把你脑子里那些"应该没问题吧"的假设，变成机器每天替你验证一遍的断言**。

---

## 一、你其实一直在测试，只是测完就扔了

Day 3 写完 `05_fetch.py` 时你做了什么——`print` 一堆结果，跑一遍，眼睛扫一下，觉得对，就往下走。

**那就是测试。** 只是它有三个缺陷：

| 缺陷 | 后果 |
|---|---|
| 只有人能判断对错 | 输出是给人看的，不是给机器判的 |
| 跑完就没了 | 明天改了代码，那段 `print` 不会自动重跑 |
| 只覆盖你想到的那一次输入 | 想不到的场景永远不会被验证 |

写测试 = **把那次临时的 `print` + 你的眼睛，换成一行会永久留在仓库里的 `assert`**。

> [!important] 判断标准：这段代码你会不会改第二次
> 只跑一次的脚本不用写测试。会被人反复改、反复调用的代码，不写测试等于给未来的自己埋债。
> 阶段 5 那个项目要连着改 10 天——不写测试，第五天你就不敢碰第一天的代码。

---

## 二、pytest 的执行模型

### 没有 `main`，因为 pytest 就是入口

Day 1-3 的文件末尾都有 `if __name__ == "__main__"`，Day 4 的测试文件一个都没有。这不是漏了。

```text
Day 1-3 的文件         Day 4 的文件
是「脚本」              是「测试」
自己知道从哪开始跑       不知道，也不该知道
需要 __main__ 块        pytest 来调它
uv run xxx.py           uv run pytest
```

Java 里完全对应：JUnit 测试类里没有 `main`，是 Runner 扫 `@Test` 注解执行的。**pytest 只是把注解换成了命名约定。**

| 扫什么 | 规则 |
|---|---|
| 文件 | `test_*.py` 或 `*_test.py` |
| 函数 | 函数名 `test` 开头 |
| 类 | 类名 `Test` 开头且无 `__init__`（今日未用） |

### 三种状态，含义完全不同

| 状态 | 含义 | 该查什么 |
|---|---|---|
| `PASSED` | 函数跑完，所有 assert 成立 | — |
| `FAILED` | 函数跑了，某条 assert 不成立 | 你的代码或断言 |
| `ERROR` | 函数**根本没跑起来** | fixture、import、语法 |

> [!warning] ERROR 与 FAILED 别混
> `ERROR` 是 setup 阶段就炸了。今天第一次跑时出现 3 个 error，就是因为 `seeded` / `checkout` 里还写着
> `raise NotImplementedError`，pytest 在**建 fixture 时**就挂了，测试函数一行都没执行。
> 看到 ERROR 先看 fixture，别急着怀疑被测代码。

### 怎么知道过没过

三档，从粗到细：

```bash
uv run pytest day04 -q        # 只看汇总：34 passed in 0.42s
uv run pytest day04 -v        # 每个用例一行 PASSED / FAILED
uv run pytest day04 -x        # 第一个失败就停，写完一条立刻验证用这个
```

**真正决定成败的是退出码**：`0` = 全过，`1` = 有失败。CI 就是靠这个数字判断红绿。

---

## 三、fixture：按名字注入，不是自动执行

这是今天最大的认知修正。

### 它做什么

```python
@pytest.fixture
def repo() -> FakeRepo:
    return FakeRepo()

def test_x(repo: FakeRepo):    # 参数名对上，就注入
    ...
```

**要素只有三个：名字、作用域、依赖。** 一个 fixture 可以要另一个 fixture，pytest 会按依赖图拓扑排序地建好。

### 和 `@BeforeEach` 的根本差别

| | JUnit `@BeforeEach` | pytest fixture |
|---|---|---|
| 执行时机 | 类里每个 `@Test` 前**都执行** | **只有点名要它的测试**才执行 |
| 如何获取 | 隐式，写进字段 | 显式，写在参数里 |
| 能否选择 | 不能 | 能 |

实测证据：定义一个会记录调用的 fixture，7 个测试里只有 1 个点名要它 → 它只执行了 1 次。

> [!important] 这是 IoC，不是钩子
> `@pytest.fixture` 的语义是「**注册一个可以按名字要的工厂**」，不是「标记一个钩子函数」。
>
> Spring 类比：它不是 `@BeforeEach`，是 `@Bean` + `@Autowired`。
> **但默认作用域正好相反**——Spring 默认 singleton，pytest 默认每次新建（相当于 prototype）。

### scope 决定它建几次

| scope | 建几次 | 生命周期 | JUnit 近似 |
|---|---|---|---|
| `function`（**默认**） | 每个测试函数 1 次 | 用完就扔 | `@BeforeEach` |
| `class` | 每个测试类 1 次 | 类跑完才扔 | — |
| `module` | 每个文件 1 次 | 文件跑完才扔 | `@BeforeAll` |
| `session` | 整次 pytest 运行 1 次 | 全部跑完才扔 | `@BeforeAll`(static) |

为什么默认是 `function`：**测试之间必须互不污染**。共享实例的话，前一个测试改了什么，后一个测试就从脏状态开始，测试顺序一变结果全变。

什么时候往上提：**只有当"每次重建太慢"且"能保证互不影响"时**（比如起一个 Postgres 要 3 秒）。否则一律 `function`。

### yield fixture：setup 和 teardown 合一个函数

```python
@pytest.fixture
def db():
    conn = connect()
    yield conn          # ← 分界线
    conn.close()        # 测试成功、失败、异常，都执行
```

这背后就是 Day 2 的生成器。用手动驱动验证过：

```python
g = gen()
next(g)          # 执行到 yield，setup 完成
next(g)          # StopIteration，teardown 执行
```

---

## 四、parametrize：一张表跑出 N 条独立用例

```python
@pytest.mark.parametrize(
    ("raw", "expected"),
    [("A1001", "A1001"), ("  A1001  ", "A1001")],
    ids=["plain", "with-spaces"],
)
def test_parse_ok(raw, expected):
    assert parse_order_id(raw) == expected
```

等价于 Java 的 `@ParameterizedTest` + `@CsvSource`。关键特性：**每个参数组合是一条独立用例**，报告里分开显示，一条失败不影响其他条。

`ids=` 控制显示名，失败时一眼能看出是哪组数据。

### 异常断言

```python
with pytest.raises(ValueError):
    parse_order_id("")

with pytest.raises(ValueError, match="不能为空"):   # match 是正则，写片段即可
    parse_order_id("")

with pytest.raises(ValueError) as excinfo:
    parse_order_id("")
assert excinfo.type is ValueError
```

> [!danger] 断言不能写在 `with` 块内部
> ```python
> with pytest.raises(ValueError) as excinfo:
>     parse_order_id(raw)
>     assert excinfo.type is ValueError     # ❌ 永远不执行
> ```
> 一抛异常，控制流立刻跳出 with 块，块内后面的语句全被跳过。**实测验证过**：块内的 append 从未执行。
>
> 需要检查异常内容，一律 `as excinfo` 取出来，**在块外断言**。

---

## 五、Mock 与 patch：名词与动词

混用这两个词是理解困难的主要来源。

| | 是什么 | 词性 |
|---|---|---|
| `Mock()` | 一个**对象**，假替身 | 名词 |
| `patch(...)` | 一个**动作**，临时换掉某个名字 | 动词 |

两者可以完全独立：

```python
# 只有 Mock：造一个假对象，直接用
fake = Mock(); fake.return_value = 9.9
assert fake("A1") == 9.9

# 只有 patch：换成什么都可以，跟 Mock 无关
with patch.object(THIS, "fetch_price", lambda sku: 1.5):
    assert fetch_price("A1") == 1.5
```

> [!note] patch 换的是**名字**，不是函数体
> 试过换成整数 `42`：`fetch_price("A1")` 直接 `TypeError: 'int' object is not callable`。
> 因为这个名字现在指向 `42`，调它就是在调 `42("A1")`。

### 什么时候用哪个

| 场景 | 用什么 | 为什么 |
|---|---|---|
| 函数**有参数**可以传 | 直接传 `Mock()` | 有口子，不需要动刀 |
| 代码里**写死**了某个调用 | `patch()` | 只能从外面换名字 |
| 目标是 `async def` | `AsyncMock()` | Mock 的返回值不是协程 |

**判断顺序：先看有没有口子（参数），有口子就传参；没口子才 patch。**

你 Day 3 的 `fetch_all(transport=...)` 就是"留了口子"的设计——所以测试时传 `MockTransport` 进去，一行 `patch` 都不用写。

### Mock 的三个能力

```python
repo = Mock()                          # 任意属性自动存在
repo.find.return_value = {"id": "A1"}  # 桩：固定返回
repo.find.side_effect = [1.0, 2.0]     # 桩：按序返回 / 抛异常
repo.find.assert_called_once_with("A1")# 间谍：检查调用
```

`Mock()` 的魔法是：访问任何属性，现场造一个子 Mock。`repo.find`、`repo.save`、`repo.随便什么` 都"存在"。Java 的 `mock(Repo.class)` 需要 `.class` 才知道有哪些方法，Python 不需要——这更宽松，也更容易写出假测试。

### patch 的路径陷阱（Python 特有）

> [!danger] 打的是「查找的位置」，不是「定义的位置」
> ```python
> # service.py
> from utils import fetch_price      # ← 被复制进 service 的命名空间
> def total(): return fetch_price()  # ← 用的是 service 命名空间里那一份
> ```
> 必须 `patch("service.fetch_price")`。patch `utils.fetch_price` **无效**——service 早就在自己家里存了一份。
>
> Java 没有这个问题（运行时按类加载，不存在"复制进命名空间"）。这是纯 Python 坑。

---

## 六、今天犯的四个错（最有价值的一节）

这四个错都不是"不会写"，是**知道但没长成肌肉记忆**。记下来。

### 错 1：漏写 `await`，4 处

```python
results = fetch.fetch_all(URLS, timeout=0.1, transport=one_slow)   # ❌
```

`fetch_all` 是 `async def`，不加 `await` 只是造了个协程对象，**函数体一行都没执行**。后面 `len(results)` 直接 `TypeError`，进程退出再补一句 `RuntimeWarning: coroutine 'fetch_all' was never awaited`。

> [!important] 这不是"排期了但没跑"，是根本没进调度
> 补充验证过：`await coro()` **不新建 Task**；`create_task(coro)` 才把新 Task 的 `__step` 放进 ready 队列。
> 漏 `await` 连 Task 都没建，协程对象是死的。详见 Day 3 笔记的「进入就绪队列的是 Task，不是协程」一节。

### 错 2：测试了一个没碰被测代码的 mock

```python
fake = AsyncMock(return_value=5.0)
await fake("A1")
fake.assert_called_once_with("A1")     # ❌ 从头到尾没碰 fetch_async
```

这个测试什么也没验证——**把 `fetch_async` 整个删掉，它照样绿**。它测的是"我刚造的 mock 能不能被调用"，等于自己考自己。

✅ 正确写法必须让被测代码用上它：

```python
with patch.object(THIS, "fetch_async", new=AsyncMock(return_value=5.0)):
    assert await fetch_async("A1") == 5.0
```

> [!tip] 识别假测试的方法
> **把被测代码改坏一行，测试还绿 → 假测试。**
> 这是区分"会写测试"和"会写断言"的唯一标准。

### 错 3：断言写在 `with pytest.raises` 块内部

见第四节。块内语句在异常抛出后全部跳过，永远执行不到。测试仍然绿——因为 `pytest.raises` 本身就是断言——但你以为验证了异常类型，实际什么都没验证。

### 错 4：`assert_called_once_with(...)` 前面加 `assert`

它是**直接抛 `AssertionError`**，不返回布尔值。`assert <它>` 等于 `assert None`，恒失败。

```python
repo.find.assert_called_once_with("A1")    # ✅ 不通过会自己抛
```

---

## 七、测试设计的三个原则

### ① 测行为，不测实现

测「超时返回 `error='timeout'`」，不要测「内部调用了几次 `perf_counter`」。后者一重构就红，但功能没坏。

### ② 一个测试只测一件事

今天 5 个测试对应 5 个行为，不是一个函数 20 条断言。红了以后你立刻知道是哪条。

### ③ 错误路径必须覆盖

| 该测 | 理由 |
|---|---|
| 边界值 | `""`、`0`、空列表——bug 的聚集地 |
| **错误路径** | 超时、500、断连。**最容易写错，因为平时跑不到** |
| 业务规则 | 状态机、格式校验 |
| 修过的 bug | 每个 bug 配一个测试防复发 |

不该测：第三方库的行为、纯 getter、实现细节。

---

## 八、测试替身为什么必须存在

不是洁癖，是两个硬约束：

| | 用真实外部 | 用替身 |
|---|---|---|
| 速度 | 5 个真请求 2 秒，20 个测试 40 秒 | 全部 0.42 秒 |
| 确定性 | 断网/限流/对方挂了 → 测试红 | 只在**你的代码有 bug** 时红 |

第二条更关键：测试如果不能稳定复现，人就会习惯性地说"这个测试本来就偶尔红"，然后**所有测试都失去意义**。

`MockTransport` 比 `Mock()` 更"真"——它走完整的 httpx 请求流程，只是最后一步不发网络。所以能测出"超时归一化"这种真实逻辑。

---

## 九、自测清单（Day 4 验收）

- [x] 能说清测试文件为什么没有 `__main__`
- [x] 能说出 pytest 的文件名 / 函数名收集规则
- [x] 能区分 `FAILED` 和 `ERROR`
- [x] 知道退出码 0 / 1 的含义
- [x] 能说清 fixture 不是 `@BeforeEach`，是依赖注入
- [x] 知道 fixture 默认 scope 是 `function`（不是全局）
- [x] 能用 yield fixture 写 setup + teardown
- [x] 知道 `@pytest.mark.parametrize` 的每条是独立用例
- [x] 知道 `pytest.raises` 的断言要写在块外
- [x] 能说清 Mock 是名词、patch 是动词
- [x] 知道 patch 打的是「查找的位置」
- [x] 知道异步目标要用 `AsyncMock`
- [x] 能识别"假测试"——改坏代码它还绿

---

## 十、明天

**Day 5 · mini agent loop**：不用真 LLM，用 mock 的 `tool_calls` JSON 写 50-100 行的 agent 循环。

```text
解析 → 路由 → 执行（并发的只读工具）→ 回填 → 终止条件
```

> [!note] 前四天在这里合流
> - Day 1 的**状态机**：循环的终止条件就是状态流转
> - Day 2 的 **Pydantic → JSON Schema**：`tool_calls` 的解析靠它
> - Day 3 的 **asyncio**：多个只读工具并发执行
> - Day 4 的 **pytest**：这个循环正好适合用测试驱动写出来

> [!tip] 今天的东西明天立刻用得上
> `mock` 的 `tool_calls` JSON——你自己造数据（Day 4 学的 mock 思想）；
> 循环的每一段——都可以先写测试再写实现（TDD）。
>
> 这是阶段 1 的收官日，也是第一个"像 Agent 的东西"。

---
title: Day 2 · 函数是一等公民
date: 2026-11-14
day: 2
phase: 1
tags:
  - ai-agent-30d
  - python
  - java-migration
status: done
---

# Day 2 · 函数是一等公民

**今天的四个概念是一条线**：Python 把「函数」和「类型」当值来用。Java 的两个前提——方法不是值、类型由编译器强制——在这里全都不成立。

| 产出 | 内容 |
|---|---|
| `decorators.py` | 手写 `@timer`、带参 `@retry` |
| `generators.py` | `iter_chunks`、`take` |
| `context.py` | `Timer`、`Suppress`、`timed` |
| `typing_practice.py` | `Protocol`、`FakeLLMClient`、`Box[T]` |
| `tool_schema.py` | **主产出**：Pydantic → OpenAI tools schema |

> [!example] 两张图
> [装饰器：定义时替换一次，调用时包装每次](assets/decorator-timing.html) · [with 与 @contextmanager](assets/contextmanager-with.html)（本地 HTML，浏览器打开）
>
> 正文里也给了一份 ASCII 版，不打开 HTML 也能读。

---

## 0 · 先破一个错觉

**结论**：看着和 Java 差不多，是因为你只对上了「意图」；坑全在「保证机制」上。

```text
┌─ 真对应 ──────────────── 意图和机制都相同，可以放心迁移 ─┐
│  类 / 继承 / 方法                                       │
│  __eq__ / __hash__  ↔  equals / hashCode                │
│  __repr__           ↔  toString                         │
│  @property          ↔  getter                           │
│  Generic[T]         ↔  Box<T>                           │
└─────────────────────────────────────────────────────────┘
┌─ 假对应 ──────────────── 长得像，机制不同   ★ 最危险 ────┐
│  Protocol   ↔  interface                                │
│  装饰器      ↔  注解 / AOP                               │
│  Pydantic   ↔  Bean Validation                          │
│  dataclass  ↔  record                                   │
│  with       ↔  try-with-resources                       │
│  生成器      ↔  Iterator                                 │
└─────────────────────────────────────────────────────────┘
┌─ 没有对应 ─────────────── 必须新学 ──────────────────────┐
│  GIL · 可变默认参数 · 鸭子类型 · 变量没有类型              │
└─────────────────────────────────────────────────────────┘
```

> [!important] 一句话记住差别
> **Java 是「不合法就编译不过」，Python 是「不合法也能跑，跑到那一步才炸」。**
> 编译器替你守的线，在 Python 里得自己建：注解 + mypy + Pydantic + 测试。

---

## 1 · 装饰器

**结论**：`@deco` 就是 `f = deco(f)`，发生在**定义时**，不是调用时。

### 1.1 两个时刻，别混

| 时刻 | 发生什么 | 次数 |
|---|---|---|
| **导入时** | 创建原函数 A → 调 `timer(A)` → 得到 W → 名字 `slow` 改指向 W | **1 次** |
| **每次调用** | 进入 W → 计时 → 调 A → 返回 | **N 次** |

```text
【导入时】
  def slow(): ...  ──创建──>  A
  @timer           ──调用──>  timer(A)          ← timer 函数体跑 1 次
                                 └──返回──> W（闭包持有 A）
  名字 slow ──改指向──> W                       A 失去名字

【每次 slow()】
  slow() ──实际是──> W() ──计时──> A() ──返回──>
```

> [!danger] 最容易答错的一题
> 调 10 次：**`timer` 跑 1 次，`wrapper` 跑 10 次。**
> `timer` 只参与过「把 A 换成 W」那一次。

### 1.2 带参数的装饰器必然三层

| 层 | 名字 | 吃什么 | 什么时候执行 |
|---|---|---|---|
| 1 | `retry` | 配置 `times` / `delay` | `@retry(3)` 求值时 |
| 2 | `decorator` | 被装饰的函数 `func` | `@` 生效时 |
| 3 | `wrapper` | 调用参数 `*args` | 每次调用 |

**为什么非要第 2 层**：`retry(3)` 执行的那一刻，`flaky` 还没被传进来。所以它必须返回一个“还欠一个函数参数”的东西。

| 写法 | 层数 |
|---|---|
| `@timer` | 2 层 |
| `@retry(3)` | 3 层 |

### 1.3 `functools.wraps` 救什么

它复制 `__name__` / `__doc__` / `__module__` / `__qualname__` / `__annotations__`，并设 `__wrapped__`。

| 不写的后果 | 具体表现 |
|---|---|
| 日志 / 报错 | 所有被装饰函数的 `__name__` 都叫 `"wrapper"` |
| pytest | 报告全是 `wrapper PASSED` |
| FastAPI | 路由名和文档标题全错 |
| 注册表 | 按 `wrapper.__name__` 注册会互相覆盖成一条 |

> [!warning] 注册型装饰器要 `return fn`
> ```python
> def tool(fn):
>     TOOLS[fn.__name__] = fn
>     return fn        # 不包装
> ```
> `return wrapper` 会让同一份逻辑有两个入口：注册表里是裸函数，模块名上是 wrapper。wrapper 里加的校验，从注册表调的路径全绕过。

---

## 2 · 生成器

**结论**：调用返回迭代器，`next()` 才推进；函数体在调用时执行 **0 行**。

### 2.1 六个问题一次答完

| 问题 | 答案 |
|---|---|
| 调用时执行几行 | **0 行** |
| 靠什么推进 | `next()` / `for` / `list()` |
| 走完之后 | 抛 `StopIteration` |
| 能回退吗 | 不能，一次性 |
| `-> Iterator[str]` 指 | **元素的类型**，不是返回值类型 |
| `return x` 会怎样 | 只结束迭代，`x` 进 `StopIteration.value`，消费者拿不到 |

### 2.2 生命周期

```text
调用 iter_chunks("abcdefg", 3)
        │
        ▼
   <generator object>            ← 函数体执行 0 行
        │
    next() ▼
   ┌───────────────────────┐
   │ 执行到 yield "abc"     │──> 返回 "abc"，挂起
   └───────────────────────┘     i 原封不动留在栈帧里
    next() ▼
   ┌───────────────────────┐
   │ 从 yield 下一行继续     │──> 返回 "def"，挂起
   └───────────────────────┘
    next() ▼
   ┌───────────────────────┐
   │ 函数体执行完           │──> StopIteration
   └───────────────────────┘
```

`list()` / `for` / `take()` 都是**消费者**，做的是同一件事：`iter(x)` → 反复 `next()` → 遇 `StopIteration` 停。所以 `list(gen)` 不是“一次执行完”，是 `list()` **逼着它跑完**。

> [!note] Java 对照
> `Iterator<String>` 里，迭代器本身不是 `String`，`next()` 才是。生成器同理。
> 区别在于：Java 的 `Iterator` 状态是你手写的游标；生成器的状态藏在栈帧里，不用你管。

---

## 3 · `with` 与上下文管理器

**结论**：`with` 认的是**协议**（有 `__enter__` 和 `__exit__`），不是类。

### 3.1 三个方法的时机

| 时机 | 调用 | 备注 |
|---|---|---|
| `Foo()` | `__init__` | `with` 不管这个 |
| 进入 | `__enter__` | 返回值绑定给 `as` 后面的名字 |
| 块内 | 业务代码 | |
| 离开 | `__exit__(exc_type, exc, tb)` | 正常结束也调、抛异常也调；返回 `True` 才吞异常 |

### 3.2 语法 vs 库函数

| | `with` | `@contextmanager` |
|---|---|---|
| 是什么 | **语言关键字** | **标准库里的普通函数** |
| 从哪来 | 原生，不用 import | `from contextlib import contextmanager` |
| 接收 | 一个管理器对象 | 一个生成器函数 |
| 返回 | — | **工厂函数**，调用它才得到管理器对象 |

```text
定义时：@contextmanager 作用于 timed → timed 变成工厂函数
调用时：timed("x")      → 管理器对象（有 __enter__ / __exit__）
        __enter__       → next(gen) 推进到 yield
        __exit__        → next(gen) 从 yield 之后继续
```

**`yield` 的位置就是分界线**：之前是 `__enter__` 的范围，之后是 `__exit__` 的范围。

> [!danger] `Suppress` 要用 `issubclass`，不能用 `in`
> `except ValueError:` 是 **issubclass** 语义，能捕获 `UnicodeDecodeError` 这种子类；
> `exc_type in (ValueError,)` 是**相等**语义，子类会漏掉。
>
> ```python
> if exc_type is None:
>     return False
> return issubclass(exc_type, self.exc_types)
> ```

---

## 4 · typing

**结论**：注解在运行时**完全不生效**，只有默认值是真的。

### 4.1 生效范围

| 写法 | mypy | 运行时 |
|---|---|---|
| `a: int` | 要求 int | **不生效**，传 `"abc"` 照样跑 |
| `b: list[str] \| None = None` | 类型 + 可空 | **只有 `= None` 生效** |
| `-> dict[str, Any]` | 返回类型 | **不生效** |

> [!note] `| None` 表达「可空」，不表达「有默认值」
> 让它可选的是默认值。`x: int | None` 没默认值时仍然必填，只是允许显式传 `None`。

### 4.2 三个容易混的对照

| 概念 | Java | Python | 差别 |
|---|---|---|---|
| 任意类型 | `Object` | `Any` | `Object` 是所有类的父类；`Any` 是**关闭检查**，什么都能调，运行时才炸 |
| 接口 | `interface` | `Protocol` | 名义 vs **结构化**：有方法就算实现，不用 `implements` |
| 泛型 | `Box<T>` | `Box[T]` | 都是**擦除**的，运行时拿不到 `T` |

验证 `Protocol` 是结构化检查：把实现类的 `complete` 改个名，mypy 立刻报错——它看的是**形状**。

> [!tip] 为什么 `FakeLLMClient` 重要
> Day 4 写测试不能真调 LLM，今天这个假实现到时候直接复用。

---

## 5 · Pydantic → JSON Schema

**结论**：出现「有名字的类型」就进 `$defs` 留 `$ref`；模型 API 不认 `$ref`，必须递归内联。

### 5.1 什么时候产生 `$ref`

| 字段写法 | 结果 |
|---|---|
| `x: str` | 内联 |
| `y: Literal["a", "b"]` | 内联 |
| `z: list[int]` | 内联 |
| `a: A`（嵌套 `BaseModel`） | **`$ref`** |
| `p: TicketPriority`（`Enum`） | **`$ref`** |

判断标准只有一条：**这个名字是不是你自己 `class` 出来的。**

### 5.2 内联前后

```text
model_json_schema()：
{
  "$defs": { "A": {...}, "TicketPriority": {...} },   ← 有名字的收在这里
  "properties": {
    "a": {"$ref": "#/$defs/A"},                        ← 原地留指针
    "p": {"$ref": "#/$defs/TicketPriority"}
  }
}

内联后：
{
  "properties": {
    "a": {...A 的实际内容...},                          ← 指针被替换
    "p": {...枚举的实际内容...}
  }
}
```

指针语法 `#/$defs/A` 是 JSON Pointer：`#` = 文档根，`/` 逐层下钻。等于「从根出发，进 `$defs`，取 `A`」。

### 5.3 三个细节

| 点 | 说明 |
|---|---|
| 为什么内联 | `$ref` 是 JSON Schema 2020-12 特性，各家模型服务支持不一，摊平最保险 |
| 为什么删 `title` | Pydantic 自动加的字段标题，OpenAI 不认，属于噪音 |
| 为什么递归 | 展开出来的定义自身可能还带 `$ref`（A 引用 C） |

> [!note] 递归路径为什么用 tuple
> `(*stack, name)` 每次生成**新元组**，上一层原封不动，每个递归帧看到的是自己这条路径的历史。
> 换成 list 的 `stack.append(name)`，所有帧共享同一个 list，回溯时分不清路径，会误报循环引用——这是 Day 1「可变默认参数」那个坑的变种。

---

## 6 · 一页速查

| 概念 | 一句话 | 陷阱 |
|---|---|---|
| 装饰器 | `f = deco(f)`，定义时执行 | 以为 `deco` 每次调用都跑 |
| 带参装饰器 | 3 层：配置 → 函数 → 调用 | 少写一层括号 |
| `wraps` | 复制元信息到 wrapper | 不写则 `__name__` 全叫 wrapper |
| 生成器 | 调用 0 行，`next` 推进 | 以为调用就执行 |
| `return` in 生成器 | 只结束迭代，不产出值 | 当成“返回最后一块” |
| `Iterator[str]` | 元素的类型 | 当成返回值类型 |
| `with` | 认 `__enter__` / `__exit__` | 以为必须传类实例 |
| `@contextmanager` | 标准库函数，非语法 | 以为它是语言内建 |
| `__exit__` 返回 True | 吞掉异常 | 返回 `in` 判断，漏掉子类 |
| 注解 | 运行时无效 | 以为 Python 会检查类型 |
| `Any` | 关闭类型检查 | 当成 `Object` |
| `Protocol` | 结构化匹配 | 去找 `implements` |
| `$defs` / `$ref` | 有名字的自定义类型 | 以为基础类型也会产生 |
| 内联 | 递归替换 + 删 `$defs`/`title` | 只替换一层，忘展开嵌套 |
| 递归路径 | 用不可变 tuple 传 | 用 list 共享，误报循环 |

---

## 7 · 自测（合上笔记再答）

- [ ] 被 `@timer` 装饰的函数调 10 次，`timer` 和 `wrapper` 各执行几次？
- [ ] 为什么 `@retry(3)` 必须三层，`@timer` 两层就够？
- [ ] 不写 `functools.wraps` 会让 pytest 报告坏成什么样？
- [ ] 生成器被调用时执行几行？靠什么推进？走完再 `next()` 会怎样？
- [ ] `Iterator[str]` 里的 `str` 描述什么？
- [ ] 生成器里的 `return value` 去哪了？
- [ ] `with` 判断一个对象能不能用，依据是什么？
- [ ] `@contextmanager` 是语法还是标准库函数？它返回什么？
- [ ] `__exit__` 返回 `True` 意味着什么？
- [ ] 注解运行时生效吗？什么情况例外？
- [ ] `Any` 和 `Object` 的区别？
- [ ] `Protocol` 为什么不需要继承？
- [ ] 什么时候生成 `$defs`？举一个不会生成的反例。
- [ ] 内联 `$ref` 时为什么要递归？
- [ ] 装饰器和 Java 注解的机制差别，一句话说清。

---

## 8 · 明天

**Day 3 · asyncio**：event loop、coroutine、Task、gather、Semaphore、timeout、async with
产出：asyncio + httpx 并发调 5 个公共 API（带超时与并发上限）

> [!danger] 这里最先翻车
> 带着「asyncio ≈ 线程池」的模型去写，会踩三件事：
>
> 1. `time.sleep()` 在协程里**卡死整个事件循环**，必须用 `asyncio.sleep()`
> 2. 协程不并行，是**交替**执行；任何时刻只有一个在跑
> 3. 漏写 `await` 不报错，你只是拿到一个没人驱动的 coroutine 对象
>
> 这和今天「生成器不自己跑」是同一个机制的两个面。

> [!note] 前向链接
> - 三层装饰器在 Day 6 的工具注册里会再出现
> - `Protocol` 是 Day 4 写测试的接口约定
> - `$ref` 内联是 Day 6 function calling 的直接前置

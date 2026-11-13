---
title: Day 1 · Java→Python 定向迁跃
date: 2026-11-13
day: 1
phase: 1
tags:
  - ai-agent-30d
  - python
  - java-migration
status: done
---

# Day 1 · Java→Python 定向迁跃

> [!abstract] 今日产出
> - `day01/python/order.py`：批注版（❌ 原写法 + ✅ 改法）
> - `day01/python/order_bean.py`：无批注的 Java bean 风格标准版
> - `day01/java/Order.java`：对照用的 Java 原版
> - 本篇笔记

> [!tip] 一句话总结
> Python 和 Java 的差异不在语法，在**约束由谁来保证**：Java 靠编译器和访问修饰符，Python 靠约定、运行时机制和类型检查器。

---

## 一、Java bean ↔ Python 映射表

| Java bean | Python | 说明 |
|---|---|---|
| `private String id;` | `self._id` | 下划线是**约定**，不是语法，外部照样能访问 |
| `public String getId()` | `@property def id` | 属性访问语法，实际调用函数 |
| `public void setState(...)` | `@state.setter` | 没有 setter 时赋值抛 `AttributeError` |
| `public Order(String id)` | `def __init__(self, id)` | |
| `public String toString()` | `__repr__` | |
| `equals` / `hashCode` | `__eq__` / `__hash__` | 必须成对，否则对象不可哈希 |
| `@Override` | `@decorator` | 机制完全不同，见 [[#四、装饰器不是注解]] |

---

## 二、十个必踩的坑

### 坑 1：可变默认参数只求值一次

```python
def add(item, bucket=[]):  # ❌ bucket 这个 list 在 def 执行时创建，被函数对象永久持有
    bucket.append(item)
    return bucket


add("a")  # ['a']
add("b")  # ['a', 'b']  ← 不是 ['b']
```

`def` 语句执行时默认值就求值了，之后每次调用复用同一个对象。Java 没有这个问题，因为 Java 不给方法参数默认值（只能重载）。

✅ 用 `None` 哨兵：

```python
def add(item, bucket: list[str] | None = None) -> list[str]:
    if bucket is None:
        bucket = []
    bucket.append(item)
    return bucket
```

dataclass 里对应的是 `field(default_factory=list)`。

### 坑 2：`is` vs `==`（和 Java 正好反过来）

| Python | Java | 比较什么 |
|---|---|---|
| `==` | `equals()` | 值 / 内容 |
| `is` | `==` | 对象身份（`id()`） |

```python
a = [1, 2]
b = [1, 2]
a == b  # True  → 调用 list.__eq__，逐元素比
a is b  # False → 两个不同的 list 对象
```

> [!warning] 唯一该用 `is` 的场景
> 和 `None`、`True`、`False` 比较：`if x is None:`。别用 `if x == None`。

> [!note] Python 没有常量池
> 有 **小整数缓存**（-5~256）和 **字符串驻留**，那是 CPython 实现细节，跟 Java 的字符串常量池不是一回事，不要拿来类比。

### 坑 3：真值判断

为 `False` 的：`None`、`False`、`0`、`0.0`、`""`、`[]`、`{}`、`()`、`set()`。

```python
bool("0")  # True  ← 非空字符串
bool([0])  # True  ← 非空容器，不看里面装什么
bool(" ")  # True  ← 空格也是非空
```

**只看容器空不空，不看内容真不真。** Java 里 `if (list)` 直接编译不过，所以这个坑 Java 程序员必踩。

### 坑 4：类属性 vs 实例属性

```python
class Bad:
    tags = []  # ❌ 类属性，所有实例共享


class Good:
    def __init__(self) -> None:
        self.tags = []  # ✅ 实例属性
```

> [!danger] 关键判断标准
> **看有没有 `self.xxx = ...`。** 有 `self.` 才是实例属性。
> 只写类型注解 `tags: list[str]` **没用**——注解在运行时什么都不做，`tags` 还是类属性，还是共享。

### 坑 5：GIL —— 它是障碍，不是优化

同一时刻只允许一个线程执行 Python 字节码。**不是** "GIL 实现了 IO 并行"，恰恰相反，asyncio 能跑起来是因为它**根本不用多线程**。

```text
你的 Python ──HTTP──> 远端 GPU 推理 ──返回──> 你的 Python
     ↑                                          ↓
     └──────── 全程只在等 socket，CPU 空转 ──────┘
```

| 场景 | 特征 | Python 手段 | GIL 影响 |
|---|---|---|---|
| CPU 密集 | 算矩阵、压缩、图像 | 多进程 | **有影响**，必须绕 |
| IO 密集 | 等网络 / DB / 磁盘 | asyncio / 线程 | **无影响**，等待时释放 |

> [!important] Agent 服务是 IO 密集型的
> 模型跑在远端机房，不在你的进程里。你的代码 99% 时间在 `await` 等回包。
> `await` 时协程主动挂起、事件循环切到别的协程——**单线程内完成，从不需要同时跑字节码**，所以 GIL 构不成限制。

### 坑 6：装饰器不是注解

Java 注解是给编译器 / 框架读的**元数据**，运行时靠反射，不改方法行为。Python 装饰器是**运行时的函数替换**：

```python
@deco
def f(): ...


# 完全等价于
def f(): ...


f = deco(f)
```

`deco(f)` 返回什么，`f` 就变成什么。能包装、能改签名、能整个替换。

> [!tip] 应用
> `@app.get("/")`、`@retry`、`@tool`、`@pytest.fixture` 全建立在这个机制上。阶段 2 的 function calling 工具注册会用大量装饰器。

### 坑 7：模块导入基于 `sys.path`

Python 没有 classpath。`import x` 按 `sys.path` 列表顺序查找。项目里靠 **venv + `uv run`** 保证 `sys.path` 正确，不需要 `-cp` 参数。

### 坑 8：依赖管理

`pyproject.toml` 一个文件声明依赖 + 工具配置（对应 `pom.xml` / `build.gradle`），`uv.lock` 锁版本（对应 `pom.xml` 的 resolved 依赖）。`uv add` / `uv sync` / `uv run` 三件套。

### 坑 9：除法

```python
7 / 2  # 3.5   永远浮点
7 // 2  # 3     整除，向下取整
-7 // 2  # -4    ← Java 是 -3（截断）
-7 % 3  # 2     ← Java 是 -1（截断余数）
```

> [!note] 恒等式
> `a == (a // b) * b + (a % b)` 在 Python 里永远成立。
> Python 的 `%` 结果**与除数同号**，Java 的与**被除数**同号。

### 坑 10：缩进即语法

缩进是语法结构的一部分，不只是排版。同一文件里 tab / 空格混用会直接 `TabError`。

本仓库统一 **4 空格**，由 `pyproject.toml` 的 `[tool.ruff.format] indent-style = "space"` 锁定，`ruff format` 负责执行。

---

## 三、类型注解

> [!warning] 注解默认不可空
> `state: OrderState = None` 是错的——Python 注解默认"永远不是 None"（PEP 484 `no_implicit_optional`）。
> 相当于 Java 里标了 `@NonNull` 却赋 `null`。

```python
state: OrderState | None = None  # Python 3.10+
history: list[OrderState] | None = None
# 等价于 typing.Optional[OrderState]，对应 Java 的 @Nullable
```

`None` 不是"假值"，是 Python 唯一的空值，对应 Java 的 `null`。别因为"枚举不是布尔类型"就觉得不能给 None——**可空性和类型无关**。

---

## 四、`@property` 与状态机

```python
class Order:
    @property
    def state(self) -> OrderState:
        return self._state
```

- `@property` 让 `state` 变成**数据描述符**，`order.state` 是读，走 `__get__`。
- `order.state = x` 是写，走 `__set__`——没定义 setter 就抛 `AttributeError: property 'state' has no setter`。
- **类内部也要写 `self._state = x`**，不能写 `self.state = x`。

> [!important] 这是设计决策，不是风格问题
> 标准 Java bean（DTO）通常全套 getter/setter。但 `Order` 是**状态机**，给它开 setter 会让外部绕过校验：
> - 枚举能挡住非法值（`DISCARD`），**挡不住非法转换**
> - `order.set_state(SHIPPED)` → 合法值 + 非法转换 → "没付款就发货"
>
> 判断标准：**这个对象有没有不变量要守**。有 → 只读属性 + 业务方法写入口。

---

## 五、`__eq__` / `__hash__`

```python
def __eq__(self, other: object) -> bool:
    if not isinstance(other, Order):
        return NotImplemented  # 注意是 NotImplemented，不是 False
    return self._id == other._id  # 实体语义：同 id 即同一实体


def __hash__(self) -> int:
    return hash(self._id)
```

> [!danger] 定义了 `__eq__` 不定义 `__hash__` 的后果
> Python **自动把 `__hash__` 置为 `None`**，对象变得不可哈希，放进 `set` / 当 `dict` 的 key 直接报
> `TypeError: unhashable type`。比 Java 狠——Java 给你个不匹配的默认 `hashCode` 让你慢慢踩坑。

**hash 契约**：`a == b` 为 True ⇒ `hash(a) == hash(b)`。反过来不成立（哈希碰撞）。
`dict` / `set` 先用 hash 定位桶、再用 `__eq__` 确认。哈希不匹配 → 相等对象落到不同桶 → 去重失效。

判断用实体语义还是全字段语义：实体（有 id 的）按 id；值对象（金额、坐标）按全字段。

---

## 六、`@dataclass` 只用了半截的坑

```python
@dataclass
class A:
    x: int

    def __init__(self, x: int) -> None:  # 手写了 init
        self.x = x
```

实测结果（本机验证）：

```text
hash: None          ← __hash__ 被禁用
eq:   True          ← __eq__ 照样生成
repr: A(x=1)        ← __repr__ 照样生成
set error: unhashable type: 'A'
```

| 成员 | 是否生成 |
|---|---|
| `__init__` | ❌ 已手写则不生成 |
| `__repr__` | ✅ 照常生成 |
| `__eq__` | ✅ 照常生成 |
| `__hash__` | ❌ 被置为 `None` |

**要么全用 dataclass（初始化逻辑放 `__post_init__`），要么不用。** 混用会产生意想不到的 `__eq__` 和不可哈希。

dataclass 正确姿势：

```python
@dataclass
class Order:
    id: str
    _state: OrderState = field(init=False, default=OrderState.CREATED)
    _history: list[OrderState] = field(init=False, default_factory=list)

    def __post_init__(self) -> None:
        self._history.append(self._state)
```

---

## 七、自测清单（Day 1 验收）

- [x] 能说出可变默认参数的机制和修法
- [x] 能说清 `is` / `==` 和 Java 的反向映射
- [x] 知道非空容器即为 True，不看内容
- [x] 知道 `self.tags = []` 才是实例属性，注解不算
- [x] 能用自己的话讲清 Agent 服务为什么 IO 密集、GIL 为什么不挡 asyncio
- [x] 能说清装饰器是函数替换、不是注解
- [x] 知道 `_` 前缀不拦截，`private` 拦截
- [x] 知道 `@property` 无 setter 时赋值报 `AttributeError`
- [x] 知道注解默认不可空、要写 `| None`
- [x] 能举出"合法值 + 非法转换"绕过状态机的例子
- [x] 知道 `__eq__` / `__hash__` 必须成对
- [x] 知道 dataclass 混用手写 `__init__` 的后果

---

## 八、明天要看

- [[Day 2 函数是一等公民]]：装饰器手写 `@retry` / `@timer`、生成器 `yield`、`with` 上下文管理器、typing（Protocol / Generic / dataclass / Pydantic v2）
- 产出：用 Pydantic 定义一套 Tool schema —— 这是阶段 2 function calling 的直接前置

> [!note] 关联
> - [[坑 6 装饰器不是注解]] 是 Day 2 的主线
> - [[坑 1 可变默认参数]] 在 Pydantic 和 dataclass 里会以 `default_factory` 的形式再出现
> - [[坑 5 GIL 与 asyncio]] 在 Day 3 会变成一整天的动手内容

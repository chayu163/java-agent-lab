# Day 3 · asyncio 知识树

六个名词不是并列的六件事，是一条**从问题到工具**的链。按这棵树的顺序读，每一层都在回答上一层留下的问题。

```text
asyncio
│
├─ ① 前提层：为什么要有它
│   └─ 一个请求 99% 时间在等 IO；线程太贵；CPU 密集不该用它
│
├─ ② 概念层：三个名词
│   ├─ coroutine   async def 定义的可暂停函数，调用返回对象，一行不跑
│   ├─ event loop  唯一的驱动者，维护就绪队列
│   └─ await        把控制权交回循环的语法标记
│
├─ ③ 调度层：怎么让它们一起跑
│   ├─ Task         coroutine 的驱动壳，create_task 立刻排期
│   ├─ gather       批量排期 + 按参数顺序收结果
│   ├─ TaskGroup    结构化并发，一个失败全体取消（3.11+）
│   └─ as_completed 谁先完成谁先交
│
├─ ④ 控制层：怎么收住
│   ├─ Semaphore    并发上限
│   ├─ Lock/Event   互斥与信号
│   ├─ timeout      总时限，超时抛 TimeoutError 并取消
│   └─ cancel       协作式取消，CancelledError 必须重新抛
│
├─ ⑤ 资源层：怎么管生命期与流
│   ├─ async with   __aenter__ / __aexit__，对应同步的 enter/exit
│   ├─ async for    __aiter__ / __anext__，异步生成器最常用
│   └─ Queue        生产者-消费者，天然背压
│
└─ ⑥ 生态层：接真实东西
    ├─ httpx.AsyncClient  连接池 + 每阶段超时
    └─ asyncio.to_thread  同步库的逃生口
```

---

## 一、前提层：为什么会有 asyncio

一次 LLM 调用，你的进程在做什么？

```text
发起 socket 写入  ▏1ms  CPU
等待远端推理      ▏3000ms  纯等待，CPU 空转
读取响应          ▏1ms  CPU
```

**99.9% 的时间 CPU 什么也没干。** 问题不是"算得慢"，是"等得久"。

两条解法：

| 方案 | 代价 | 适合 |
|---|---|---|
| 多线程 | 每线程 1-8MB 栈；切换要进内核；GIL 限制字节码并发 | 已有同步库、连接数 ≤ 几百 |
| 事件循环 | 单线程，协程栈只有几 KB；切换是纯用户态函数返回 | 高并发 IO、连接数上千 |

事件循环的核心思想：**把"等待"从线程里拿出来，变成一张登记表**。谁在等，就登记"等什么、好了叫我"；好了再排进就绪队列。等待期间不占线程。

> [!warning] 什么时候别用
> CPU 密集（矩阵运算、压缩、图像处理）用 asyncio 是纯自残——没有"等待"可以交出去，单线程就是单线程。
> 那时候要的是 **多进程**（`multiprocessing` / `ProcessPoolExecutor`），因为多进程各自有解释器，绕开 GIL。

---

## 二、概念层：三个名词

### coroutine

```python
async def f():
    print("hello")


coro = f()  # 只创建对象，一行都不执行
print(coro)  # <coroutine object f at 0x...>
```

`async def` 定义的是一个**可暂停的函数**。底层机制和 Day 2 的生成器是同一套：coroutine 就是一个实现了 `__await__` 协议的生成器。区别只在协议——生成器用 `send()` 推进，coroutine 用 `await` 驱动。

> [!important] 和生成器的这一层关系
> 你已经知道"生成器调用后执行 0 行，`next()` 才推进"。coroutine 完全一样：`await` 是那个 `next()`。
> 所以"协程不自己跑"不是 asyncio 的特殊规定，是**同一个机制**的必然结果。

### event loop

循环本体只有一件事：

```text
while True:
    取出就绪队列里的下一个回调，执行它
    执行到 await -> 该协程登记"我等什么"，把控制权交回来
    检查有没有等待条件已满足的 -> 满足就重新塞回就绪队列
```

`asyncio.run(coro)` 就是"建一个循环、把 coro 塞进去、跑到空为止、关掉循环"。

### await

`await x` 的准确含义：**把 x 跑到底**。

x 内部每遇到一个真正需要等的挂起点（`asyncio.sleep`、网络读、`Queue.get`），它才把控制权交回循环。循环趁这个空档去跑别的 Task，等 x 的条件满足再回来接着跑。

> [!important] `await` 是**可能**挂起，不是**一定**挂起
> 如果被 await 的对象当场就能给出结果（比如一个没写 `await` 的子协程、一个已完成的 Future），
> 整个 `await` 会在**同一次 `send()` 里**跑完，控制权根本不会回到循环。
> 只有"条件未就绪"时才有让出。这一点决定了你以为的并发有时候并不存在——见 `00_trace.py` 第 6 段。

用词上要分清两件事，混了会判断错：

| | 阻塞（Java 线程） | 挂起（Python 协程） |
|---|---|---|
| 栈 | 保留在线程上，占内存 | **冻结在堆上**，线程栈清空 |
| 谁在等 | 内核把它移出 CPU，进等待队列 | 协程自己返回，循环照常转 |
| 别的活能不能跑 | 要另一个线程才行 | **同一个线程**立刻能跑别的协程 |
| 恢复 | 内核调度器决定 | 条件满足后，回调把它重新塞进就绪队列 |

---

## 二·五、和 Java 线程模型对照

Java 的状态是**内核对象**，有枚举、有 API；Python 的状态藏在 coroutine 的帧里，同一个 `SUSPENDED` 覆盖了 Java 的三个等待态。

| Java `Thread.State` | Python `inspect.getcoroutinestate()` |
|---|---|
| `NEW` | `CORO_CREATED`（调用 `async def` 后，一行没跑） |
| `RUNNABLE` | `CORO_RUNNING`（`Task.__step` 正在推它） |
| `WAITING` / `TIMED_WAITING` / `BLOCKED` | `CORO_SUSPENDED`（卡在某个 `await` 上，不区分等多久） |
| `TERMINATED` | `CORO_CLOSED`（耗尽 / 异常 / 被取消） |

方法对应：

| Java | Python | 差异 |
|---|---|---|
| `new Thread(r)` | `asyncio.create_task(coro)` | 两者都**只是排期**，还没跑 |
| `t.start()` | **没有对应物** | Python 的"启动"就是下一次循环迭代，不可显式触发 |
| `t.join()` | `await task` | 一样阻塞调用方，但 Python 是让出而非阻塞线程 |
| `t.isAlive()` | `not task.done()` | 一致 |
| `t.getState()` | `inspect.getcoroutinestate(...)` | 粒度更粗，不区分等什么 |
| `Thread.sleep(ms)` | `await asyncio.sleep(s)` | 必须 `await`，否则整个循环卡死 |
| `t.interrupt()` | `task.cancel()` | 都只是**发请求**，不是立刻终止 |
| `ExecutorService.submit()` | `create_task` | 一致 |
| `invokeAll()` | `asyncio.gather` / `TaskGroup` | TaskGroup 才有"一败俱败" |
| `Semaphore` | `asyncio.Semaphore` | 几乎完全一致 |
| `CountDownLatch(1)` | `asyncio.Event` | `wait()` / `set()` |
| `ThreadLocal` | `contextvars.ContextVar` | Agent 里存 trace_id 用它 |

**唯一真正缺的是 `t.start()`。** Java 里创建和启动是两步，你可以先 `new` 再决定何时 `start`；Python 的 `create_task` 一次做完，但**必须让出控制权**它才真的开始跑——所以 `create_task` 返回时状态仍是 `CORO_CREATED`。这是最容易判断错的一处。

`await` 在实现上是 `yield from x.__await__()`，事件循环干的事就是反复 `coro.send(None)`。想亲手验证，跑 `python/00_trace.py`。

---

## 三、调度层：怎么让它们一起跑

| 写法 | 含义 | 结果顺序 | 一个失败 |
|---|---|---|---|
| `await f()` | 跑到底，不建 Task | — | 直接抛 |
| `create_task(f())` | 立刻排期，**不等** | 无返回值，要自己 await Task | 挂在 Task 上，不主动抛 |
| `gather(*coros)` | 全部排期，一起等 | **按参数顺序** | 立刻抛（除非 `return_exceptions=True`） |
| `TaskGroup()` | 结构化并发块 | 自己管理 | 全体取消，抛 `ExceptionGroup` |
| `as_completed(tasks)` | 迭代，谁先完谁先出 | **按完成顺序** | 抛在迭代里 |

### 两个顺序，两个来源

"结果顺序由谁决定"这个问题问得太粗，会得到自相矛盾的答案。拆成两个：

| 顺序 | 谁产生 | 证据 |
|---|---|---|
| **完成顺序** | 事件循环调度（定时器堆 + 就绪队列） | `fast→mid→slow`，由各自的 delay 决定 |
| **交付顺序** | 组合器**是否重排** | 见下表 |

同一批任务跑三种收集方式，实测：

```text
gather        交付=['slow','fast','mid']   真实完成=['fast','mid','slow']
as_completed  交付=['fast','mid','slow']   真实完成=['fast','mid','slow']
[await t ...] 交付=['slow','fast','mid']   真实完成=['fast','mid','slow']
```

- **`gather` 在重排**：它把调度产出的完成顺序整个丢掉，按**参数下标**把结果摆回去。这是真正的编排——它违背了调度。
- **`as_completed` 不编排**：它按谁先完成就交谁，原样透传调度结果。说它"编排顺序"是本末倒置。
- **`TaskGroup` 不交结果**：它只管取消语义，结果要自己往外部容器里塞。

所以准确的因果是：

```text
create_task    → 任务进入就绪队列（提交）
事件循环       → 决定每个任务何时完成（调度，产出完成顺序）
组合器         → 决定交付顺序：重排（gather）/ 透传（as_completed）/ 不给（TaskGroup）
```

> [!warning] Python 没有"协程池"
> 这是 Java `ExecutorService` 带来的错误联想。asyncio 里没有 worker 线程、没有任务排队等空闲 worker。
> `create_task` 之后所有任务同时"在飞"，各自停在 `await` 上；Task 是"协程 + 一个驱动壳"，用完即弃。
> `as_completed` 内部有个 `asyncio.Queue`，那是**完成事件的信箱**，不是任务池。

### 为什么 `for ... await` 不是串行

这是最反直觉的一处。看这段代码：

```python
for x in asyncio.as_completed(ts):
    result = await x
```

字面上像"一个一个等",但三个任务确实是并发的。原因是**被挂起的是 `main` 这一个协程,不是事件循环**：

```text
t=0.002  main  create_task x3  → 三个任务已排期，但都没开始
t=0.002  main  进入 for，await 一个空队列  → main 挂起，控制权交回 loop
t=0.002  loop  终于有活干了：依次启动 slow / mid / fast，三个都卡在 sleep
t=0.057  fast  睡醒 → 完成回调把 fast 塞进队列 → 唤醒 main
t=0.057  main  拿到 'fast'，append → 下一轮 await，队列空 → 再次挂起
t=0.148  mid   睡醒 → 同上
t=0.303  slow  睡醒 → 同上，循环结束
```

关键在于把时间轴拆成两列看：

| 时刻 | `main` 在干什么 | 那三个任务在干什么 |
|---|---|---|
| 0.002 | 挂起，等队列 | 刚被启动，各自 sleep |
| 0.057 | 醒来，处理 fast，又挂起 | fast 完成；mid / slow 还在睡 |
| 0.148 | 醒来，处理 mid，又挂起 | mid 完成；slow 还在睡 |
| 0.303 | 醒来，处理 slow，结束 | slow 完成 |

**`main` 确实是串行的——它一次只处理一个结果。但任务不是它驱动的。** 任务在 `main` 挂起的每个空档里自己往前跑，这才是并发。

对照 Java 就清楚了：`as_completed` ≈ `ExecutorCompletionService`。

```java
ExecutorCompletionService<String> cs = new ExecutorCompletionService<>(pool);
for (int i = 0; i < 3; i++) cs.submit(task);
for (int i = 0; i < 3; i++) {
    String r = cs.take().get();   // ← 也是"一个一个拿"，但任务早就在线程池里跑
}
```

`cs.take()` 串行，三个任务并行。Python 这行代码是同一个形状，只是"线程池"换成了"事件循环"。

> [!warning] 但有一个前提
> 任务内部**必须有真正的挂起点**（`await asyncio.sleep` / 网络 IO / `Queue.get`）。
> 如果三个任务是纯 CPU 计算、从不 `await`，那第一个会把循环占满，
> 后面两个根本没机会启动，`as_completed` 也就退化成了串行。
> 并发是**挂起点**给的，不是 `as_completed` 给的。

三个必须分清的点：

1. **`gather` 的结果顺序 ≠ 完成顺序。** `gather(slow, fast)` 返回 `[slow 的结果, fast 的结果]`，即使 fast 先完成。这是最常见的误读。
2. **`[await f(x) for x in xs]` 是串行。** 列表推导不会帮你并发，每个 `await` 都在原地等完。
3. **`create_task` 之后一定要有人 await 它。** 否则任务还在跑，异常没人收，程序退出时被静默丢弃（"Task was destroyed but it is pending"）。

> [!tip] 为什么 TaskGroup 是更安全的默认
> `gather` 里有一个失败，其他的 Task **继续跑**——你拿到了异常，但另外几个还在后台烧钱。
> `TaskGroup` 是结构化并发：块里任何一个失败，兄弟立刻被取消，块统一抛 `ExceptionGroup`。对 Agent 服务（一个工具挂了没必要等其余五个）这是对的行为。

---

## 四、控制层：怎么收住

并发一旦有了，就必须能限制、能中断。

### Semaphore

一个带计数的闸门。`async with sem` 拿名额，离开自动还。

```python
sem = asyncio.Semaphore(3)  # 最多 3 个同时进门


async def one(u):
    async with sem:  # 名额满了就在这里排队
        return await client.get(u)
```

> [!danger] 名额泄漏
> 不用 `async with` 而手写 `acquire()` / `release()`，一旦中间抛异常或任务被取消，`release()` 没执行，名额永久少一个，闸门越开越小直到卡死。
> **永远用 `async with sem`**，它保证 `finally` 语义。

### timeout

```python
async with asyncio.timeout(2.0):  # 3.11+
    resp = await client.get(url)
```

超时抛 `TimeoutError`，并且**会取消**里面正在跑的东西——不是扔下不管。

老写法 `await asyncio.wait_for(coro, 2.0)` 等价，但 `asyncio.timeout` 能包住一段多步逻辑（比如"三次请求 + 两次重试"整体 2 秒），`wait_for` 只能包一个协程。

### cancel

```python
task = asyncio.create_task(f())
task.cancel()  # 不是立刻杀，是"下次到这个 await 点时抛 CancelledError"
```

协作式取消：被取消的协程在 `await` 点收到 `asyncio.CancelledError`，它可以做清理，但**必须重新抛出**。

> [!danger] 这里是最难查的 bug 源
> `CancelledError` 在 3.8+ 继承自 `BaseException`，不是 `Exception`。原因就是防止 `except Exception` 顺手把它吞掉。
> 但如果你写 `except BaseException:` 然后不重抛，任务就"正常结束"了——调用方以为取消了，其实它还在跑。

---

## 五、资源层：生命期与流

### async with

和同步 `with` 一一对应：

| 同步 | 异步 |
|---|---|
| `__enter__` | `__aenter__` |
| `__exit__` | `__aexit__` |
| `with x:` | `async with x:` |
| `@contextmanager` | `@asynccontextmanager` |

`__aexit__` 返回 `True` 同样是吞异常。`@asynccontextmanager` 同样是"写在 `contextlib` 里的标准库函数，不是语言语法"——Day 2 的结论原样搬过来。

### async for

`async for` 认 `__aiter__` / `__anext__`，最常用的是**异步生成器**：

```python
async def paginate(url):
    while url:
        resp = await client.get(url)
        yield resp.json()
        url = resp.json().get("next")
```

`async for page in paginate(...)` 一边等一边吃，不用把所有页先攒进内存。流式输出（LLM 的 token 流）就是这个形状。

### Queue

`asyncio.Queue` 是线程安全队列的协程版，天然带背压：`put` 在队满时挂起，`get` 在队空时挂起。生产者-消费者用它解耦。

---

## 六、生态层：接真实东西

- **`httpx.AsyncClient`**：连接池是它最大的价值。一次 `async with` 建一个 client，所有请求复用 TCP 连接，比每个请求新建连接快一个数量级。它的 `timeout` 管**单个阶段**（连接 / 读），`asyncio.timeout` 管**整个协程**——两个都要。
- **`asyncio.to_thread(fn, *args)`**：把同步阻塞函数扔到线程池跑。这是接老库（`requests`、`psycopg2` 同步版、本地文件 IO）的逃生口。它不违反 GIL 的故事——线程里跑的是等待，不是计算。
- **`run_in_executor`**：`to_thread` 的底层，需要选线程池/进程池时用它。

---

## 七、映射回 Agent 工程

今天学的每一样，在阶段 5 都有明确出处：

| 今天的工具 | Agent 里的用处 |
|---|---|
| `gather` | 并行工具调用：模型一次返回 3 个 `tool_calls`，同时执行 |
| `Semaphore` | 限流：对 LLM API 的并发上限、对向量库的 QPS 上限 |
| `asyncio.timeout` | 单个工具的时限；超时就回填一条"工具超时"给模型，而不是整个请求挂掉 |
| `async for` | 流式输出 token；流式读大文档做 ingestion |
| `Queue` | ingestion 流水线：解析 → 分块 → embedding 三段用队列串起来 |
| `to_thread` | 包同步的 embedding 库、同步的 DB 驱动 |
| `TaskGroup` | 多 Agent 协作：一个子 Agent 失败时把同批其他子任务停掉 |

---

## 八、十个坑

1. **`time.sleep()` 在协程里会卡死整个事件循环**——必须 `await asyncio.sleep()`。它不"挂起"，它真的让整个线程睡了。
2. **漏写 `await` 不报错**，你只是拿到一个没人驱动的 coroutine 对象，最后 `RuntimeWarning` 提示 "was never awaited"。
3. **以为 `gather` 按完成顺序返回结果**——实际按参数顺序。
4. **用列表推导做并发**：`[await f(x) for x in xs]` 是串行。
5. **`create_task` 之后不 await**，异常被静默吞掉，或者任务在循环关闭时被杀。
6. **手写 `acquire`/`release`** 导致名额泄漏，闸门越开越小。
7. **`except Exception` 抓 `CancelledError`** 抓不到；反过来 `except BaseException` 吞掉它会让取消失效。
8. **在协程里调同步库**（`requests.get`、`psycopg2`、`time.sleep`）——整条循环停摆。用 `to_thread`。
9. **每个请求新建 `AsyncClient`**，连接池白建，性能比同步还差。
10. **`asyncio.run()` 只能在最外层调用一次**，不能在已有事件循环里嵌套调用（Jupyter 里要 `await` 而不是 `asyncio.run`）。

---

## 九、学习顺序与验收

按文件顺序做，每个文件独立可跑：

| 文件 | 树上的位置 | 核心考点 |
|---|---|---|
| `python/00_trace.py` | ② 概念层 | 用 `inspect.getcoroutinestate()` 看四态变化 |
| `python/01_coroutine.py` | ② 概念层 | 协程惰性执行；两个协程交替而非并行 |
| `python/02_task.py` | ③ 调度层 | 结果顺序 vs 完成顺序；TaskGroup 一败俱败 |
| `python/03_control.py` | ④ 控制层 | 名额上限；超时会取消；`CancelledError` 必须重抛 |
| `python/04_resources.py` | ⑤ 资源层 | `__aexit__` 保证清理；异步生成器；Queue 背压 |
| `python/05_fetch.py` | ⑥ 生态层（**今日产出**） | 三层嵌套；失败归一化不拖垮整批 |

验收标准（计划原文）：**能不看教程手写 `asyncio.gather` 并发调用**，并且能说清"协程是交替不是并行"。

跑法：

```bash
uv run day03/python/00_trace.py
uv run day03/python/01_coroutine.py
uv run day03/python/05_fetch.py            # 默认走本地 Mock，不联网
uv run day03/python/05_fetch.py --real     # 真打公共 API
```

笔记在 `notes/day03/asyncio-concurrency.md`，配三幅可交互图（`notes/day03/assets/`）。

# Day 3 · asyncio 知识树

六个名词不是并列的六件事，而是一条由问题到工具的链。按树的顺序阅读，每一层回答上一层留下的问题。

```text
asyncio
│
├─ ① 前提层：为什么需要它
│   └─ 一次请求绝大部分时间在等待 IO；线程成本高；CPU 密集任务不适用
│
├─ ② 概念层：三个名词
│   ├─ coroutine   async def 定义的可暂停函数，调用返回对象，函数体不执行
│   ├─ event loop  唯一的驱动者，维护就绪队列
│   └─ await        交还控制权的语法标记
│
├─ ③ 调度层：如何让它们一起运行
│   ├─ Task         coroutine 的驱动壳，create_task 立即排期
│   ├─ gather       批量排期，按参数顺序交付结果
│   ├─ TaskGroup    结构化并发，单个失败导致全体取消（3.11+）
│   └─ as_completed 按完成顺序逐个交付
│
├─ ④ 控制层：如何约束
│   ├─ Semaphore    并发上限
│   ├─ Lock/Event   互斥与信号
│   ├─ timeout      总时限，超时抛 TimeoutError 并取消
│   └─ cancel       协作式取消，CancelledError 必须重新抛出
│
├─ ⑤ 资源层：生命周期与流
│   ├─ async with   __aenter__ / __aexit__，对应同步的 enter/exit
│   ├─ async for    __aiter__ / __anext__，最常见形式是异步生成器
│   └─ Queue        生产者-消费者，天然形成背压
│
└─ ⑥ 生态层：接入真实组件
    ├─ httpx.AsyncClient  连接池与分阶段超时
    └─ asyncio.to_thread  同步库的接入通道
```

---

## 一、前提层：为什么会有 asyncio

一次 LLM 调用期间，进程的 CPU 占用如下：

```text
发起 socket 写入  ▏1ms  CPU
等待远端推理      ▏3000ms  纯等待，CPU 空闲
读取响应          ▏1ms  CPU
```

99.9% 的时间 CPU 不执行任何计算。性能瓶颈不在计算量，而在等待。

两条解法：

| 方案 | 代价 | 适用场景 |
|---|---|---|
| 多线程 | 每线程 1-8MB 栈空间；切换需进入内核；GIL 限制字节码并发 | 已有同步库、连接数不超过数百 |
| 事件循环 | 单线程，协程栈仅数 KB；切换是用户态函数返回 | 高并发 IO、连接数上千 |

事件循环的核心思想：把等待从线程中移出，改为一张登记表。任务登记等待的条件，条件满足后重新进入就绪队列；等待期间不占用线程。

> [!warning] 不适用场景
> CPU 密集任务（矩阵运算、压缩、图像处理）使用 asyncio 没有收益：没有等待可以交出，单线程仍然只是单线程。
> 这类任务应使用 **多进程**（`multiprocessing` / `ProcessPoolExecutor`），各进程拥有独立解释器，绕开 GIL。

---

## 二、概念层：三个名词

### coroutine

```python
async def f():
    print("hello")


coro = f()  # 只创建对象，函数体不执行
print(coro)  # <coroutine object f at 0x...>
```

`async def` 定义的是一个可暂停的函数。底层机制与 Day 2 的生成器相同：coroutine 就是实现了 `__await__` 协议的生成器。区别只在协议——生成器用 `send()` 推进，coroutine 用 `await` 驱动。

> [!important] 与生成器的关系
> 生成器调用后执行 0 行，`next()` 才推进。coroutine 完全一致：`await` 就是那个 `next()`。
> 因此「协程不会自行运行」不是 asyncio 的特殊规定，而是同一机制的必然结果。

### event loop

循环本体只做一件事：

```text
while True:
    取出就绪队列里的下一个回调，执行它
    执行到 await -> 该协程登记等待条件，交还控制权
    检查等待条件已满足的回调 -> 重新放入就绪队列
```

`asyncio.run(coro)` 即：建立一个循环、把 coro 放入、运行至空、关闭循环。

### await

`await x` 的准确含义是把 x 执行到底。

x 内部每遇到一个真正需要等待的挂起点（`asyncio.sleep`、网络读、`Queue.get`），才交还控制权。循环利用这段时间运行其他 Task，待 x 的条件满足后继续执行。

> [!important] `await` 是可能挂起，不是一定挂起
> 若被 await 的对象当场就能返回结果（例如一个没有 `await` 的子协程、一个已完成的 Future），
> 整个 `await` 会在同一次 `send()` 内执行完毕，控制权不会回到循环。
> 只有条件未就绪时才会让出。这一点决定了某些看似并发的代码实际并未并发，见 `00_trace.py` 第 6 段。

#### 进入就绪队列的是 Task，不是协程

这是最容易说错的一处。「`await` 后面的协程进入就绪态」是**不准确**的说法 —— 协程对象没有身份，不能被调度。

| 写法 | 新建 Task | ready 队列多出什么 | 实测 |
|---|---|---|---|
| `await coro()`，不挂起 | 否 | **空** | 零调度动作 |
| `await coro()`，内部挂起 | 否 | 承载它的那个 Task 的 `task_wakeup` | `call_soon(Task.task_wakeup)` |
| `create_task(coro)` | **是** | 新 Task 的 `__step` | `call_soon(TaskStepMethWrapper)` |

所以：

- `await coro()` **不新建 Task**，协程体在当前 Task 的栈上就地展开。它只是「跑一段代码」，不是一个调度实体。
- 但一旦它内部挂起，**当前这个 Task** 会被重新排进 ready 队列 —— 恢复的是 Task，不是协程。
- `create_task` 才是「新建调度实体」：立刻把新 Task 的 `__step` 放进 ready 队列，但**不会立刻执行**，要等当前 Task 让出。

一句话：**Task 是调度单位，协程是 Task 肚子里跑的东西。**

> [!danger] 漏写 `await` 的真实后果
> `results = fetch_all(...)` 之后，协程体**一行都没执行** —— 不是「排期了但没跑」，是**根本没进调度**，
> 连 Task 都没建。拿到的是一个死对象，后续任何操作都是 `TypeError`，进程退出时再补一句
> `RuntimeWarning: coroutine was never awaited`。
>
> 这和「`create_task` 之后没 await」不是一回事：后者至少已经排期、会运行，只是异常没人收。


两个术语需要区分，混用会导致判断错误：

| | 阻塞（Java 线程） | 挂起（Python 协程） |
|---|---|---|
| 栈 | 保留在线程上，占用内存 | 冻结在堆上，线程栈清空 |
| 谁在等待 | 内核将其移出 CPU，进入等待队列 | 协程自行返回，循环继续运行 |
| 能否执行其他任务 | 需要另一个线程 | 同一线程可立即执行其他协程 |
| 恢复 | 由内核调度器决定 | 条件满足后，回调将其重新放入就绪队列 |

---

## 二·五、与 Java 线程模型对照

Java 的线程状态是内核对象，有公开枚举与 API；Python 的状态保存在 coroutine 的内部帧中，同一个 `SUSPENDED` 覆盖了 Java 的三个等待态。

| Java `Thread.State` | Python `inspect.getcoroutinestate()` |
|---|---|
| `NEW` | `CORO_CREATED`（调用 `async def` 后，函数体未执行） |
| `RUNNABLE` | `CORO_RUNNING`（`Task.__step` 正在驱动） |
| `WAITING` / `TIMED_WAITING` / `BLOCKED` | `CORO_SUSPENDED`（停在某个 `await` 上，不区分等待类型） |
| `TERMINATED` | `CORO_CLOSED`（耗尽、异常或被取消） |

API 对应：

| Java | Python | 差异 |
|---|---|---|
| `new Thread(r)` | `asyncio.create_task(coro)` | 两者都只是排期，尚未执行 |
| `t.start()` | **无对应物** | Python 的启动即下一次循环迭代，不可显式触发 |
| `t.join()` | `await task` | 同样等待调用方，但 Python 是让出而非阻塞线程 |
| `t.isAlive()` | `not task.done()` | 一致 |
| `t.getState()` | `inspect.getcoroutinestate(...)` | 粒度更粗，不区分等待原因 |
| `Thread.sleep(ms)` | `await asyncio.sleep(s)` | 必须 `await`，否则整个循环阻塞 |
| `t.interrupt()` | `task.cancel()` | 都是发出请求，不是立即终止 |
| `ExecutorService.submit()` | `create_task` | 一致 |
| `invokeAll()` | `asyncio.gather` / `TaskGroup` | 仅 TaskGroup 具备「一败俱败」 |
| `Semaphore` | `asyncio.Semaphore` | 几乎完全一致 |
| `CountDownLatch(1)` | `asyncio.Event` | `wait()` / `set()` |
| `ThreadLocal` | `contextvars.ContextVar` | Agent 中用于存放 trace_id |

唯一真正缺失的是 `t.start()`。Java 中创建与启动分为两步，可以先 `new` 再决定何时 `start`；Python 的 `create_task` 一次完成，但必须让出控制权才开始执行，因此 `create_task` 返回时状态仍是 `CORO_CREATED`。这是最容易判断错的一处。

`await` 在实现上是 `yield from x.__await__()`，事件循环的工作就是反复调用 `coro.send(None)`。可通过 `python/00_trace.py` 验证。

---

## 三、调度层：如何让它们一起运行

| 写法 | 含义 | 结果顺序 | 单项失败时 |
|---|---|---|---|
| `await f()` | 执行到底，不创建 Task | — | 直接抛出 |
| `create_task(f())` | 立即排期，不等待 | 无返回值，需自行 await Task | 挂在 Task 上，不主动抛出 |
| `gather(*coros)` | 全部排期，一起等待 | 按参数顺序 | **立刻抛给调用方，且不取消兄弟**（除非 `return_exceptions=True`） |
| `TaskGroup()` | 结构化并发块 | 自行管理 | 全体取消，抛 `ExceptionGroup` |
| `as_completed(tasks)` | 迭代，先完成者先交付 | 按完成顺序 | 在迭代中抛出 |

### `gather` 的异常策略：默认既不捕获，也不取消兄弟

最常见的误解是「`gather` 会兜住异常，所以整批正常返回」。实测：

```text
=== 默认 gather ===
  a 正常跑完
  调用方收到异常: b 炸了          ← 异常抛给了调用方
  c 正常跑完                      ← c 没被取消，还在后台跑完了

=== return_exceptions=True ===
  交付: ['a', ValueError('b 炸了'), 'c']   ← 异常变成【值】占位
```

两条要记住：

1. **默认一错就抛。** 只有 `return_exceptions=True` 时才把异常当成结果元素返回。
2. **默认不取消兄弟。** `b` 炸了之后 `c` 照样跑完。要「一败俱败」只能用 `TaskGroup`。

> [!note] 那 `05_fetch.py` 为什么整批没崩
> 因为 `fetch_one` **自己**用 `try/except` 把异常吞成了返回的 dict，`gather` 从头到尾只看到正常返回。
> 「整批活下来」是 `fetch_one` 的功劳，不是 `gather` 的。删掉那个 `except`，`gather` 会立刻让整批炸掉。


### 两个顺序，两个来源

「结果顺序由谁决定」这个问题过于笼统，会得到自相矛盾的答案。拆成两个：

| 顺序 | 产生方 | 证据 |
|---|---|---|
| 完成顺序 | 事件循环调度（定时器堆 + 就绪队列） | `fast→mid→slow`，由各自 delay 决定 |
| 交付顺序 | 组合器是否重排 | 见下表 |

同一批任务用三种收集方式，实测结果：

```text
gather        交付=['slow','fast','mid']   真实完成=['fast','mid','slow']
as_completed  交付=['fast','mid','slow']   真实完成=['fast','mid','slow']
[await t ...] 交付=['slow','fast','mid']   真实完成=['fast','mid','slow']
```

- **`gather` 会重排**：丢弃调度产生的完成顺序，按参数下标恢复结果位置。这是真正的编排，与调度结果无关。
- **`as_completed` 不编排**：先完成者先交付，原样透传调度结果。称其「编排顺序」是不准确的。
- **`TaskGroup` 不交付结果**：它只负责取消语义，结果需自行写入外部容器。

因此准确的因果是：

```text
create_task    → 任务进入就绪队列（提交）
事件循环       → 决定每个任务何时完成（调度，产出完成顺序）
组合器         → 决定交付顺序：重排（gather）/ 透传（as_completed）/ 不交付（TaskGroup）
```

> [!warning] Python 没有协程池
> 这是 Java `ExecutorService` 带来的错误联想。asyncio 中没有 worker 线程，也没有任务排队等待空闲 worker。
> `create_task` 之后所有任务同时处于运行中状态，各自停在 `await` 上；Task 是「协程加一个驱动壳」，用完即弃。
> `as_completed` 内部有一个 `asyncio.Queue`，那是完成事件的信箱，不是任务池。

### 为什么 `for ... await` 不是串行

这一点最反直觉。看这段代码：

```python
for x in asyncio.as_completed(ts):
    result = await x
```

字面上像逐个等待，但三个任务确实是并发的。原因是被挂起的是 `main` 这一个协程，不是事件循环：

```text
t=0.002  main  create_task x3  → 三个任务已排期，均未开始
t=0.002  main  进入 for，await 一个空队列  → main 挂起，控制权交回 loop
t=0.002  loop  开始执行：依次启动 slow / mid / fast，三个都停在 sleep
t=0.057  fast  完成 → 完成回调把 fast 放入队列 → 唤醒 main
t=0.057  main  取得 'fast'，append → 下一轮 await，队列空 → 再次挂起
t=0.148  mid   完成 → 同上
t=0.303  slow  完成 → 同上，循环结束
```

把时间轴拆成两列观察：

| 时刻 | `main` 的行为 | 三个任务的行为 |
|---|---|---|
| 0.002 | 挂起，等待队列 | 刚被启动，各自 sleep |
| 0.057 | 醒来，处理 fast，再次挂起 | fast 完成；mid / slow 仍在等待 |
| 0.148 | 醒来，处理 mid，再次挂起 | mid 完成；slow 仍在等待 |
| 0.303 | 醒来，处理 slow，结束 | slow 完成 |

**`main` 确实是串行的——它一次只处理一个结果。但任务不是由它驱动的。** 任务在 `main` 挂起的间隙各自推进，这才是并发的来源。

对照 Java：`as_completed` 相当于 `ExecutorCompletionService`。

```java
ExecutorCompletionService<String> cs = new ExecutorCompletionService<>(pool);
for (int i = 0; i < 3; i++) cs.submit(task);
for (int i = 0; i < 3; i++) {
    String r = cs.take().get();   // 同样逐个获取，但任务早已在线程池中运行
}
```

`cs.take()` 串行，三个任务并行。Python 这行代码形状相同，只是线程池换成了事件循环。

> [!warning] 前提条件
> 任务内部必须有真正的挂起点（`await asyncio.sleep` / 网络 IO / `Queue.get`）。
> 若三个任务是纯 CPU 计算、从不 `await`，第一个会占满循环，
> 后两个没有机会启动，`as_completed` 退化为串行。
> 并发来自挂起点，不是来自 `as_completed`。

三个必须区分的点：

1. **`gather` 的结果顺序不等于完成顺序。** `gather(slow, fast)` 返回 `[slow 的结果, fast 的结果]`，即使 fast 先完成。这是最常见的误读。
2. **`[await f(x) for x in xs]` 是串行。** 列表推导不会产生并发，每个 `await` 都在原地等待完成。
3. **`create_task` 之后必须有人 await 它。** 否则任务继续运行，异常无人接收，程序退出时被静默丢弃（"Task was destroyed but it is pending"）。

> [!tip] 为什么 TaskGroup 更适合作为默认选择
> `gather` 中单项失败时，其他 Task 继续运行——调用方拿到了异常，但其余任务仍在消耗资源。
> `TaskGroup` 是结构化并发：块内任一任务失败，其余立即取消，块统一抛 `ExceptionGroup`。对 Agent 服务（单个工具失败时无需等待其余）这是正确的行为。

---

## 四、控制层：如何约束

并发建立之后，必须能够限制与中断。

### Semaphore

带计数的许可池。`async with sem` 获取名额，离开时自动归还。

```python
sem = asyncio.Semaphore(3)  # 最多 3 个同时进入


async def one(u):
    async with sem:  # 名额用尽时在此排队
        return await client.get(u)
```

> [!danger] 名额泄漏
> 不用 `async with` 而手写 `acquire()` / `release()` 时，若中途抛异常或任务被取消，
> `release()` 不执行，名额永久减少，可用名额逐步收紧直至阻塞。
> 应始终使用 `async with sem`，它保证 `finally` 语义。

### timeout

```python
async with asyncio.timeout(2.0):  # 3.11+
    resp = await client.get(url)
```

超时抛 `TimeoutError`，并取消内部正在运行的任务，不会放任其继续运行。

旧写法 `await asyncio.wait_for(coro, 2.0)` 等价，但 `asyncio.timeout` 可以包住一段多步逻辑
（例如三次请求加两次重试整体限时 2 秒），`wait_for` 只能包一个协程。

### cancel

```python
task = asyncio.create_task(f())
task.cancel()  # 不是立即终止，而是下次到达 await 点时抛 CancelledError
```

协作式取消：被取消的协程在 `await` 点收到 `asyncio.CancelledError`，可以执行清理，但必须重新抛出。

> [!danger] 最难排查的一类缺陷
> `CancelledError` 在 3.8+ 继承自 `BaseException` 而非 `Exception`，目的是防止被 `except Exception` 吞掉。
> 若写成 `except BaseException:` 且不重新抛出，任务会「正常结束」——调用方以为已取消，实际仍在运行。

---

## 五、资源层：生命周期与流

### async with

与同步 `with` 一一对应：

| 同步 | 异步 |
|---|---|
| `__enter__` | `__aenter__` |
| `__exit__` | `__aexit__` |
| `with x:` | `async with x:` |
| `@contextmanager` | `@asynccontextmanager` |

`__aexit__` 返回 `True` 同样表示吞掉异常。`@asynccontextmanager` 同样是「定义在 `contextlib` 中的标准库函数，不是语言语法」——Day 2 的结论在此同样成立。

### async for

`async for` 依赖 `__aiter__` / `__anext__`，最常见的形式是异步生成器：

```python
async def paginate(url):
    while url:
        resp = await client.get(url)
        yield resp.json()
        url = resp.json().get("next")
```

`async for page in paginate(...)` 边等待边消费，无需把所有页先读入内存。流式输出（LLM 的 token 流）采用同一形状。

### Queue

`asyncio.Queue` 是线程安全队列的协程版，天然带背压：队满时 `put` 挂起，队空时 `get` 挂起。生产者与消费者通过它解耦。

---

## 六、生态层：接入真实组件

- **`httpx.AsyncClient`**：连接池是其主要价值。一次 `async with` 建立一个 client，所有请求复用 TCP 连接，
  比每个请求新建连接快一个数量级。它的 `timeout` 管理单个阶段（连接 / 读取），
  `asyncio.timeout` 管理整个协程，两者都需要。
- **`asyncio.to_thread(fn, *args)`**：把同步阻塞函数交给线程池执行，是接入旧库
  （`requests`、同步版 `psycopg2`、本地文件 IO）的通道。它与 GIL 的限制不冲突——线程中执行的是等待，不是计算。
- **`run_in_executor`**：`to_thread` 的底层实现，需要指定线程池或进程池时使用。

---

## 七、映射回 Agent 工程

本节各项在阶段 5 均有明确用途：

| 工具 | Agent 中的用处 |
|---|---|
| `gather` | 并行工具调用：模型一次返回 3 个 `tool_calls`，同时执行 |
| `Semaphore` | 限流：LLM API 的并发上限、向量库的 QPS 上限 |
| `asyncio.timeout` | 单个工具的时限；超时后回填「工具超时」给模型，而不是整个请求失败 |
| `async for` | 流式输出 token；流式读取大文档做 ingestion |
| `Queue` | ingestion 流水线：解析、分块、embedding 三段以队列串联 |
| `to_thread` | 包装同步的 embedding 库与同步的数据库驱动 |
| `TaskGroup` | 多 Agent 协作：单个子 Agent 失败时取消同批其余子任务 |

---

## 八、十项常见错误

1. **在协程中调用 `time.sleep()` 会阻塞整个事件循环**——必须使用 `await asyncio.sleep()`。它不挂起，而是让整个线程睡眠。
2. **漏写 `await` 不会报错**，只会得到一个未被驱动的 coroutine 对象，最终由 `RuntimeWarning` 提示 "was never awaited"。
3. **误以为 `gather` 按完成顺序返回结果**——实际按参数顺序。
4. **用列表推导实现并发**：`[await f(x) for x in xs]` 是串行。
5. **`create_task` 之后不 await**，异常被静默吞掉，或任务在循环关闭时被终止。
6. **手写 `acquire` / `release`** 导致名额泄漏，可用名额逐步收紧。
7. **用 `except Exception` 捕获 `CancelledError`** 捕获不到；反之用 `except BaseException` 吞掉它会使取消失效。
8. **在协程中调用同步库**（`requests.get`、`psycopg2`、`time.sleep`）——整个循环停止推进。应使用 `to_thread`。
9. **每个请求新建 `AsyncClient`**，连接池失去作用，性能低于同步实现。
10. **`asyncio.run()` 只能在最外层调用一次**，不能在已有事件循环中嵌套调用（Jupyter 中应使用 `await` 而非 `asyncio.run`）。

---

## 九、学习顺序与验收

按文件顺序执行，每个文件独立可运行：

| 文件 | 树上位置 | 核心考点 |
|---|---|---|
| `python/00_trace.py` | ② 概念层 | 用 `inspect.getcoroutinestate()` 观察四种状态的变化 |
| `python/01_coroutine.py` | ② 概念层 | 协程惰性执行；两个协程交替而非并行 |
| `python/02_task.py` | ③ 调度层 | 结果顺序与完成顺序的区别；TaskGroup 一败俱败 |
| `python/03_control.py` | ④ 控制层 | 名额上限；超时会取消；`CancelledError` 必须重新抛出 |
| `python/04_resources.py` | ⑤ 资源层 | `__aexit__` 保证清理；异步生成器；Queue 背压 |
| `python/05_fetch.py` | ⑥ 生态层（当日产出） | 三层嵌套；失败归一化不影响整批 |

验收标准（计划原文）：能不查阅教程手写 `asyncio.gather` 并发调用，并能说明「协程是交替而非并行」。

运行方式：

```bash
uv run day03/python/00_trace.py
uv run day03/python/01_coroutine.py
uv run day03/python/05_fetch.py            # 默认使用本地 Mock，不联网
uv run day03/python/05_fetch.py --real     # 请求公共 API
```

笔记见 `notes/day03/asyncio-concurrency.md`，配三幅可交互图（`notes/day03/assets/`）。

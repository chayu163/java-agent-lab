"""Day 3 · 练习 4：资源层 —— async with / async for / Queue

这一节钉三件事：
    1. async with 认的是 __aenter__ / __aexit__，@asynccontextmanager 只是标准库的一个函数
    2. async for 认的是 __aiter__ / __anext__，异步生成器是最常见的形状
    3. Queue 让生产者和消费者各跑各的，天然带背压

跑法：uv run day03/python/04_resources.py
现在跑会抛 NotImplementedError。
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

# ---------------------------------------------------------------------------
# 1. async with：自己写一个异步上下文管理器
# ---------------------------------------------------------------------------


class FakeSession:
    """模仿 httpx.AsyncClient：进入时建连接，退出时关连接。"""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.closed = False

    async def __aenter__(self) -> "FakeSession":
        self.events.append("open")
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self.events.append("close")
        self.closed = True
        return False  # False = 不吞异常


async def use_context_manager(raise_inside: bool) -> tuple[list[str], bool]:
    """在 async with 里（可选）抛异常，返回 (事件序列, 最终是否关闭)。

    ★ 关键：即使 body 里抛异常，__aexit__ 也会执行 —— 这是"保证清理"的语义。
      返回 False 表示不吞，异常会继续往外抛，所以外层要接住。

    ★ 你这个实现缺了"外层要接住"这一步：body 抛出 ValueError 时，函数直接
      带着异常退出，return 那行根本走不到，测试里 events2 也就拿不到。
      正确做法是在这里 try/except 接住 —— 接到异常本身就证明了它确实往外抛过。
    """
    session = FakeSession()
    try:
        async with session:
            # ❌ if raise_inside == True:
            #    布尔值不要和 True 比较，直接 if raise_inside:。
            if raise_inside:
                raise ValueError("inside")
    except ValueError:
        pass  # 接住只是为了让函数能返回事件序列；异常确实抛出过
    return session.events, session.closed


# ---------------------------------------------------------------------------
# 2. asynccontextmanager：同一个东西的函数式写法
# ---------------------------------------------------------------------------


@asynccontextmanager
async def timed(label: str, log: list[str]) -> AsyncIterator[str]:
    """yield 之前是 __aenter__，之后是 __aexit__。

    log 里追加 f"{label}:enter" 和 f"{label}:exit"。

    ★ 返回类型要写成 AsyncIterator[str]，不是 str 也不是 coroutine。
      yield 决定了它是异步生成器；asynccontextmanager 把它包装成上下文管理器。
    """
    # raise NotImplementedError(
    #     "TODO: log.append(f'{label}:enter'); yield label; log.append(f'{label}:exit')"
    # )
    # yield label  # 让 mypy 认出这是异步生成器；你填完实现后删掉这行
    log.append(f"{label}:enter")
    yield label
    log.append(f"{label}:exit")
    # ❌ 这里原来有一行裸 `return`：
    #    异步生成器里 return 只表示"结束迭代"，不产出值，
    #    但函数末尾本来就会自然结束，这行是多余的，还带尾随空格让 ruff 报 W291。


# ---------------------------------------------------------------------------
# 3. async for：异步生成器（分页就是最典型的场景）
# ---------------------------------------------------------------------------


async def paginate(pages: list[list[int]]) -> AsyncIterator[list[int]]:
    """逐页产出，每页之间 await asyncio.sleep(0) 模拟网络延迟。

    ★ 这是一个【异步生成器】：函数体里有 yield，所以调用它返回的是 async_generator，
      一行都不执行。必须先 async for，或者用 anext()。
    ★ 返回值类型注解写 AsyncIterator[list[int]]，不是 list[list[int]]。

    ❌ 你原来写的是 `-> Any`，还包了一层 try/except 原样 re-raise。
       注解写 Any 等于关掉 mypy 检查，文档里说的 AsyncIterator 就白写了；
       而那个 try/except 只是打印一句再抛回去，没有任何收益。
       生成器的异常本来就会自然地传给调用方，不需要手动转发。
    """
    for page in pages:
        await asyncio.sleep(0)
        yield page


async def consume_pages(pages: list[list[int]]) -> list[int]:
    """用 async for 把分页拍平成一维列表。"""
    # raise NotImplementedError("TODO: async for page in paginate(pages): out.extend(page)")
    result: list[int] = []
    async for page in paginate(pages):
        result.extend(page)
    return result


# ---------------------------------------------------------------------------
# 4. Queue：生产者-消费者流水线
# ---------------------------------------------------------------------------


async def run_pipeline(items: list[str]) -> tuple[list[str], int]:
    """两段流水线：producer 往队列塞，consumer 取出来转大写。

    返回 (处理后的列表, 队列被塞满过的最多次数)。

    ★ 队列 maxsize=2：put 在第 3 个元素时就会挂起等消费者来取，
      这就是【背压】——生产者被消费者的速度约束住，不会无限堆内存。
    ★ 结束信号：塞一个 None 进去，consumer 看到 None 就退出。
      不要用 queue.empty() 判断结束，那玩意在并发下不可靠。
    """

    # ❌ async for item in items:
    #    items 是普通 list，没有 __aiter__。async for 只能遍历【异步迭代器】。
    #    运行到这里直接 TypeError: 'async for' requires an object with __aiter__ method。
    #    普通列表用普通 for。
    #
    # ❌ queue.put(None) 但队列声明成 Queue[str]
    #    结束信号是 None，所以类型应该是 Queue[str | None]。
    #
    # ❌ return processed, queue.maxsize
    #    maxsize 是你【设置的上限】，永远等于 2，不是"实际塞满过几次"。
    #    断言 max_waiting <= 2 因此永远成立，测了个寂寞。
    #    要测背压，得在 put 之后记录 queue.qsize() 的实际峰值。
    async def producer(queue: asyncio.Queue[str | None]) -> None:
        for item in items:
            await queue.put(item)
            tracker["peak"] = max(tracker["peak"], queue.qsize())
        await queue.put(None)  # 结束信号

    async def consumer(queue: asyncio.Queue[str | None], processed: list[str]) -> None:
        while True:
            item = await queue.get()
            if item is None:
                break
            processed.append(item.upper())

    queue: asyncio.Queue[str | None] = asyncio.Queue(maxsize=2)
    processed: list[str] = []
    tracker = {"peak": 0}
    await asyncio.gather(producer(queue), consumer(queue, processed))
    return processed, tracker["peak"]


async def main() -> None:
    events, closed = await use_context_manager(raise_inside=False)
    assert events == ["open", "close"], f"正常路径: {events}"
    assert closed is True

    events2, closed2 = await use_context_manager(raise_inside=True)
    assert events2 == ["open", "close"], f"异常路径也必须 close: {events2}"
    assert closed2 is True

    # @asynccontextmanager 版
    log: list[str] = []
    async with timed("t", log) as label:
        assert label == "t"
        log.append("body")
    assert log == ["t:enter", "body", "t:exit"], f"asynccontextmanager: {log}"

    # async for
    pages = [[1, 2], [3], [], [4, 5, 6]]
    gen = paginate(pages)
    assert hasattr(gen, "__anext__"), "异步生成器应该实现 __anext__"
    assert await consume_pages(pages) == [1, 2, 3, 4, 5, 6]

    # Queue
    processed, max_waiting = await run_pipeline([f"x{i}" for i in range(6)])
    assert processed == [f"X{i}" for i in range(6)], f"顺序应该是 FIFO: {processed}"
    assert max_waiting <= 2, f"maxsize=2 时队列不该堆超过 2 个: {max_waiting}"


if __name__ == "__main__":
    asyncio.run(main())
    print("04_resources: 全部通过")

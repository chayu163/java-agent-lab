"""Day 3 · 练习 4：资源层 —— async with / async for / Queue

本节验证三件事：
    1. async with 依赖 __aenter__ / __aexit__；@asynccontextmanager 只是标准库函数
    2. async for 依赖 __aiter__ / __anext__，最常见的形式是异步生成器
    3. Queue 使生产者与消费者各自独立运行，并天然形成背压

运行：uv run day03/python/04_resources.py
"""

import asyncio
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager
from typing import Any

# ---------------------------------------------------------------------------
# 1. async with：手写异步上下文管理器
# ---------------------------------------------------------------------------


class FakeSession:
    """模仿 httpx.AsyncClient：进入时建立连接，退出时关闭连接。"""

    def __init__(self) -> None:
        self.events: list[str] = []
        self.closed = False

    async def __aenter__(self) -> "FakeSession":
        self.events.append("open")
        return self

    async def __aexit__(self, exc_type: Any, exc: Any, tb: Any) -> bool:
        self.events.append("close")
        self.closed = True
        # 返回 False 表示不吞异常
        return False


async def use_context_manager(raise_inside: bool) -> tuple[list[str], bool]:
    """在 async with 内可选地抛异常，返回 (事件序列, 最终是否关闭)。

    ★ 函数体即使抛异常，__aexit__ 仍会执行，这是「保证清理」的语义。
      __aexit__ 返回 False 表示不吞异常，异常继续向外传播，因此外层必须捕获。

    ★ 外层如果不捕获，函数会带着异常退出，return 语句不会执行，调用方拿不到
      事件序列。这里用 try/except 接住，捕获到异常本身就证明它确实向外传播过。
    """
    session = FakeSession()
    try:
        async with session:
            # 布尔值直接用于条件判断，不需要与 True 比较。
            if raise_inside:
                raise ValueError("inside")
    except ValueError:
        # 捕获只为让函数能返回事件序列；异常确实向外传播过。
        pass
    return session.events, session.closed


# ---------------------------------------------------------------------------
# 2. asynccontextmanager：同一件事的函数式写法
# ---------------------------------------------------------------------------


@asynccontextmanager
async def timed(label: str, log: list[str]) -> AsyncIterator[str]:
    """yield 之前的部分对应 __aenter__，之后对应 __aexit__。

    向 log 追加 f"{label}:enter" 与 f"{label}:exit"。

    ★ 返回类型写作 AsyncIterator[str]，不是 str，也不是 coroutine。
      函数体含 yield，因而是异步生成器；asynccontextmanager 将其包装为上下文管理器。
    """
    log.append(f"{label}:enter")
    yield label
    log.append(f"{label}:exit")


# ---------------------------------------------------------------------------
# 3. async for：异步生成器（分页是最典型的场景）
# ---------------------------------------------------------------------------


async def paginate(pages: list[list[int]]) -> AsyncIterator[list[int]]:
    """逐页产出，页间 await asyncio.sleep(0) 模拟网络延迟。

    ★ 这是异步生成器：函数体含 yield，调用它返回 async_generator，一行都不执行。
      必须用 async for 或 anext() 驱动。
    ★ 返回类型注解写 AsyncIterator[list[int]]，不是 list[list[int]]。

    ❌ 若注解写成 Any，等于对 mypy 关闭类型检查，上一行的约定就失去作用。
       生成器抛出的异常本就自动传给调用方，不需要在内部 try/except 后原样重抛；
       在内部包一层只是转发一次异常，没有额外收益。
    """
    for page in pages:
        await asyncio.sleep(0)
        yield page


async def consume_pages(pages: list[list[int]]) -> list[int]:
    """用 async for 把分页结果拍平成一维列表。"""
    result: list[int] = []
    async for page in paginate(pages):
        result.extend(page)
    return result


# ---------------------------------------------------------------------------
# 4. Queue：生产者-消费者流水线
# ---------------------------------------------------------------------------


async def run_pipeline(items: list[str]) -> tuple[list[str], int]:
    """两段流水线：producer 写入队列，consumer 取出并转为大写。

    返回 (处理后的列表, 队列实际堆积的最大长度)。

    ★ maxsize=2 时，producer 写入第 3 个元素时会挂起等待 consumer 取走，
      这就是背压：生产者的速度被消费者约束，内存不会无限增长。
    ★ 结束信号：写入一个 None，consumer 读到 None 即退出。
      不要用 queue.empty() 判断结束，该判断在并发下不可靠。

    ❌ items 是普通 list，没有 __aiter__，不能用 async for 遍历；
       运行时会抛 TypeError: 'async for' requires an object with __aiter__ method。
    ❌ 结束信号是 None，队列类型应为 Queue[str | None]，否则 mypy 报类型不符。
    ❌ 不要用 queue.maxsize 充当「实际堆积长度」：它等于配置的上限，恒为 2，
       对应断言永远成立，测不到任何东西。堆积长度要在 put 之后读 qsize()。
    """

    async def producer(queue: asyncio.Queue[str | None]) -> None:
        for item in items:
            await queue.put(item)
            tracker["peak"] = max(tracker["peak"], queue.qsize())
        await queue.put(None)

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
    assert events2 == ["open", "close"], f"异常路径同样必须关闭: {events2}"
    assert closed2 is True

    # asynccontextmanager 版本
    log: list[str] = []
    async with timed("t", log) as label:
        assert label == "t"
        log.append("body")
    assert log == ["t:enter", "body", "t:exit"], f"asynccontextmanager: {log}"

    # async for
    pages = [[1, 2], [3], [], [4, 5, 6]]
    gen = paginate(pages)
    assert hasattr(gen, "__anext__"), "异步生成器应实现 __anext__"
    assert await consume_pages(pages) == [1, 2, 3, 4, 5, 6]

    # Queue
    processed, max_waiting = await run_pipeline([f"x{i}" for i in range(6)])
    assert processed == [f"X{i}" for i in range(6)], f"顺序应为 FIFO: {processed}"
    assert max_waiting <= 2, f"maxsize=2 时队列堆积不应超过 2: {max_waiting}"


if __name__ == "__main__":
    asyncio.run(main())
    print("04_resources: 全部通过")

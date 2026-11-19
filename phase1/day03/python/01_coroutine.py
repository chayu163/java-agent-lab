"""Day 3 · 练习 1：概念层 —— coroutine / event loop / await

本节用断言验证三件事：
    1. 调用 async def 只得到 coroutine 对象，函数体一行不执行
    2. 同一个 coroutine 只能被驱动一次
    3. 两个协程同时运行时交替执行，不是并行执行

运行：uv run day03/python/01_coroutine.py

★ 本节不涉及 Task 与 gather 的细节，只确立「协程是什么」。
"""

import asyncio
import itertools


async def ticker(name: str, n: int, delay: float, log: list[str]) -> str:
    """向 log 依次追加 f"{name}{i}" 共 n 次，每次追加后 await asyncio.sleep(delay)。

    返回 f"{name} done"。

    ★ 顺序是先 append 再 sleep，而不是先 sleep 再 append。
      delay=0 时 log 的最终形状由这个顺序决定。
    """
    for i in range(n):
        log.append(f"{name}{i}")
        await asyncio.sleep(delay)
    return f"{name} done"


async def run_concurrent() -> tuple[list[str], list[str]]:
    """同时运行 A、B 两个 ticker（各 3 次，delay=0），返回 (执行顺序, 两个返回值)。

    ★ 用 asyncio.gather 让两者同时开始。
    ★ delay 传 0：asyncio.sleep(0) 是主动让出一次控制权的惯用写法。
      它不等待，只是把控制权交还事件循环，使其他协程得以运行。
    """
    log: list[str] = []
    results = await asyncio.gather(ticker("A", 3, 0, log), ticker("B", 3, 0, log))
    return log, list(results)


if __name__ == "__main__":
    # --- 证据 1：创建不等于执行 ---
    lazy_log: list[str] = []
    coro = ticker("A", 3, 0, lazy_log)
    assert asyncio.iscoroutine(coro) is True, "调用 async def 得到的是 coroutine 对象"
    assert lazy_log == [], "创建 coroutine 时函数体一行都不应执行"
    assert asyncio.run(coro) == "A done"

    # --- 证据 2：同一个 coroutine 只能驱动一次 ---
    coro2 = ticker("C", 1, 0, [])
    asyncio.run(coro2)
    try:
        asyncio.run(coro2)
    except RuntimeError:
        pass
    else:
        raise AssertionError("同一个 coroutine 被驱动两次应抛 RuntimeError")

    # --- 证据 3：交替执行，不是并行执行 ---
    order, results = asyncio.run(run_concurrent())
    assert results == ["A done", "B done"], f"gather 按参数顺序交付: {results}"
    assert len(order) == 6, f"两个 ticker 各 3 次，共 6 条: {order}"

    names = [f"{item[0]}" for item in order]
    alternating = all(a != b for a, b in itertools.pairwise(names))
    assert alternating, f"两个协程应严格交替，实际: {order}"

    assert order[:2] == ["A0", "B0"], f"A0 先执行，A 挂起后才轮到 B0: {order}"

    print("执行顺序:", order)
    print("01_coroutine: 全部通过")

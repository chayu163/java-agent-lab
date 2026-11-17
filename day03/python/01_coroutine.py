"""Day 3 · 练习 1：概念层 —— coroutine / event loop / await

这一节只验证三件事，全部用断言钉死：
    1. async def 调用后只拿到一个 coroutine 对象，函数体一行没跑
    2. 同一个 coroutine 不能被驱动两次
    3. 两个协程一起跑时是【交替】，不是【并行】

跑法：uv run day03/python/01_coroutine.py
现在跑会抛 NotImplementedError —— 那就是给你填的地方。

★ 这一节不涉及 Task、gather 的细节，只把"什么是协程"钉住。
"""

import asyncio
import itertools


async def ticker(name: str, n: int, delay: float, log: list[str]) -> str:
    """往 log 里依次追加 f"{name}{i}" 共 n 次，每次追加完 await asyncio.sleep(delay)。

    返回 f"{name} done"。

    ★ 顺序是"先 append 再 sleep"，不是"先 sleep 再 append"。
      这决定了 delay=0 时最终 log 的形状，注意。
    """
    # raise NotImplementedError(
    #     "TODO: for i in range(n): log.append(f'{name}{i}'); await asyncio.sleep(delay)"
    # )
    for i in range(n):
        log.append(f"{name}{i}")
        await asyncio.sleep(delay)
    return f"{name} done"


async def run_concurrent() -> tuple[list[str], list[str]]:
    """同时跑 A、B 两个 ticker（各 3 次，delay=0），返回 (执行顺序, 两个返回值)。

    ★ 用 asyncio.gather 让它们"同时"开始。
    ★ delay 传 0：asyncio.sleep(0) 是"主动让出一次"的惯用写法，
      它不睡觉，只是把控制权交给循环，让别的协程有机会跑。
    """
    # raise NotImplementedError("TODO: 建 log，gather 两个 ticker，返回 (log, 结果列表)")
    log: list[str] = []
    results = await asyncio.gather(ticker("A", 3, 0, log), ticker("B", 3, 0, log))
    return log, list(results)


if __name__ == "__main__":
    # --- 证据 1：创建 ≠ 执行 ---
    lazy_log: list[str] = []
    coro = ticker("A", 3, 0, lazy_log)
    assert asyncio.iscoroutine(coro) is True, "调用 async def 得到的是 coroutine 对象"
    assert lazy_log == [], "创建 coroutine 时函数体一行都不该执行"
    assert asyncio.run(coro) == "A done"

    # --- 证据 2：同一个 coroutine 只能驱动一次 ---
    coro2 = ticker("C", 1, 0, [])
    asyncio.run(coro2)
    try:
        asyncio.run(coro2)
    except RuntimeError:
        pass
    else:
        raise AssertionError("同一个 coroutine 被驱动两次应该抛 RuntimeError")

    # --- 证据 3：交替，不是并行 ---
    order, results = asyncio.run(run_concurrent())
    assert results == ["A done", "B done"], f"gather 按参数顺序返回: {results}"
    assert len(order) == 6, f"两个 ticker 各 3 次，共 6 条: {order}"

    names = [f"{item[0]}" for item in order]
    alternating = all(a != b for a, b in itertools.pairwise(names))
    assert alternating, f"两个协程应该严格交替，实际: {order}"

    assert order[:2] == ["A0", "B0"], f"A0 先跑，A 睡下后才轮到 B0 —— 这就是交替的证据: {order}"

    print("执行顺序:", order)
    print("01_coroutine: 全部通过")

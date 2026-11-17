"""Day 3 · 实验 0：把 asyncio 的隐式状态机打印出来。

Java 有 Thread.State（NEW / RUNNABLE / BLOCKED / WAITING / TERMINATED）这个显式枚举。
Python 的协程也有状态，只是没人告诉你，它藏在 inspect.getcoroutinestate() 里：

    CORO_CREATED    刚调用 async def 得到对象，一行没跑
    CORO_RUNNING    正在被 Task 驱动执行
    CORO_SUSPENDED  在某个 await 处挂起，等条件满足
    CORO_CLOSED     跑完了（或抛异常终止）

跑法：uv run day03/python/00_trace.py
"""

import asyncio
import inspect
from typing import Any, cast


def state_of(task: asyncio.Task[Any]) -> str:
    """从 Task 反查它持有的 coroutine 的状态。"""
    return inspect.getcoroutinestate(cast(Any, task.get_coro()))


async def worker(name: str, delay: float) -> str:
    print(f"    [worker {name}] 进入函数体")
    await asyncio.sleep(delay)
    print(f"    [worker {name}] 睡醒了")
    return name


async def main() -> None:
    print("=== 1. 调用 async def：只创建对象 ===")
    coro = worker("raw", 0.1)
    print(f"    inspect.getcoroutinestate(coro) = {inspect.getcoroutinestate(coro)}")
    print("    注意：此时函数体一行都没执行")
    coro.close()  # 不关会报 RuntimeWarning

    print()
    print("=== 2. create_task：只是【排期】，还没开始跑 ===")
    task = asyncio.create_task(worker("A", 0.1))
    print(f"    create_task 刚返回：state = {state_of(task)}, done = {task.done()}")
    print("    ↑ CORO_CREATED。create_task 只是把 __step 塞进了 loop 的就绪队列，")

    print()
    print("=== 3. 让出一次控制权，loop 才有机会跑它 ===")
    await asyncio.sleep(0)
    print(f"    await sleep(0) 之后：state = {state_of(task)}")
    print("    ↑ CORO_SUSPENDED。它跑到了 await asyncio.sleep(0.1) 处，挂起了")

    print()
    print("=== 4. 等它完成 ===")
    result = await task
    print(f"    await task 之后：state = {state_of(task)}, result = {result!r}")
    print("    ↑ CORO_CLOSED。coroutine 已经耗尽，Task 里存着返回值")

    print()
    print("=== 5. 事件循环到底在干什么：手动 send() 驱动 ===")

    async def no_await() -> str:
        return "立刻返回"

    plain = no_await()
    print(f"    无 await 的协程，创建后: {inspect.getcoroutinestate(plain)}")
    try:
        plain.send(None)
    except StopIteration as stop:
        print(f"    send(None) 直接抛 StopIteration，返回值在 .value: {stop.value!r}")
    print(f"    驱动后: {inspect.getcoroutinestate(plain)}")

    manual = worker("manual", 0)
    print(f"    有 await 的协程，创建后: {inspect.getcoroutinestate(manual)}")
    manual.send(None)
    print(f"    第一次 send(None) 后: {inspect.getcoroutinestate(manual)}  ← yield 挂起了")
    print("    ↑ await asyncio.sleep(0) 即使延迟为 0，也是一次【主动让出】。")
    print("      事件循环干的全部事情就是反复 send(None)，直到 StopIteration。")

    print()
    print("=== 6. 关键：await 是【可能】挂起，不是【一定】挂起 ===")

    async def no_suspend() -> str:
        return "我没有 await，不会挂起"

    async def outer() -> str:
        print("        outer: 即将 await 一个不挂起的协程")
        value = await no_suspend()
        print(f"        outer: 拿到了 {value!r}，我还在同一次 send 里")
        return "outer 完成"

    probe = outer()
    try:
        probe.send(None)
    except StopIteration as stop:
        print(f"    send(None) 一次就抛了 StopIteration: {stop.value!r}")
    print("    ↑ 从头跑到尾，中途【没有】返回过。说明这次 await 没挂起。")
    print("      只有被 await 的对象还没就绪时，才会真的让出去。")


if __name__ == "__main__":
    asyncio.run(main())

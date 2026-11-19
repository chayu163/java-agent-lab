"""Day 3 · 实验 0：打印 asyncio 的协程状态机。

Java 有显式的 Thread.State 枚举（NEW / RUNNABLE / BLOCKED / WAITING / TERMINATED）。
Python 协程同样有状态，只是没有暴露为公开枚举，可通过 inspect.getcoroutinestate() 读取：

    CORO_CREATED    调用 async def 得到对象，函数体未执行
    CORO_RUNNING    正被 Task 驱动执行
    CORO_SUSPENDED  在某个 await 处挂起，等待条件满足
    CORO_CLOSED     执行结束，或因异常终止

运行：uv run day03/python/00_trace.py
"""

import asyncio
import inspect
from typing import Any, cast


def state_of(task: asyncio.Task[Any]) -> str:
    """从 Task 反查其持有的 coroutine 的状态。"""
    return inspect.getcoroutinestate(cast(Any, task.get_coro()))


async def worker(name: str, delay: float) -> str:
    print(f"    [worker {name}] 进入函数体")
    await asyncio.sleep(delay)
    print(f"    [worker {name}] 等待结束")
    return name


async def main() -> None:
    print("=== 1. 调用 async def：只创建对象 ===")
    coro = worker("raw", 0.1)
    print(f"    inspect.getcoroutinestate(coro) = {inspect.getcoroutinestate(coro)}")
    print("    此时函数体一行都未执行")
    # 不关闭会触发 RuntimeWarning: coroutine was never awaited
    coro.close()

    print()
    print("=== 2. create_task：仅排期，尚未开始 ===")
    task = asyncio.create_task(worker("A", 0.1))
    print(f"    create_task 刚返回：state = {state_of(task)}, done = {task.done()}")
    print("    ↑ CORO_CREATED。create_task 只是把 __step 放入 loop 的就绪队列")

    print()
    print("=== 3. 让出一次控制权，loop 才有机会执行它 ===")
    await asyncio.sleep(0)
    print(f"    await sleep(0) 之后：state = {state_of(task)}")
    print("    ↑ CORO_SUSPENDED。它执行到 await asyncio.sleep(0.1) 处挂起")

    print()
    print("=== 4. 等待其完成 ===")
    result = await task
    print(f"    await task 之后：state = {state_of(task)}, result = {result!r}")
    print("    ↑ CORO_CLOSED。coroutine 已耗尽，Task 中保存着返回值")

    print()
    print("=== 5. 事件循环的实际行为：手动 send() 驱动 ===")

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
    print(f"    第一次 send(None) 后: {inspect.getcoroutinestate(manual)}  ← 在 yield 处挂起")
    print("    ↑ await asyncio.sleep(0) 即使延迟为 0，也是一次主动让出。")
    print("      事件循环的全部工作就是反复 send(None)，直到 StopIteration。")

    print()
    print("=== 6. await 是可能挂起，不是一定挂起 ===")

    async def no_suspend() -> str:
        return "无 await，不会挂起"

    async def outer() -> str:
        print("        outer: 即将 await 一个不会挂起的协程")
        value = await no_suspend()
        print(f"        outer: 取得 {value!r}，仍在同一次 send 内")
        return "outer 完成"

    probe = outer()
    try:
        probe.send(None)
    except StopIteration as stop:
        print(f"    send(None) 一次即抛 StopIteration: {stop.value!r}")
    print("    ↑ 从头执行到尾，中途没有返回过，说明这次 await 未挂起。")
    print("      只有被 await 的对象尚未就绪时，才会真正让出控制权。")


if __name__ == "__main__":
    asyncio.run(main())

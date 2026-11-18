"""Day 3 · 练习 2：调度层 —— create_task / gather / TaskGroup / as_completed

同一批任务，五种调度方式的差别集中在本文件。观察两点：
    - 结果顺序与完成顺序的差异：gather 交付前者，as_completed 交付后者
    - 单个任务失败时，其余任务继续运行还是被取消

运行：uv run day03/python/02_task.py
"""

import asyncio
import time


async def job(name: str, delay: float) -> str:
    """等待 delay 秒后返回 name。本文件各场景共用该任务。"""
    await asyncio.sleep(delay)
    return name


# ---------------------------------------------------------------------------
# 1. 串行基线：作为后续并发写法的对照
# ---------------------------------------------------------------------------


async def serial_jobs(specs: list[tuple[str, float]]) -> list[str]:
    """逐个 await，总耗时等于所有 delay 之和。

    列表推导加 await 属于串行写法：每个 await 在原地等待完成后才处理下一个，
    看上去像并发，实际没有并发。
    """
    # 空列表必须标注元素类型，mypy 才能推断 append 的目标类型。
    results: list[str] = []
    for name, delay in specs:
        result = await job(name, delay)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# 2. gather：批量排期，按参数顺序交付结果
# ---------------------------------------------------------------------------


async def with_gather(specs: list[tuple[str, float]]) -> list[str]:
    """gather 一次性排期所有协程，返回结果列表，顺序与参数顺序一致。"""
    # `*(...)` 把生成器摊开成位置参数。gather 接收的是若干协程，不是列表。
    return await asyncio.gather(*(job(n, d) for n, d in specs))


async def gather_order_proof() -> tuple[list[str], list[str]]:
    """返回 (gather 交付顺序, 实际完成顺序)。两者不一致才符合预期。"""
    # 常见错误写法及其原因：
    #
    # 1. 引用 specs —— 它是 __main__ 的局部变量，函数无法访问其他函数的局部变量。
    #    参数需要自行传入或在本函数内定义。
    #
    # 2. 用 as_completed 的产出充当 gather 的返回值。as_completed 交付的是完成顺序，
    #    而 gather 交付的是参数顺序，两者是不同的东西。
    #
    # 3. 漏写 await。with_gather 是 async def，调用它只创建 coroutine 对象，
    #    不执行函数体，后续比较得到的是 coroutine 对象本身。
    #
    # 4. 分别用 create_task 与 with_gather 各跑一遍。两遍执行的结果不对应同一次运行，
    #    完成顺序与 gather 顺序的对照因此失去意义。
    #
    # 正确做法：让每个协程在完成的时刻自行记录，只跑一遍。
    finished: list[str] = []

    async def tracked(name: str, delay: float) -> str:
        await asyncio.sleep(delay)
        # 先返回的协程先记录，这里得到的是真实完成顺序。
        finished.append(name)
        return name

    results = await asyncio.gather(
        tracked("slow", 0.06),
        tracked("fast", 0.01),
        tracked("mid", 0.03),
    )
    # gather 按传参顺序排列返回值，与完成先后无关。
    return list(results), finished


# ---------------------------------------------------------------------------
# 3. create_task：立即排期，不等待
# ---------------------------------------------------------------------------


async def with_create_task() -> list[str]:
    """用 create_task 启动两个任务，等待完成后按创建顺序返回结果。"""
    task1 = asyncio.create_task(job("a", 0.05))
    task2 = asyncio.create_task(job("b", 0.05))
    result1 = await task1
    result2 = await task2
    return [result1, result2]


# ---------------------------------------------------------------------------
# 4. TaskGroup：结构化并发，单个失败导致全体取消（3.11+）
# ---------------------------------------------------------------------------


async def with_task_group_failure_proof() -> tuple[list[str], list[str]]:
    """TaskGroup 中单个任务抛异常时，其余任务全部取消。

    返回 (正常完成的任务, 被取消的任务)。
    ★ 外层用 `except* ValueError:` 捕获 —— 结构化并发抛出的是 ExceptionGroup。
    """
    # 常见错误写法的共同根源：把 TaskGroup 当成「接收若干任务并代为运行」的函数。
    # 它是上下文管理器，这个区别构成本题的全部内容。
    #
    # 1. create_task 没有 exception 参数。让任务失败的唯一方式是协程内部抛异常，
    #    不存在「构造一个带异常的 Task」的写法（Java 的 CompletableFuture 有
    #    failedFuture()，Python 无对应物）。
    #
    # 2. 任务必须在 TaskGroup 的 async with 块内创建，块才能管理它们。
    #    在块外 create_task，TaskGroup 不知道这些任务存在。
    #
    # 3. asyncio.task_group 这个名称不存在，正确写法是 asyncio.TaskGroup()。
    #    块的边界即任务的生命周期边界：离开块时所有任务要么完成，要么被取消。
    #
    # 4. task.get_name() 返回自动生成的名字（如 "Task-3"），不是传给 job 的参数。
    #    名字需要自行记录，不依赖框架生成。

    done: list[str] = []
    cancelled: list[str] = []

    async def tracked(name: str, delay: float, fail: bool = False) -> str:
        try:
            await asyncio.sleep(delay)
            if fail:
                raise ValueError(name)
            done.append(name)
            return name
        except asyncio.CancelledError:
            # 被取消时记录，然后必须重新抛出；吞掉它会使取消失效。
            cancelled.append(name)
            raise

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(tracked("error", 0.0, fail=True))
            tg.create_task(tracked("slow1", 0.05))
            tg.create_task(tracked("slow2", 0.05))
    except* ValueError:
        # 结构化并发把所有异常打包成 ExceptionGroup，用 except* 按类型拆开。
        pass

    return done, cancelled


# ---------------------------------------------------------------------------
# 5. as_completed：按完成顺序交付
# ---------------------------------------------------------------------------


async def with_as_completed() -> list[str]:
    """返回完成顺序：slow=0.06 / mid=0.03 / fast=0.01。"""
    task1 = asyncio.create_task(job("slow", 0.06))
    task2 = asyncio.create_task(job("mid", 0.03))
    task3 = asyncio.create_task(job("fast", 0.01))

    futures = [task1, task2, task3]
    results: list[str] = []
    # as_completed 返回生成器而非 list，且必须逐个消费才能拿到结果。
    for fut in asyncio.as_completed(futures):
        result = await fut
        results.append(result)
    return results


if __name__ == "__main__":
    specs = [("a", 0.05), ("b", 0.05), ("c", 0.05), ("d", 0.05), ("e", 0.05)]

    async def scene() -> None:
        t0 = time.perf_counter()
        serial = await serial_jobs(specs)
        t_serial = time.perf_counter() - t0

        t1 = time.perf_counter()
        concurrent = await with_gather(specs)
        t_concurrent = time.perf_counter() - t1

        assert serial == ["a", "b", "c", "d", "e"]
        assert concurrent == ["a", "b", "c", "d", "e"]
        assert t_concurrent < t_serial / 3, (
            f"并发耗时应显著低于串行：串行 {t_serial:.3f}s，并发 {t_concurrent:.3f}s"
        )

        gathered, finished = await gather_order_proof()
        assert gathered == ["slow", "fast", "mid"], f"gather 按参数顺序交付: {gathered}"
        assert finished == ["fast", "mid", "slow"], f"完成顺序应与参数顺序相反: {finished}"

        assert await with_create_task() == ["a", "b"]

        done, cancelled = await with_task_group_failure_proof()
        assert done == [], f"较慢的任务应被中断，不应完成: {done}"
        assert sorted(cancelled) == ["slow1", "slow2"], f"兄弟任务应被取消: {cancelled}"

        assert await with_as_completed() == ["fast", "mid", "slow"]

        print(f"串行 {t_serial:.3f}s / 并发 {t_concurrent:.3f}s")

    asyncio.run(scene())
    print("02_task: 全部通过")

"""Day 3 · 练习 2：调度层 —— create_task / gather / TaskGroup / as_completed

同一批活儿，五种调度方式的差别就在这个文件里。重点盯两件事：
    - 结果顺序 vs 完成顺序（gather 给前者，as_completed 给后者）
    - 一个任务失败时，兄弟任务是"继续跑"还是"被取消"

跑法：uv run day03/python/02_task.py
"""

import asyncio
import time


async def job(name: str, delay: float) -> str:
    """睡 delay 秒后返回 name。本文件所有场景共用这个活儿。"""
    await asyncio.sleep(delay)
    return name


# ---------------------------------------------------------------------------
# 1. 串行基线（反面教材，但你需要它做对照）
# ---------------------------------------------------------------------------


async def serial_jobs(specs: list[tuple[str, float]]) -> list[str]:
    """一个一个 await，总耗时 = 所有 delay 之和。

    ★ 这就是"列表推导 + await"的写法：[await job(n, d) for n, d in specs]
      它看上去像并发，实际是串行 —— 每个 await 都在原地等完才做下一个。
    """
    # 你写对了。只有一处要改：空列表要标类型，mypy 才知道后面 append 什么。
    # ❌ results = []
    results: list[str] = []
    for name, delay in specs:
        result = await job(name, delay)
        results.append(result)
    return results


# ---------------------------------------------------------------------------
# 2. gather：批量排期，按【参数顺序】收结果
# ---------------------------------------------------------------------------


async def with_gather(specs: list[tuple[str, float]]) -> list[str]:
    """gather 一次性排期所有协程，返回结果列表（顺序 = 参数顺序）。"""
    # 这题完全正确。`*(...)` 是把生成器摊开成位置参数，gather 要的是若干个协程，不是列表。
    return await asyncio.gather(*(job(n, d) for n, d in specs))


async def gather_order_proof() -> tuple[list[str], list[str]]:
    """返回 (gather 给出的顺序, 实际完成顺序)。两个不一样才是对的。"""
    # ❌ 原写法有四个问题，逐个说：

    # ❌ 问题 1：specs 在这个函数里不存在。
    #    它是 __main__ 里的局部变量，函数看不到别的函数的局部变量。
    #    这正是 Day 1 的坑 7（作用域）以另一种形式出现 —— 参数要自己传或自己定义。
    #
    # ❌ finished: list[str] = []
    # ❌ tasks: list[asyncio.Task] = []
    # ❌ for n, d in specs:
    # ❌     task = asyncio.create_task(job(n, d))
    # ❌     tasks.append(task)
    #
    # ❌ 问题 2：for task in asyncio.as_completed(tasks) 拿到的是"完成顺序"，
    #    但你要的 finished 确实是完成顺序，这一步没错 —— 错在你把它当成 gather 的返回值。
    #
    # ❌ 问题 3：results = with_gather(specs)  ← 少了 await。
    #    with_gather 是 async def，调用它只创建 coroutine 对象，不会执行。
    #    results 拿到的是 <coroutine object ...>，后面 assert 一比较就炸。
    #    这就是笔记第八节列的第 2 个坑，你亲手踩了一次。
    #
    # ❌ 问题 4：就算补上 await，这里也跑了【两遍】任务（一遍 create_task，一遍 with_gather），
    #    finished 来自第一遍，results 来自第二遍，两组数据不是同一次运行的结果，对照就失去意义。
    #
    # ✅ 正确做法：让一个协程在【完成的那一刻】自己记账，然后只跑一遍。
    finished: list[str] = []

    async def tracked(name: str, delay: float) -> str:
        await asyncio.sleep(delay)
        finished.append(name)  # 谁先醒谁先 append，这就是真实完成顺序
        return name

    results = await asyncio.gather(
        tracked("slow", 0.06),
        tracked("fast", 0.01),
        tracked("mid", 0.03),
    )
    # gather 的返回值按你传参数时的顺序排，和谁先完成无关
    return list(results), finished


# ---------------------------------------------------------------------------
# 3. create_task：立刻排期，不等
# ---------------------------------------------------------------------------


async def with_create_task() -> list[str]:
    """用 create_task 起两个任务，等它们完成，返回按创建顺序的结果。"""
    # 完全正确。这题你抓到了"create_task 立刻排期，await 才是等"的本质。
    task1 = asyncio.create_task(job("a", 0.05))
    task2 = asyncio.create_task(job("b", 0.05))
    result1 = await task1
    result2 = await task2
    return [result1, result2]


# ---------------------------------------------------------------------------
# 4. TaskGroup：结构化并发，一个失败全体取消（3.11+）
# ---------------------------------------------------------------------------


async def with_task_group_failure_proof() -> tuple[list[str], list[str]]:
    """TaskGroup 里一个任务抛异常，兄弟全部被取消。

    返回 (正常完成的, 被取消的)。
    ★ 外面要用 `except* ValueError:` 接住 —— 结构化并发抛的是 ExceptionGroup。
    """
    # ❌ 原写法几乎每一行都有问题，而且问题是同一个根源：
    #    你把 TaskGroup 当成了一个"接收若干任务、替我跑"的函数。
    #    它不是函数，是【上下文管理器】。这个区别就是本题的全部内容。
    #
    # ❌ taskError = asyncio.create_task(job("error", 0.0), exception=ValueError())
    #    create_task 没有 exception 参数。Python 里让任务失败的唯一方式是
    #    【协程内部抛异常】，不存在"造一个带异常的 Task"这种写法。
    #    （Java 的 CompletableFuture 有 failedFuture()，Python 没有对应物。）
    #
    # ❌ task1 = asyncio.create_task(job("sleep1", 0.05))
    # ❌ tasks = [taskError, task1, task2]
    #    任务必须在 TaskGroup 的 async with 块【里面】创建，块才管得住它们。
    #    在块外面 create_task，TaskGroup 根本不知道它们存在。
    #
    # ❌ await asyncio.task_group(taskError, task1, task2)
    #    asyncio.task_group 这个名字不存在。正确的是 asyncio.TaskGroup()：
    #
    #        async with asyncio.TaskGroup() as tg:
    #            tg.create_task(...)
    #            tg.create_task(...)
    #
    #    块的边界 = 任务的生命周期边界。出了块，所有任务要么完成、要么被取消。
    #
    # ❌ 用 task.get_name() 判断谁被取消
    #    get_name() 返回的是自动生成的 "Task-3"，不是你传给 job 的 "sleep1"。
    #    名字要自己记，不能指望框架帮你记。
    #
    # ✅ 正确写法：

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
            # 被取消时记一笔，然后【必须重新抛】—— 吞掉它取消就失效了
            cancelled.append(name)
            raise

    try:
        async with asyncio.TaskGroup() as tg:
            tg.create_task(tracked("error", 0.0, fail=True))
            tg.create_task(tracked("slow1", 0.05))
            tg.create_task(tracked("slow2", 0.05))
    except* ValueError:
        # 结构化并发把所有异常打包成 ExceptionGroup，要用 except* 按类型拆开
        pass

    return done, cancelled


# ---------------------------------------------------------------------------
# 5. as_completed：谁先完成谁先交
# ---------------------------------------------------------------------------


async def with_as_completed() -> list[str]:
    """返回【完成顺序】：slow=0.06 / mid=0.03 / fast=0.01。"""
    # 完全正确。和 gather 的区别正是本题考点：gather 按参数顺序，as_completed 按完成顺序。
    task1 = asyncio.create_task(job("slow", 0.06))
    task2 = asyncio.create_task(job("mid", 0.03))
    task3 = asyncio.create_task(job("fast", 0.01))

    futures = [task1, task2, task3]
    results: list[str] = []
    # ❌ results = asyncio.as_completed(futures)
    #    这行有三个问题：① 上一行的空列表立刻变成死代码；② as_completed 返回的是
    #    生成器，不是 list[str]，mypy 直接报 assignment 不兼容；③ 就算类型对，
    #    不消费生成器也拿不到任何结果。
    #    "一次 await 取一个"只能靠下面的 for 循环，省不掉。
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
            f"并发应该快一个量级: 串行 {t_serial:.3f}s vs 并发 {t_concurrent:.3f}s"
        )

        gathered, finished = await gather_order_proof()
        assert gathered == ["slow", "fast", "mid"], f"gather 按参数顺序: {gathered}"
        assert finished == ["fast", "mid", "slow"], f"完成顺序应该反过来: {finished}"

        assert await with_create_task() == ["a", "b"]

        done, cancelled = await with_task_group_failure_proof()
        assert done == [], f"慢任务应该被打断，不该完成: {done}"
        assert sorted(cancelled) == ["slow1", "slow2"], f"兄弟应被取消: {cancelled}"

        assert await with_as_completed() == ["fast", "mid", "slow"]

        print(f"串行 {t_serial:.3f}s / 并发 {t_concurrent:.3f}s")

    asyncio.run(scene())
    print("02_task: 全部通过")

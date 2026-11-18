"""Day 3 · 练习 3：控制层 —— Semaphore / timeout / cancel

并发建立之后必须能够约束。本节验证三件事：
    1. Semaphore 限制并发峰值，峰值不会超过名额数
    2. asyncio.timeout 超时后取消内部协程，不会放任其继续运行
    3. 被取消的协程可以在 CancelledError 中清理，但必须重新抛出

运行：uv run day03/python/03_control.py
"""

import asyncio


async def limited(sem: asyncio.Semaphore, name: str, delay: float, tracker: dict[str, int]) -> str:
    """在 sem 限流下等待 delay 秒，返回 name。

    tracker 的维护方式：
        进入临界区时  tracker["active"] += 1
        更新并发峰值  tracker["peak"] = max(tracker["peak"], tracker["active"])
        离开临界区时  tracker["active"] -= 1

    ★ 必须使用 `async with sem:`，不要手写 acquire / release。
      sleep 要放在临界区内部，占用的名额才有意义。
    """
    # 计数递减若不放在 finally 中，sleep 抛异常或任务被取消时该行不执行，
    # 计数永久多算一次。Semaphore 自身不会泄漏（async with 保证 release），
    # 泄漏的是这个计数。生产代码中它可能代表当前数据库连接数或在途请求数。
    async with sem:
        tracker["active"] += 1
        tracker["peak"] = max(tracker["peak"], tracker["active"])
        try:
            await asyncio.sleep(delay)
        finally:
            tracker["active"] -= 1
    return name


async def with_deadline(delay: float, deadline: float, marks: list[str]) -> str | None:
    """在 deadline 秒的总时限内等待 delay 秒。

    marks 按实际发生的顺序追加：
        "started"    进入
        "cancelled"  内部协程被取消时，在 CancelledError 分支内、重新抛出之前
        "timeout"    外层捕获 TimeoutError 时
        "finished"   未超时，正常等待结束

    返回 "ok" 或 None。

    ★ 两层嵌套：
          try:
              async with asyncio.timeout(deadline):
                  try:
                      await asyncio.sleep(delay)
                  except asyncio.CancelledError:
                      ...        # 追加 "cancelled" 后必须 raise
          except TimeoutError:
              ...            # 追加 "timeout"，返回 None
    ★ 顺序是关键：CancelledError 分支先记录再抛出，asyncio.timeout 将其转换为
      TimeoutError，由外层捕获。
    """
    try:
        async with asyncio.timeout(deadline):
            marks.append("started")
            try:
                await asyncio.sleep(delay)
                marks.append("finished")
            except asyncio.CancelledError:
                marks.append("cancelled")
                raise
    except TimeoutError:
        marks.append("timeout")
        return None
    return "ok"


async def main() -> None:
    # --- Semaphore：10 个任务，名额 3 ---
    sem = asyncio.Semaphore(3)
    tracker = {"active": 0, "peak": 0}
    names = await asyncio.gather(*(limited(sem, f"t{i}", 0.02, tracker) for i in range(10)))
    assert names == [f"t{i}" for i in range(10)], f"gather 保持参数顺序: {names}"
    assert tracker["peak"] == 3, f"并发峰值应等于名额数: {tracker['peak']}"
    assert tracker["active"] == 0, f"执行结束后名额应全部归还: {tracker['active']}"

    # --- timeout：实际超时 ---
    marks: list[str] = []
    result = await with_deadline(delay=0.5, deadline=0.05, marks=marks)
    assert result is None, "超时应返回 None"
    assert marks == ["started", "cancelled", "timeout"], f"marks 不符: {marks}"

    # --- timeout：未超时的路径 ---
    ok_marks: list[str] = []
    assert await with_deadline(delay=0.01, deadline=0.5, marks=ok_marks) == "ok"
    assert ok_marks == ["started", "finished"], f"正常路径不应记录 cancelled: {ok_marks}"

    # --- cancel：协作式取消 ---
    reached = []

    async def victim() -> None:
        try:
            await asyncio.sleep(10)
        except asyncio.CancelledError:
            reached.append("cleanup")
            raise

    task = asyncio.create_task(victim())
    await asyncio.sleep(0.01)
    task.cancel()
    try:
        await task
    except asyncio.CancelledError:
        reached.append("propagated")
    assert reached == ["cleanup", "propagated"], f"取消链路不符: {reached}"

    # --- CancelledError 不继承 Exception ---
    assert not issubclass(asyncio.CancelledError, Exception), "3.8+ 起它继承 BaseException"
    assert issubclass(asyncio.CancelledError, BaseException)


if __name__ == "__main__":
    asyncio.run(main())
    print("03_control: 全部通过")

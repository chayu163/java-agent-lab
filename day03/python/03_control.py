"""Day 3 · 练习 3：控制层 —— Semaphore / timeout / cancel

并发有了就必须能收住。这一节钉三件事：
    1. Semaphore 是"名额闸门"，峰值并发不会超过名额数
    2. asyncio.timeout 超时后会【取消】里面的协程，不是扔下不管
    3. 被取消的协程可以在 CancelledError 里做清理，但必须重新抛

跑法：uv run day03/python/03_control.py
"""

import asyncio


async def limited(sem: asyncio.Semaphore, name: str, delay: float, tracker: dict[str, int]) -> str:
    """在 sem 限流下睡 delay 秒，返回 name。

    tracker 的用法：
        进入临界区时   tracker["active"] += 1
        顺手更新峰值   tracker["peak"] = max(tracker["peak"], tracker["active"])
        离开临界区时   tracker["active"] -= 1

    ★ 必须用 `async with sem:`，不要手写 acquire / release。
      Semaphore 管的是"进入临界区"，sleep 要放在临界区【里面】才算数。
    """
    # ✅ 主体正确。但你写的是：
    # ❌     async with sem:
    # ❌         tracker["active"] += 1
    # ❌         await asyncio.sleep(delay)
    # ❌         tracker["active"] -= 1
    #    问题：sleep 抛异常 / 任务被取消时，最后那行永远不会执行，计数永久 +1。
    #    当前断言只测了"全部正常完成"这一条路径，所以没暴露。
    #    实测：取消其中一个任务后 tracker["active"] 残留 1，不是 0。
    #
    #    Semaphore 本身不会泄漏（async with 保证 release），但【你自己的计数】会。
    #    真实项目里这个计数可能是"当前数据库连接数""当前在途请求数"，泄漏就是真故障。
    #
    #    ✅ 规则：进出成对的操作，出那一半必须放 finally。
    async with sem:
        tracker["active"] += 1
        tracker["peak"] = max(tracker["peak"], tracker["active"])
        try:
            await asyncio.sleep(delay)
        finally:
            tracker["active"] -= 1
    return name


async def with_deadline(delay: float, deadline: float, marks: list[str]) -> str | None:
    """在 deadline 秒的总时限内睡 delay 秒。

    marks 按实际发生顺序追加：
        "started"    进入
        "cancelled"  内部协程被取消时（在 CancelledError 分支里，抛之前）
        "timeout"    外层捕获 TimeoutError 时
        "finished"   没超时，正常睡完

    返回 "ok" 或 None。

    ★ 结构是两层相嵌：
          try:
              async with asyncio.timeout(deadline):
                  try:
                      await asyncio.sleep(delay)
                  except asyncio.CancelledError:
                      ...        # 追加 "cancelled" 后必须 raise
          except TimeoutError:
              ...            # 追加 "timeout"，返回 None
    ★ 这里顺序很关键：CancelledError 分支先记一笔，再抛；
      抛出去之后 asyncio.timeout 把它转成 TimeoutError，外层接住。
    """
    # raise NotImplementedError("TODO: 按上面的两层结构写")
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
    assert names == [f"t{i}" for i in range(10)], f"gather 保序: {names}"
    assert tracker["peak"] == 3, f"峰值并发应该正好等于名额: {tracker['peak']}"
    assert tracker["active"] == 0, f"跑完名额应该全还回去: {tracker['active']}"

    # --- timeout：真的超时 ---
    marks: list[str] = []
    result = await with_deadline(delay=0.5, deadline=0.05, marks=marks)
    assert result is None, "超时应返回 None"
    assert marks == ["started", "cancelled", "timeout"], f"marks 不对: {marks}"

    # --- timeout：没超时，不应误伤 ---
    ok_marks: list[str] = []
    assert await with_deadline(delay=0.01, deadline=0.5, marks=ok_marks) == "ok"
    assert ok_marks == ["started", "finished"], f"正常路径不该记 cancelled: {ok_marks}"

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
    assert reached == ["cleanup", "propagated"], f"取消链路不对: {reached}"

    # --- CancelledError 不是 Exception ---
    assert not issubclass(asyncio.CancelledError, Exception), "3.8+ 它继承 BaseException"
    assert issubclass(asyncio.CancelledError, BaseException)


if __name__ == "__main__":
    asyncio.run(main())
    print("03_control: 全部通过")

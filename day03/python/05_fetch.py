"""Day 3 产出：asyncio + httpx 并发调 5 个 API（带超时和并发上限）。

计划原文的今日产出就是这个文件。它把前四个练习拼成一个能用的东西：
    Semaphore   -> 限并发
    timeout     -> 单个请求的时限，超时只影响自己
    AsyncClient -> 连接池复用
    gather      -> 保序收结果

两种跑法：
    uv run day03/python/05_fetch.py            # 本地 Mock，不联网，用来验证断言
    uv run day03/python/05_fetch.py --real     # 真打公共 API
"""

import asyncio
import sys
import time
from typing import Any

import httpx

MOCK_URLS = [
    "https://mock.local/fast",
    "https://mock.local/mid",
    "https://mock.local/slow",
    "https://mock.local/broken",
    "https://mock.local/normal",
]

REAL_URLS = [
    "https://httpbin.org/json",
    "https://httpbin.org/uuid",
    "https://httpbin.org/delay/1",
    "https://httpbingo.org/status/500",
    "https://httpbin.org/headers",
]

# 每次请求在这些 URL 上分别要睡多久（秒）。slow 会超过默认 timeout。
MOCK_DELAYS = {
    "https://mock.local/fast": 0.02,
    "https://mock.local/mid": 0.08,
    "https://mock.local/slow": 1.5,
    "https://mock.local/broken": 0.01,
    "https://mock.local/normal": 0.05,
}


# ---------------------------------------------------------------------------
# 单个请求
# ---------------------------------------------------------------------------


async def fetch_one(
    client: httpx.AsyncClient,
    url: str,
    sem: asyncio.Semaphore,
    timeout: float,
    tracker: dict[str, Any],
) -> dict[str, Any]:
    """抓一个 URL，永不抛异常——所有失败都变成返回值。

    返回字段：url / ok / status / elapsed_ms / error

    tracker 维护并发峰值（和练习 3 一样）：
        进临界区 active += 1，更新 peak，出临界区 active -= 1

    ★ 三层嵌套，每层解决一个问题：
          async with sem:                     # 1. 排队拿名额
              try:
                  async with asyncio.timeout(timeout):   # 2. 总时限
                      resp = await client.get(url)       # 3. 真请求
              except TimeoutError: ...
              except httpx.HTTPError: ...

    ★ 为什么 except 里不捕获 CancelledError：
      任务被外层取消时应该让取消传播出去，不能吞。
      只抓 TimeoutError（它是 Exception 的子类）和 httpx.HTTPError。
    ★ 为什么返回 dict 而不是抛异常：
      5 个请求里有 1 个超时，不该让整批失败。
      Agent 里"一个工具挂了"也是这个处理方式——回填错误信息给模型，继续跑。

    ❌ 你原来的实现有四处问题：
      1. tracker["active"] += 1 之后【没有任何地方减回去】，峰值会一路涨到 5，
         等于 tracker 失效。出临界区必须放在 finally 里（和练习 3 同一个坑）。
      2. start_time 记在 timeout 块【里面】、且在 await 之前——超时那条路径
         没有 elapsed_ms，返回 None，后面 f"{...:>7.1f}" 格式化直接 TypeError。
         计时必须放在 timeout 外面，覆盖包括超时在内的全部路径。
      3. 三条 return path 各自手写一遍 dict，字段一多就容易漏。
      4. 500 那种"服务端返回了但状态不对"和"根本没连上"被混在一起，
         调用方没法区分。
    ✅ 正确结构见下。
    """
    async with sem:
        tracker["active"] += 1
        tracker["peak"] = max(tracker["peak"], tracker["active"])
        started = time.perf_counter()
        try:
            async with asyncio.timeout(timeout):
                resp = await client.get(url)
        except TimeoutError:
            return {
                "url": url,
                "ok": False,
                "status": None,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
                "error": "timeout",
            }
        except httpx.HTTPError as exc:
            # 只抓 httpx 自己的异常；CancelledError 是 BaseException，抓不到也不能抓
            return {
                "url": url,
                "ok": False,
                "status": None,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
                "error": f"http_error: {type(exc).__name__}",
            }
        finally:
            # 无论成功、超时、断网、被取消，名额计数都要还回去
            tracker["active"] -= 1

        elapsed_ms = (time.perf_counter() - started) * 1000
        ok = resp.status_code == 200
        return {
            "url": url,
            "ok": ok,
            "status": resp.status_code,
            "elapsed_ms": elapsed_ms,
            "error": None if ok else f"http_{resp.status_code}",
        }


# ---------------------------------------------------------------------------
# 批量请求
# ---------------------------------------------------------------------------


async def fetch_all(
    urls: list[str],
    *,
    max_concurrency: int = 3,
    timeout: float = 0.5,
    transport: httpx.AsyncBaseTransport | None = None,
) -> list[dict[str, Any]]:
    """并发抓全部 URL，返回结果列表（顺序 = urls 顺序）。

    ★ AsyncClient 必须只建一个：它的连接池是复用的关键。
      每个请求新建 client 会让连接池白建，性能比同步还差。
    ★ gather 保序：结果列表和 urls 一一对应，即使 slow 最后才完成。
    ★ 需要自己建 sem（Semaphore(max_concurrency)）和一个 tracker 字典
      （{"active": 0, "peak": 0}），传给每个 fetch_one。

    ❌ 你原来的实现：最核心的一步漏了——根本没有调用 fetch_one。
      1. `results = await asyncio.gather(*(client.get(url) for url in urls))`
         拿到的是 list[httpx.Response]，不是 list[dict]。于是
         ① 返回类型对不上（mypy 直接报）；② Semaphore 建了没用（ruff F841）；
         ③ tracker 没传给任何人；④ 超时 / 500 的归一化逻辑全被绕过。
     2. `client = httpx.AsyncClient(...)` 没有 `async with`，也没有 aclose()，
         连接池永远不关。它是资源，必须进 async with。
     3. `async with asyncio.timeout(timeout * len(urls))` 是"整批总时限"，
         这个想法本身不算错，但和 fetch_one 里"单请求时限"是两层，容易互相
         干扰：slow 那个 1.5s 的请求把总预算 1.5s 吃满，整批直接 TimeoutError。
         今天只练单请求超时，总时限可以不加。
     4. `except ...: raise` / `raise e` 两个分支都是空转 —— 什么都不做还重抛，
         不如不写。`raise e` 还会丢掉原始 traceback，要重抛就用裸 `raise`。
    """
    sem = asyncio.Semaphore(max_concurrency)
    tracker: dict[str, Any] = {"active": 0, "peak": 0}
    async with httpx.AsyncClient(transport=transport) as client:
        return await asyncio.gather(
            *(fetch_one(client, url, sem, timeout, tracker) for url in urls)
        )


# ---------------------------------------------------------------------------
# Mock transport：不联网也能验证全部逻辑
# ---------------------------------------------------------------------------


def make_mock_transport() -> httpx.MockTransport:
    """按 MOCK_DELAYS 返回延迟和状态的假 transport。"""

    async def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        await asyncio.sleep(MOCK_DELAYS.get(url, 0.01))
        if url.endswith("/broken"):
            return httpx.Response(500, json={"error": "boom"})
        return httpx.Response(200, json={"url": url})

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# 验收
# ---------------------------------------------------------------------------


async def offline_check() -> None:
    t0 = time.perf_counter()
    results = await fetch_all(
        MOCK_URLS, max_concurrency=2, timeout=0.3, transport=make_mock_transport()
    )
    elapsed = time.perf_counter() - t0

    assert len(results) == 5, f"5 个 URL 应该都回来: {len(results)}"
    assert [r["url"] for r in results] == MOCK_URLS, "gather 必须保序"

    by_url = {r["url"]: r for r in results}

    assert by_url["https://mock.local/fast"]["ok"] is True, "fast 应该成功"
    assert by_url["https://mock.local/fast"]["status"] == 200

    assert by_url["https://mock.local/slow"]["ok"] is False, "slow 超过了 timeout"
    assert by_url["https://mock.local/slow"]["error"] == "timeout", (
        f"超时的 error 应该是 'timeout': {by_url['https://mock.local/slow']}"
    )

    assert by_url["https://mock.local/broken"]["ok"] is False, "500 不该算成功"
    assert by_url["https://mock.local/broken"]["status"] == 500
    assert by_url["https://mock.local/broken"]["error"] == "http_500"

    # 5 个里：slow 超时、broken 返回 500，只有 fast / mid / normal 成功
    ok_count = sum(1 for r in results if r["ok"])
    assert ok_count == 3, f"应该 3 个成功: {ok_count}"

    # 串行下界 = sum(delays)；并发应该明显更快
    serial_lower_bound = sum(MOCK_DELAYS.values())
    assert elapsed < serial_lower_bound, (
        f"并发 {elapsed:.2f}s 应该快于串行下界 {serial_lower_bound:.2f}s"
    )

    print(f"offline: 5 个请求 / 并发上限 2 / 总耗时 {elapsed:.2f}s")
    print(f"         串行下界 {serial_lower_bound:.2f}s")
    for r in results:
        mark = "ok " if r["ok"] else "err"
        print(
            f"  [{mark}] {r['url']:<30} {r['status']} {r['elapsed_ms']:>7.1f}ms {r['error'] or ''}"
        )


async def online_check() -> None:
    results = await fetch_all(REAL_URLS, max_concurrency=3, timeout=10.0)
    ok_count = sum(1 for r in results if r["ok"])
    print(f"online: {ok_count}/{len(results)} 成功")
    for r in results:
        mark = "ok " if r["ok"] else "err"
        print(
            f"  [{mark}] {r['url']:<32} {r['status']} {r['elapsed_ms']:>7.1f}ms {r['error'] or ''}"
        )


if __name__ == "__main__":
    real = "--real" in sys.argv[1:]
    asyncio.run(online_check() if real else offline_check())
    print("05_fetch: 全部通过")

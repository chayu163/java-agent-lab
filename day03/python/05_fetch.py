"""Day 3 产出：asyncio + httpx 并发调用 5 个 API，带超时与并发上限。

计划原文指定的当日产出。它把前四个练习组合成一个可用的组件：
    Semaphore    限制并发数
    timeout      单个请求的时限，超时只影响该请求
    AsyncClient  复用连接池
    gather       按参数顺序收集结果

两种运行方式：
    uv run day03/python/05_fetch.py            本地 Mock，不联网，用于验证断言
    uv run day03/python/05_fetch.py --real     实际请求公共 API
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

# 各 URL 在 Mock 下的响应延迟，单位为秒。slow 的延迟超过默认 timeout。
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
    """抓取单个 URL，不抛异常，所有失败都作为返回值。

    返回字段：url / ok / status / elapsed_ms / error

    tracker 维护并发峰值：
        进入临界区 active += 1，更新 peak，离开临界区 active -= 1

    ★ 三层嵌套，每层解决一个问题：
          async with sem:                            排队获取名额
              try:
                  async with asyncio.timeout(timeout):   设置总时限
                      resp = await client.get(url)       发起请求
              except TimeoutError: ...
              except httpx.HTTPError: ...

    ★ 不捕获 CancelledError：任务被外层取消时，取消必须继续传播。
      只捕获 TimeoutError（Exception 的子类）与 httpx.HTTPError。
    ★ 返回 dict 而非抛异常：5 个请求中有 1 个超时，不应使整批失败。
      Agent 中单个工具失败时同样如此处理 —— 把错误信息回填给模型，继续执行。

    ❌ 常见错误一：tracker["active"] += 1 之后没有任何地方减回去，峰值会一路增长，
       使 tracker 失效。递减操作必须放在 finally 中（与练习 3 同一问题）。
    ❌ 常见错误二：started 记录在 timeout 块内部、且在 await 之前，
       超时路径没有 elapsed_ms，返回 None，后续按浮点格式化时抛 TypeError。
       计时必须放在 timeout 之外，覆盖包括超时在内的全部路径。
    ❌ 常见错误三：三条返回路径各自手写一遍 dict，字段增多时容易遗漏。
    ❌ 常见错误四：把「服务端返回了但状态码不对」与「连接未建立」混为一类，
       调用方无法区分。
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
            # 只捕获 httpx 自身的异常；CancelledError 属于 BaseException，捕获不到。
            return {
                "url": url,
                "ok": False,
                "status": None,
                "elapsed_ms": (time.perf_counter() - started) * 1000,
                "error": f"http_error: {type(exc).__name__}",
            }
        finally:
            # 无论成功、超时、断网还是被取消，名额计数都必须归还。
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
    """并发抓取全部 URL，返回结果列表，顺序与 urls 一致。

    ★ AsyncClient 只建一个：连接池复用依赖这一点。
      每个请求新建 client 会使连接池失效，性能低于同步实现。
    ★ gather 保持顺序：结果列表与 urls 一一对应，即使最慢的请求最后完成。
    ★ sem 与 tracker 在此构造：Semaphore(max_concurrency) 与
      {"active": 0, "peak": 0}，传递给每个 fetch_one。

    ❌ 常见错误：直接 gather(client.get(url) for url in urls)，没有调用 fetch_one。
       这会导致：① 返回类型是 list[httpx.Response] 而非 list[dict]，mypy 报错；
       ② Semaphore 构造后未使用；③ tracker 未传给任何调用；
       ④ 超时与状态码的归一化逻辑全部被绕过。
    ❌ 常见错误：client 没有用 async with 管理，也没有调用 aclose()，
       连接池不会关闭。
    ❌ 常见错误：用 asyncio.timeout(timeout * len(urls)) 包裹整批请求。
       这是「整批总时限」，与 fetch_one 内的「单请求时限」构成两层超时，容易互相干扰：
       单个慢请求会耗尽总预算，使整批抛 TimeoutError。今日只练习单请求超时。
    ❌ 常见错误：except 分支中只写 raise，或写 raise e。前者什么也不做，
       不如不写；后者会丢失原始 traceback，需要重抛时应使用裸 raise。
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
    """按 MOCK_DELAYS 返回延迟与状态码的假 transport。"""

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

    assert len(results) == 5, f"5 个 URL 应全部返回: {len(results)}"
    assert [r["url"] for r in results] == MOCK_URLS, "gather 必须保持顺序"

    by_url = {r["url"]: r for r in results}

    assert by_url["https://mock.local/fast"]["ok"] is True, "fast 应成功"
    assert by_url["https://mock.local/fast"]["status"] == 200

    assert by_url["https://mock.local/slow"]["ok"] is False, "slow 超过 timeout"
    assert by_url["https://mock.local/slow"]["error"] == "timeout", (
        f"超时请求的 error 应为 'timeout': {by_url['https://mock.local/slow']}"
    )

    assert by_url["https://mock.local/broken"]["ok"] is False, "500 不应计为成功"
    assert by_url["https://mock.local/broken"]["status"] == 500
    assert by_url["https://mock.local/broken"]["error"] == "http_500"

    # 5 个请求中 slow 超时、broken 返回 500，成功的是 fast、mid、normal。
    ok_count = sum(1 for r in results if r["ok"])
    assert ok_count == 3, f"应有 3 个成功: {ok_count}"

    # 串行下界为各延迟之和；并发耗时应当明显低于该值。
    serial_lower_bound = sum(MOCK_DELAYS.values())
    assert elapsed < serial_lower_bound, (
        f"并发耗时 {elapsed:.2f}s 应低于串行下界 {serial_lower_bound:.2f}s"
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

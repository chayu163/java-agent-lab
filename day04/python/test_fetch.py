"""Day 4 产出：为 Day 3 的 05_fetch.py 编写 5 个测试。

3 个成功路径加 2 个错误路径，覆盖 Day 3 版本中的四类缺陷：
    1. gather 误用、顺序错乱、返回类型不符
    2. 单个请求失败导致整批失败
    3. 计时写在 timeout 内部，超时路径的 elapsed_ms 为 None
    4. 非 200 计入成功；连接错误直接抛给调用方

运行：uv run pytest day04/python/test_fetch.py -v

文件名使用 test_fetch.py 而非 04_xxx：pytest 只收集 test_*.py 与 *_test.py，
该文件为当日产出，采用标准命名便于单独运行。
"""

import asyncio
import importlib.util
import sys
from pathlib import Path
from types import ModuleType

import httpx
import pytest

# 05_fetch.py 以数字开头，不能直接 import，需要按路径加载
_SRC = Path(__file__).resolve().parents[2] / "day03" / "python" / "05_fetch.py"


def _load(name: str, path: Path) -> ModuleType:
    spec = importlib.util.spec_from_file_location(name, path)
    assert spec is not None and spec.loader is not None
    module = importlib.util.module_from_spec(spec)
    sys.modules[name] = module
    spec.loader.exec_module(module)
    return module


fetch = _load("day03_fetch", _SRC)

URLS = [f"https://t.local/{i}" for i in range(5)]


def transport_with(
    delays: dict[str, float],
    statuses: dict[str, int] | None = None,
) -> httpx.MockTransport:
    statuses = statuses or {}

    async def handler(request: httpx.Request) -> httpx.Response:
        url = str(request.url)
        """按 URL 决定响应延迟与状态码。未登记的 URL 立即返回 200。"""
        await asyncio.sleep(delays.get(url, 0.0))
        return httpx.Response(statuses.get(url, 200), json={"url": url})

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# fixture：测试所需的替身均由 fixture 提供，测试函数只负责断言
# ---------------------------------------------------------------------------


@pytest.fixture
def all_ok() -> httpx.MockTransport:
    """5 个 URL 均在 10ms 内返回 200。"""
    return transport_with({url: 0.01 for url in URLS})


@pytest.fixture
def one_slow() -> httpx.MockTransport:
    """仅 URLS[2] 延迟 1 秒，用于验证单个超时不影响整批。"""
    return transport_with({URLS[2]: 1.0})


@pytest.fixture
def first_slow() -> httpx.MockTransport:
    """仅 URLS[0] 延迟，用于检查超时路径记录的 elapsed_ms。"""
    return transport_with({URLS[0]: 1.0})


@pytest.fixture
def one_500() -> httpx.MockTransport:
    """URLS[1] 返回 500。"""
    return transport_with({}, {URLS[1]: 500})


@pytest.fixture
def conn_refused() -> httpx.MockTransport:
    """URLS[0] 连接失败，抛 httpx.ConnectError；其余正常。"""

    async def handler(request: httpx.Request) -> httpx.Response:
        if str(request.url) == URLS[0]:
            raise httpx.ConnectError("refused")
        return httpx.Response(200, json={})

    return httpx.MockTransport(handler)


# ---------------------------------------------------------------------------
# 成功路径
# ---------------------------------------------------------------------------


async def test_all_succeed_and_keep_order(all_ok: httpx.MockTransport) -> None:
    """5 个 URL 全部成功：结果数量、顺序与字段均需正确。

    断言清单：
        len(results) == 5
        [r["url"] for r in results] == URLS          gather 保持顺序
        all(r["ok"] for r in results)
        all(r["status"] == 200 for r in results)
        all(r["error"] is None for r in results)
    """
    results = await fetch.fetch_all(URLS, transport=all_ok)
    assert len(results) == 5
    assert [r["url"] for r in results] == URLS
    assert all(r["ok"] for r in results)
    assert all(r["status"] == 200 for r in results)
    assert all(r["error"] is None for r in results)


async def test_one_failure_does_not_sink_the_batch(one_slow: httpx.MockTransport) -> None:
    """URLS[2] 超时，其余 4 个照常成功。

    断言清单：
        len(results) == 5                   失败项同样出现在结果中
        results[2]["ok"] is False
        results[2]["error"] == "timeout"
        sum(r["ok"] for r in results) == 4

    timeout 传 0.1，使延迟 1 秒的请求必然超时。
    """
    # ❌ results = fetch.fetch_all(URLS, timeout=0.1, transport=one_slow)
    #    漏写 await：fetch_all 是 async def，不加 await 只是造了个协程对象，
    #    函数体一行都没执行。下面 len(results) 会直接 TypeError。
    # ✅ 加 await
    results = await fetch.fetch_all(URLS, timeout=0.1, transport=one_slow)
    assert len(results) == 5
    assert results[2]["ok"] is False
    assert results[2]["error"] == "timeout"
    assert sum(r["ok"] for r in results) == 4


async def test_timeout_path_records_elapsed(first_slow: httpx.MockTransport) -> None:
    """超时项的 elapsed_ms 必须是数值，且接近 timeout，不能为 None。

    对应 Day 3 的缺陷：started 记录在 timeout 块内部，超时路径未赋值而返回 None，
    后续按浮点格式化时抛 TypeError。

    断言清单：
        isinstance(results[0]["elapsed_ms"], float)
        100 <= results[0]["elapsed_ms"] <= 400      timeout=0.1，留出余量
    """
    results = await fetch.fetch_all(URLS, timeout=0.1, transport=first_slow)
    assert isinstance(results[0]["elapsed_ms"], float)
    assert 100 <= results[0]["elapsed_ms"] <= 400


# ---------------------------------------------------------------------------
# 错误路径
# ---------------------------------------------------------------------------


async def test_http_500_is_normalized(one_500: httpx.MockTransport) -> None:
    """500 不计为成功，且能区分出是 HTTP 层的错误。

    断言清单：
        results[1]["ok"] is False
        results[1]["status"] == 500
        results[1]["error"] == "http_500"
    """
    # raise NotImplementedError("TODO: 让 URLS[1] 返回 500，按上述三条断言")
    results = await fetch.fetch_all(URLS, timeout=0.1, transport=one_500)
    assert results[1]["ok"] is False
    assert results[1]["status"] == 500
    assert results[1]["error"] == "http_500"


async def test_connection_error_is_swallowed(conn_refused: httpx.MockTransport) -> None:
    """连接失败必须被归一化，不得抛给调用方。

    断言清单：
        results[0]["ok"] is False
        results[0]["status"] is None
        results[0]["error"].startswith("http_error:")
        sum(r["ok"] for r in results) == 4          其余 4 个不受影响

    若 Day 3 的 fetch_one 未捕获 httpx.HTTPError，此处会抛出 httpx.ConnectError，
    测试表现为 error 而非 failed，这一差异本身就是有效信号。
    """
    # raise NotImplementedError("TODO: 用 conn_refused 调用 fetch_all")
    results = await fetch.fetch_all(URLS, timeout=0.1, transport=conn_refused)
    assert results[0]["ok"] is False
    assert results[0]["status"] is None
    assert results[0]["error"].startswith("http_error:")
    assert sum(r["ok"] for r in results) == 4

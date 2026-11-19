"""Day 2 · 练习 3：上下文管理器。

同一功能写两遍：手写 __enter__ / __exit__，再用 contextlib.contextmanager 改写。
完成后对照两者，说明各自适用的场景。

验收：uv run phase1/day02/python/context.py
"""

import time
from collections.abc import Iterator
from contextlib import contextmanager
from types import TracebackType
from typing import Self


class Timer:
    """手写版：__enter__ 记录开始时间，__exit__ 计算耗时并打印。"""

    def __init__(self, label: str = "") -> None:
        self.label = label
        self.elapsed = 0.0

    def __enter__(self) -> Self:
        self.start_time = time.perf_counter()
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> None:
        self.elapsed = time.perf_counter() - self.start_time
        print(f"{self.label} 耗时: {self.elapsed:.6f} 秒")


class Suppress:
    """吞掉指定类型的异常。"""

    def __init__(self, *exc_types: type[BaseException]) -> None:
        self.exc_types = exc_types

    def __enter__(self) -> Self:
        return self

    def __exit__(
        self,
        exc_type: type[BaseException] | None,
        exc: BaseException | None,
        tb: TracebackType | None,
    ) -> bool:
        if exc_type is None:
            return False
        return issubclass(exc_type, self.exc_types)


@contextmanager
def timed(label: str) -> Iterator[None]:
    """contextlib 版：yield 之前对应 __enter__，之后对应 __exit__。

    中间部分要用 try/finally 包住，否则 with 块内抛异常时收尾代码不执行。
    """
    start_time = time.perf_counter()
    try:
        yield
    finally:
        elapsed = time.perf_counter() - start_time
        print(f"{label} 耗时: {elapsed:.6f} 秒")


if __name__ == "__main__":
    with Timer("手写版"):
        time.sleep(0.05)
    assert Timer("").elapsed == 0.0

    with timed("contextmanager 版"):
        time.sleep(0.05)

    with Suppress(ValueError):
        raise ValueError("被 Suppress 吞掉，不应向上冒泡")

    try:
        with Timer("不吞异常"):
            raise RuntimeError("应继续向上传播")
    except RuntimeError as exc:
        print("expected:", exc)
    else:
        raise AssertionError("Timer 不应吞异常")

    print("context: 全部通过")

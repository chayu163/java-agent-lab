"""Day 2 · 练习 1：装饰器。

要求
1. timer：打印被包装函数的调用耗时，返回值原样透传。
2. retry(times, delay, exceptions)：带参数的装饰器。失败且异常类型在 exceptions 里
   就重试，总共尝试 times 次；全部失败时抛出【最后一次的原生异常】，不要包装。
3. 两个装饰器都用 functools.wraps 保留原函数的 __name__ / __doc__。

验收：uv run day02/python/decorators.py，全部断言通过。
现在跑会抛 NotImplementedError —— 那就是给你填的地方。
"""

import functools
import time
from collections.abc import Callable
from typing import Any


def timer(func: Callable[..., Any]) -> Callable[..., Any]:
    """打印 func 每次调用的耗时。"""

    @functools.wraps(func)
    def wrapper(*args: Any, **kwargs: Any) -> Any:
        # raise NotImplementedError("TODO: 记开始时间 -> 调用 func -> 打印耗时 -> 返回结果")
        start = time.perf_counter()
        result = func(*args, **kwargs)
        end = time.perf_counter()
        print(f"{func.__name__} 调用耗时: {end - start:.6f} 秒")
        return result

    return wrapper


def retry(
    times: int = 3,
    delay: float = 0.1,
    exceptions: tuple[type[BaseException], ...] = (Exception,),
) -> Callable[[Callable[..., Any]], Callable[..., Any]]:
    """带参数的装饰器：总共尝试 times 次，每次失败后等 delay 秒。

    注意这是【三层】函数：retry(...) 先返回 decorator，decorator 再包住 func。
    """
    if times < 1:
        raise ValueError("times 必须 >= 1")

    def decorator(func: Callable[..., Any]) -> Callable[..., Any]:
        @functools.wraps(func)
        def wrapper(*args: Any, **kwargs: Any) -> Any:
            # raise NotImplementedError("TODO: 循环 times 次，全部失败时抛最后一次的原始异常")
            for attempt in range(times):
                try:
                    return func(*args, **kwargs)
                except exceptions as e:
                    if attempt < times - 1:
                        time.sleep(delay)
                    else:
                        raise e

        return wrapper

    return decorator


if __name__ == "__main__":
    calls: list[int] = []

    @retry(times=3, delay=0.01)
    def flaky() -> str:
        calls.append(1)
        if len(calls) < 3:
            raise ValueError(f"第 {len(calls)} 次失败")
        return "ok"

    assert flaky() == "ok"
    assert len(calls) == 3, "应该正好尝试 3 次"

    calls.clear()

    @retry(times=2, delay=0.01)
    def always_fail() -> None:
        calls.append(1)
        raise ValueError("总是失败")

    try:
        always_fail()
    except ValueError as exc:
        assert str(exc) == "总是失败", "应该抛最后一次的原生异常，不是包装后的"
        assert len(calls) == 2
    else:
        raise AssertionError("应该抛异常")

    @timer
    def slow() -> int:
        time.sleep(0.05)
        return 42

    assert slow() == 42
    assert slow.__name__ == "slow", "没写 functools.wraps 的话这里会变成 wrapper"

    # 想一想：把 @timer 放在 @retry 里面 vs 外面，timer 各会打印几次？
    # 自己加 print 验证，答案写进今晚的笔记。

    print("decorators: 全部通过")

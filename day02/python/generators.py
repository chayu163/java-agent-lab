"""Day 2 · 练习 3：生成器。

这题的重点是「语义先定、代码后写」——overlap 的边界最容易含糊，
先把下面 docstring 里的四条读一遍，确认这就是你想要的行为，再动手。

验收：uv run day02/python/generators.py
"""

from collections.abc import Iterator
from itertools import islice
from typing import TypeVar

T = TypeVar("T")


def iter_chunks(text: str, size: int, overlap: int = 0) -> Iterator[str]:
    """按窗口切分文本。

    语义：
    - size 是每块的最大字符数，必须 > 0
    - overlap 是相邻两块的重复字符数，必须满足 0 <= overlap < size
    - 最后一块可以不足 size
    - 参数非法时抛 ValueError
      （注意生成器是惰性的：异常在第一次 next() 时才抛，不是调用 iter_chunks 时）
    """
    # raise NotImplementedError("TODO: while 循环 + yield")
    if size <= 0:
        raise ValueError("size 必须 > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap 必须满足 0 <= overlap < size")

    i = 0
    while i < len(text):
        chunk = text[i : i + size]
        yield chunk
        i += size - overlap
    # return text[i:len(text)]


def take(n: int, it: Iterator[T]) -> list[T]:
    """取前 n 个元素。用 itertools.islice，不要写 list(it)[:n]。"""
    # raise NotImplementedError("TODO: itertools.islice(it, n)")

    return list(islice(it, n))


if __name__ == "__main__":
    print(iter_chunks("abcdefg", 3))
    assert list(iter_chunks("abcdefg", 3)) == ["abc", "def", "g"]
    assert list(iter_chunks("abcdefg", 3, overlap=1)) == ["abc", "cde", "efg", "g"]

    g = iter_chunks("abcdefg", 3)
    assert next(g) == "abc", "第一次 next 才真正开始执行"
    assert take(1, g) == ["def"]
    assert list(g) == ["g"], "生成器是一次性的，前面消费掉的不会再来"

    for bad in (0, -1):
        try:
            list(iter_chunks("abc", bad))
        except ValueError:
            pass
        else:
            raise AssertionError(f"size={bad} 应该抛 ValueError")

    print("generators: 全部通过")

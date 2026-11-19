"""Day 2 · 练习 3：生成器。

重点是先确定语义、再写实现：overlap 的边界最容易含糊。
先读完 iter_chunks 的 docstring 中的四条规则，确认行为无误后再动手。

验收：uv run phase1/day02/python/generators.py
"""

from collections.abc import Iterator
from itertools import islice
from typing import TypeVar

T = TypeVar("T")


def iter_chunks(text: str, size: int, overlap: int = 0) -> Iterator[str]:
    """按窗口切分文本。

    语义：
    - size 是每块的最大字符数，必须大于 0
    - overlap 是相邻两块的重复字符数，需满足 0 <= overlap < size
    - 最后一块可以不足 size
    - 参数非法时抛 ValueError
      生成器是惰性的：异常在第一次 next() 时抛出，不是调用 iter_chunks 时
    """
    if size <= 0:
        raise ValueError("size 必须 > 0")
    if overlap < 0 or overlap >= size:
        raise ValueError("overlap 必须满足 0 <= overlap < size")

    i = 0
    while i < len(text):
        chunk = text[i : i + size]
        yield chunk
        i += size - overlap


def take(n: int, it: Iterator[T]) -> list[T]:
    """取前 n 个元素。用 itertools.islice，不要写 list(it)[:n]。

    list(it) 会把整个迭代器消费完，对大文件或无限流不可用。
    """
    return list(islice(it, n))


if __name__ == "__main__":
    print(iter_chunks("abcdefg", 3))
    assert list(iter_chunks("abcdefg", 3)) == ["abc", "def", "g"]
    assert list(iter_chunks("abcdefg", 3, overlap=1)) == ["abc", "cde", "efg", "g"]

    g = iter_chunks("abcdefg", 3)
    assert next(g) == "abc", "第一次 next 才开始执行"
    assert take(1, g) == ["def"]
    assert list(g) == ["g"], "生成器是一次性的，已消费的元素不会再出现"

    for bad in (0, -1):
        try:
            list(iter_chunks("abc", bad))
        except ValueError:
            pass
        else:
            raise AssertionError(f"size={bad} 应抛 ValueError")

    print("generators: 全部通过")

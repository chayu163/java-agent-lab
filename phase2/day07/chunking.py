"""Day 7 练习：按固定字符窗口切分文本。"""

from __future__ import annotations


def chunk_text(text: str, size: int, overlap: int) -> list[str]:
    """返回长度不超过 size 的 chunks，并保留相邻 chunks 的 overlap。

    约定：
    - size 必须大于 0。
    - overlap 必须满足 0 <= overlap < size。
    - 空文本返回空列表。
    - 不跳过字符，也不重复生成最后一个 chunk。
    """
    raise NotImplementedError("TODO：实现带 overlap 的固定窗口切分")


def check_examples() -> None:
    assert chunk_text("", size=4, overlap=1) == []
    assert chunk_text("abcd", size=4, overlap=1) == ["abcd"]
    assert chunk_text("abcdefg", size=3, overlap=1) == ["abc", "cde", "efg"]
    assert chunk_text("abcdefg", size=3, overlap=0) == ["abc", "def", "g"]

    for size, overlap in ((0, 0), (3, -1), (3, 3)):
        try:
            chunk_text("abc", size=size, overlap=overlap)
        except ValueError:
            pass
        else:
            raise AssertionError(f"非法窗口参数未被拒绝: size={size}, overlap={overlap}")


if __name__ == "__main__":
    check_examples()
    print("chunking：全部断言通过")

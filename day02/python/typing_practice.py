"""Day 2 · 练习 4：Protocol / Generic。

FakeLLMClient 是 Day 4 写测试时现成的打桩件，当日就要能运行。

验收：uv run day02/python/typing_practice.py 通过断言；
      uv run mypy day02/python/typing_practice.py 零报错；
      再把 FakeLLMClient.complete 改名，mypy 必须报错，以此确认检查是结构化的。
"""

from collections.abc import Callable
from typing import Generic, Protocol, TypeVar

T = TypeVar("T")
U = TypeVar("U")


class LLMClient(Protocol):
    """实现 complete 即满足该协议，不需要显式继承。"""

    def complete(self, prompt: str) -> str: ...


class FakeLLMClient:
    """打桩客户端：查表命中则返回，未命中返回 default。"""

    def __init__(self, table: dict[str, str], default: str = "不知道") -> None:
        self.table = table
        self.default = default

    def complete(self, prompt: str) -> str:
        return self.table.get(prompt, self.default)


def ask(client: LLMClient, prompt: str) -> str:
    """接受任何满足 LLMClient 协议的对象，不依赖具体实现。"""
    return client.complete(prompt)


class Box(Generic[T]):
    """对应 Java 的 Box<T>。"""

    def __init__(self, value: T) -> None:
        self.value = value

    def get(self) -> T:
        return self.value

    def map(self, fn: Callable[[T], U]) -> "Box[U]":
        """返回新的 Box，不修改当前实例。"""
        return Box(fn(self.value))


if __name__ == "__main__":
    client: LLMClient = FakeLLMClient({"你好": "你好，有什么可以帮你"})
    assert ask(client, "你好") == "你好，有什么可以帮你"
    assert ask(client, "没见过的") == "不知道"

    box = Box(3)
    assert box.get() == 3
    assert box.map(lambda x: x * 2).get() == 6
    assert box.map(str).get() == "3"
    assert box.get() == 3, "map 不应修改原 Box"

    print("typing_practice: 全部通过")

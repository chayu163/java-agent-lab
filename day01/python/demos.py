"""Day 1 概念验证：Java 背景最容易误判的六个语义差异。

运行 uv run day01/python/demos.py 查看输出。每个函数演示一处差异，注释只写
「为什么与 Java 不同」，不复述代码本身。
"""

from dataclasses import dataclass


def demo_1_mutable_default() -> None:
    """默认参数在 def 执行时求值一次，可变对象由所有调用共享。"""

    def append_bad(item, bucket=[]):  # noqa: B006  # 故意演示错误写法
        bucket.append(item)
        return bucket

    print("bad 1:", append_bad("a"))
    print("bad 2:", append_bad("b"), "← 期望 ['b']，实际因共享累积成 ['a', 'b']")

    def append_good(item, bucket=None):  # 哨兵值 None，每次调用新建
        if bucket is None:
            bucket = []
        bucket.append(item)
        return bucket

    print("good 1:", append_good("a"))
    print("good 2:", append_good("b"))


def demo_2_is_vs_eq() -> None:
    """is 比较对象身份，== 比较值。

    与 Java 的对应关系正好相反：Python 的 == 对应 Java 的 equals()，
    Python 的 is 对应 Java 对引用类型的 ==。
    """
    a = [1, 2, 3]
    b = [1, 2, 3]
    c = a
    print("a == b:", a == b, "← 值相等")
    print("a is b:", a is b, "← 两个不同对象")
    print("a is c:", a is c, "← 同一个对象")

    # 用 int() 绕开编译期常量折叠，才能观察缓存边界
    x = 256
    y = int("256")
    print("256 is 256:", x is y, "← [-5, 256] 的小整数被 CPython 缓存复用")
    x = 257
    y = int("257")
    print("257 is 257:", x is y, "← 超出缓存范围，是两个对象")

    # is 的适用场景只有一处：与 None、True、False 比较
    v = None
    print("v is None:", v is None)


def demo_3_truthiness() -> None:
    """空容器、0、空字符串、None 都为假。判断只看容器是否为空，不看内容。"""
    for value in [[], {}, "", 0, 0.0, None, [0], "0"]:
        print(type(value).__name__, repr(value), "->", bool(value))


def demo_4_class_vs_instance_attr() -> None:
    """类属性由所有实例共享，实例属性在 __init__ 里用 self.x 创建。"""

    class Bad:
        tags = []  # noqa: RUF012  # 类属性，全体共享

        def add(self, t):
            self.tags.append(t)

    b1, b2 = Bad(), Bad()
    b1.add("x")
    print("bad b2.tags:", b2.tags, "← 期望 []，实际因共享变成 ['x']")

    class Good:
        def __init__(self):
            self.tags = []

        def add(self, t):
            self.tags.append(t)

    g1, g2 = Good(), Good()
    g1.add("x")
    print("good g2.tags:", g2.tags)


def demo_5_division() -> None:
    """整除与取模的符号规则与 Java 不同。

    Python 的 // 向下取整，% 的结果与除数同号；Java 的整数除法向零截断，
    % 的结果与被除数同号。两侧在正数上一致，遇到负数才分叉。
    """
    print("7 / 2 =", 7 / 2, "← 真除法永远返回 float")
    print("7 // 2 =", 7 // 2)
    print("-7 // 2 =", -7 // 2, "← 向下取整为 -4；Java 向零截断，结果为 -3")
    print("7 % 3 =", 7 % 3)
    print("-7 % 3 =", -7 % 3, "← 与除数同号，结果为 2；Java 为 -1")


@dataclass
class Order:
    """dataclass 自动生成 __init__、__repr__、__eq__。"""

    id: str
    amount: int = 0


def demo_6_dataclass() -> None:
    o1 = Order("A1", 100)
    o2 = Order("A1", 100)
    print("dataclass repr:", o1)
    print("dataclass eq:", o1 == o2, "← 按字段比较，不需要手写 equals")


if __name__ == "__main__":
    demo_1_mutable_default()
    print("-" * 40)
    demo_2_is_vs_eq()
    print("-" * 40)
    demo_3_truthiness()
    print("-" * 40)
    demo_4_class_vs_instance_attr()
    print("-" * 40)
    demo_5_division()
    print("-" * 40)
    demo_6_dataclass()

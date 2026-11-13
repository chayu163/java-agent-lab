"""Day 1 概念验证：Java 背景最容易踩的六个坑。直接 uv run demos.py 看输出。"""

from dataclasses import dataclass


def demo_1_mutable_default():
    """坑 1：默认参数在 def 时只求值一次，可变对象被所有调用共享。"""

    def append_bad(item, bucket=[]):  # noqa: B006  # 故意演示错误写法
        bucket.append(item)
        return bucket

    print("bad 1:", append_bad("a"))
    print("bad 2:", append_bad("b"))  # 期望 ['b']，实际 ['a', 'b']

    def append_good(item, bucket=None):  # 正确写法：哨兵值 None
        if bucket is None:
            bucket = []
        bucket.append(item)
        return bucket

    print("good 1:", append_good("a"))
    print("good 2:", append_good("b"))


def demo_2_is_vs_eq():
    """坑 2：is 比身份（是不是同一对象），== 比值。

    Java 的 == 对引用也是比身份，但 Integer 缓存坑更隐蔽。
    """
    a = [1, 2, 3]
    b = [1, 2, 3]
    c = a
    print("a == b:", a == b)  # 值相等 -> True
    print("a is b:", a is b)  # 不同对象 -> False
    print("a is c:", a is c)  # 同一对象 -> True

    # 用 int() 绕过编译期常量折叠，才能看到真正的缓存边界
    x = 256
    y = int("256")
    print("256 is 256:", x is y)  # True：[-5, 256] 小整数被缓存复用
    x = 257
    y = int("257")
    print("257 is 257:", x is y)  # False：超出缓存范围，是两个对象

    # 唯一该用 is 的场景：和 None / True / False 比较
    v = None
    print("v is None:", v is None)


def demo_3_truthiness():
    """坑 3：空容器、0、空字符串、None 都算 False。"""
    for value in [[], {}, "", 0, 0.0, None, [0], "0"]:
        # print(f"bool({value!r}) =", bool(value))
        print(type(value).__name__, repr(value), "->", bool(value))


def demo_4_class_vs_instance_attr():
    """坑 4：类属性被所有实例共享，可变类属性会被实例一起改。"""

    class Bad:
        tags = []  # noqa: RUF012  # 类属性，全体共享

        def add(self, t):
            self.tags.append(t)

    b1, b2 = Bad(), Bad()
    b1.add("x")
    print("bad b2.tags:", b2.tags)  # 期望 []，实际 ['x']

    class Good:
        def __init__(self):
            self.tags = []  # 每个实例自己的

        def add(self, t):
            self.tags.append(t)

    g1, g2 = Good(), Good()
    g1.add("x")
    print("good g2.tags:", g2.tags)


def demo_5_division():
    """坑 5：/ 永远是浮点，整除是 //，取模 % 对负数行为与 Java 一致（都向 0 截断）。"""
    print("7 / 2 =", 7 / 2)  # 3.5，不是 3
    print("7 // 2 =", 7 // 2)  # 3
    print("-7 // 2 =", -7 // 2)  # -4（向下取整，不是截断！Java 是 -3）
    print("7 % 3 =", 7 % 3)
    print("-7 % 3 =", -7 % 3)  # 2（Python 取模结果与除数同号）


@dataclass
class Order:
    """顺带展示 dataclass：Java 的 record/POJO + equals/hashCode/toString 自动生成。"""

    id: str
    amount: int = 0


def demo_6_dataclass():
    o1 = Order("A1", 100)
    o2 = Order("A1", 100)
    print("dataclass repr:", o1)
    print("dataclass eq:", o1 == o2)  # 自动按字段比较，不需要手写 equals


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

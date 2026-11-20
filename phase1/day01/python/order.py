"""Day 1 作业：把 Order.java 的状态机翻译成 Python。

四条约束：
1. 用 enum.Enum + auto() 定义状态，print(state) 输出可读名字
2. 非法转换抛 InvalidTransition，消息里带当前状态
3. history 对外返回不可变副本，对应 Java 的 List.copyOf
4. apply(event: str) 用字典分发表，不用 if/elif 链

本文件是批注版：❌ 标注被替换掉的写法，✅ 标注当前写法，原因写在该行上方。
组织方式按 Java bean —— 字段私有 + 只读属性（getter），状态只能经业务方法流转。
刻意不提供 setter：一旦开放写入口，外部就能绕过状态机直接赋值。
"""

from enum import Enum, auto
from typing import ClassVar


class InvalidTransition(Exception):
    """非法状态转换。"""


class OrderState(Enum):
    CREATED = auto()
    PAID = auto()
    SHIPPED = auto()
    CANCELLED = auto()


# 这里保留普通类的身份相等语义，与 Java 未重写 equals 的版本一致。
# 若启用 dataclass 默认的 eq=True，即使手写 __init__，dataclass 仍会生成按字段比较的 __eq__。
# dataclass 也可通过 eq=False 保留身份相等，因此是否使用取决于对象的比较语义。
#
# @dataclass
# class Order:
#     _id: str
#     _state: OrderState
#     _history: list[OrderState]


class Order:
    """订单状态机。"""

    # 事件名到处理方法名的映射。声明为类属性只构造一次。
    # ❌ 原写法在每次 apply 调用里重建这个 dict。
    _EVENTS: ClassVar[dict[str, str]] = {
        "pay": "pay",
        "ship": "ship",
        "cancel": "cancel",
    }

    def __init__(
        self,
        id: str,
        # ❌ state: OrderState = None          触发 mypy 的隐式 Optional 报告
        # ❌ history: list[OrderState] = None  同上
        # 当前 mypy 配置要求把可空性写入注解；Python 运行时本身不会据此拒绝 None。
        state: OrderState | None = None,
        history: list[OrderState] | None = None,
    ) -> None:
        self._id = id
        self._state = state if state is not None else OrderState.CREATED
        self._history = history.copy() if history is not None else [self._state]

    def pay(self) -> None:
        if self._state != OrderState.CREATED:
            # 用 .name 对齐 Java 输出的 "CREATED"；直接插值枚举会打印 OrderState.CREATED。
            raise InvalidTransition(f"Cannot pay when order is in state {self._state.name}")
        # ❌ self.state = OrderState.PAID
        # ❌ self.history.append(self.state)
        # 这两行抛 AttributeError: property 'state' has no setter。
        # property 是只读的，类内部一律写私有字段。
        self._state = OrderState.PAID
        self._history.append(self._state)

    def ship(self) -> None:
        if self._state != OrderState.PAID:
            raise InvalidTransition(f"Cannot ship when order is in state {self._state.name}")
        # ❌ self.state = OrderState.SHIPPED
        # ❌ self.history.append(self.state)
        self._state = OrderState.SHIPPED
        self._history.append(self._state)

    def cancel(self) -> None:
        # ❌ if self._state != OrderState.CREATED:
        # 这种写法只放行 CREATED，但 Java 原版拒绝的是 SHIPPED 和 CANCELLED，
        # 即 CREATED 与 PAID 都可取消。翻译状态机时先确定允许集合，再写条件。
        if self._state in (OrderState.SHIPPED, OrderState.CANCELLED):
            raise InvalidTransition(f"Cannot cancel when order is in state {self._state.name}")
        self._state = OrderState.CANCELLED
        self._history.append(self._state)

    def apply(self, event: str) -> None:
        # ❌ 原写法在每次调用里重建 event_map。
        handler = self._EVENTS.get(event)
        if handler is None:
            raise ValueError(f"Unknown event: {event}")
        getattr(self, handler)()

    # 只读属性即 Java bean 的 getter；没有 setter，外部拿不到写入口。
    @property
    def id(self) -> str:
        return self._id

    @property
    def state(self) -> OrderState:
        return self._state

    @property
    def history(self) -> tuple[OrderState, ...]:
        # tuple() 对应 Java 的 List.copyOf：调用方拿到快照，无法改动内部 list。
        return tuple(self._history)

    def __repr__(self) -> str:  # Java 的 toString()
        history = [s.name for s in self._history]
        return f"Order(id={self._id!r}, state={self._state.name}, history={history})"


if __name__ == "__main__":
    order = Order("A1")
    order.pay()
    order.ship()
    print(order)

    # PAID 状态同样可以取消，Java 原版允许。
    paid = Order("A2")
    paid.pay()
    paid.cancel()
    print(paid)

    # 非法转换
    shipped = Order("A3")
    shipped.pay()
    shipped.ship()
    try:
        shipped.cancel()
    except InvalidTransition as exc:
        print("expected:", exc)

    # 未知事件
    try:
        shipped.apply("refund")
    except ValueError as exc:
        print("expected:", exc)

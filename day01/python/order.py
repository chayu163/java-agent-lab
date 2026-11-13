"""Day 1 作业：把 Order.java 的状态机翻译成 Python。

四条硬性要求：
1. 用 enum.Enum + auto() 定义状态，print(state) 输出可读的名字
2. 非法转换抛 InvalidTransition，异常消息里带当前状态
3. history 对外返回不可变副本（对应 Java 的 List.copyOf）
4. apply(event: str) 用字典分发表实现，不要 if/elif 链

批注版（2026-11-13）：❌ 是被注释掉的原写法，✅ 是改法，原因写在旁边。
组织方式按 Java bean：字段私有 + 只读属性（getter），状态只能通过业务方法流转；
故意不提供 setter —— 否则外部能绕过状态机直接改状态。
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


# ---------------- 原写法（已注释） ----------------
# ❌ @dataclass 只用了半截：类里已有手写的 __init__，dataclass 就不再生成 init，
#    但 __repr__ / __eq__ 照样会生成，于是 Order("A1") == Order("A1") 为 True
#    （Java 没写 equals 时是 False）。要么全用 dataclass + __post_init__，
#    要么不用；这里按 Java bean 风格选后者。
#
# @dataclass
# class Order:
#     _id: str
#     _state: OrderState
#     _history: list[OrderState]
# --------------------------------------------------


class Order:
    """订单状态机。"""

    # ✅ 事件名 -> 处理方法名。类属性只建一次；原写法在每次 apply 调用时重建 dict。
    _EVENTS: ClassVar[dict[str, str]] = {
        "pay": "pay",
        "ship": "ship",
        "cancel": "cancel",
    }

    def __init__(
        self,
        id: str,
        # ❌ state: OrderState = None          -> mypy: 隐式 Optional（Python 注解默认不可空）
        # ❌ history: list[OrderState] = None  -> 同上
        state: OrderState | None = None,
        history: list[OrderState] | None = None,
    ) -> None:
        self._id = id
        self._state = state if state is not None else OrderState.CREATED
        self._history = history.copy() if history is not None else [self._state]

    def pay(self) -> None:
        if self._state != OrderState.CREATED:
            # 用 .name 对齐 Java 输出的 "CREATED"；直接插值枚举会打印 OrderState.CREATED
            raise InvalidTransition(f"Cannot pay when order is in state {self._state.name}")
        # ❌ self.state = OrderState.PAID
        # ❌ self.history.append(self.state)
        #    这两行会抛 AttributeError: property 'state' has no setter。
        #    property 是只读的，类内部一律写私有字段 self._state / self._history。
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
        #    原写法只放行 CREATED，但 Java 原版拒绝的是 SHIPPED 和 CANCELLED，
        #    也就是 CREATED 和 PAID 都能取消。翻译状态机先读成"允许集合"再写条件。
        if self._state in (OrderState.SHIPPED, OrderState.CANCELLED):
            raise InvalidTransition(f"Cannot cancel when order is in state {self._state.name}")
        self._state = OrderState.CANCELLED
        self._history.append(self._state)

    def apply(self, event: str) -> None:
        # ❌ 原写法在每次调用里重建 event_map
        handler = self._EVENTS.get(event)
        if handler is None:
            raise ValueError(f"Unknown event: {event}")
        getattr(self, handler)()

    # 只读属性 = Java bean 的 getter 方法；没有 setter 意味着外部拿不到写入口
    @property
    def id(self) -> str:
        return self._id

    @property
    def state(self) -> OrderState:
        return self._state

    @property
    def history(self) -> tuple[OrderState, ...]:
        # ✅ tuple() 就是 Java 的 List.copyOf：调用方拿到快照，改不到内部 list
        return tuple(self._history)

    def __repr__(self) -> str:  # Java 的 toString()
        history = [s.name for s in self._history]
        return f"Order(id={self._id!r}, state={self._state.name}, history={history})"


if __name__ == "__main__":
    order = Order("A1")
    order.pay()
    order.ship()
    print(order)

    # PAID 状态也能取消（Java 原版允许，之前的写法会误抛异常）
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

"""Day 1 无批注版：Java bean 映射到 Python 的标准写法。

Java bean 的五个约定 -> Python 的对应物：
    私有字段      private String id;        ->  self._id（下划线约定）
    getter        public String getId()     ->  @property def id
    setter        public void setState(...) ->  @state.setter（本例故意不提供）
    构造器        public Order(String id)   ->  __init__
    toString      public String toString()  ->  __repr__
    equals/hashCode                        ->  __eq__ / __hash__

状态字段没有 setter：状态只能通过 pay / ship / cancel 流转，
外部拿不到写入口，才守得住状态机的不变量。
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


class Order:
    """订单状态机。"""

    _EVENTS: ClassVar[dict[str, str]] = {
        "pay": "pay",
        "ship": "ship",
        "cancel": "cancel",
    }

    def __init__(
        self,
        id: str,
        state: OrderState | None = None,
        history: list[OrderState] | None = None,
    ) -> None:
        self._id = id
        self._state = state if state is not None else OrderState.CREATED
        self._history = history.copy() if history is not None else [self._state]

    # ---- 业务方法：唯一的状态写入口 ----

    def pay(self) -> None:
        if self._state != OrderState.CREATED:
            raise InvalidTransition(f"Cannot pay when order is in state {self._state.name}")
        self._state = OrderState.PAID
        self._history.append(self._state)

    def ship(self) -> None:
        if self._state != OrderState.PAID:
            raise InvalidTransition(f"Cannot ship when order is in state {self._state.name}")
        self._state = OrderState.SHIPPED
        self._history.append(self._state)

    def cancel(self) -> None:
        if self._state in (OrderState.SHIPPED, OrderState.CANCELLED):
            raise InvalidTransition(f"Cannot cancel when order is in state {self._state.name}")
        self._state = OrderState.CANCELLED
        self._history.append(self._state)

    def apply(self, event: str) -> None:
        handler = self._EVENTS.get(event)
        if handler is None:
            raise ValueError(f"Unknown event: {event}")
        getattr(self, handler)()

    # ---- 只读属性：Java 的 getter ----

    @property
    def id(self) -> str:
        return self._id

    @property
    def state(self) -> OrderState:
        return self._state

    @property
    def history(self) -> tuple[OrderState, ...]:
        return tuple(self._history)

    # ---- Object 方法：Java 的 toString / equals / hashCode ----

    def __repr__(self) -> str:
        history = [s.name for s in self._history]
        return f"Order(id={self._id!r}, state={self._state.name}, history={history})"

    def __eq__(self, other: object) -> bool:
        if not isinstance(other, Order):
            return NotImplemented
        return self._id == other._id

    def __hash__(self) -> int:
        return hash(self._id)


if __name__ == "__main__":
    order = Order("A1")
    order.pay()
    order.ship()
    print(order)

    paid = Order("A2")
    paid.pay()
    paid.cancel()
    print(paid)

    shipped = Order("A3")
    shipped.pay()
    shipped.ship()
    try:
        shipped.cancel()
    except InvalidTransition as exc:
        print("expected:", exc)

    try:
        shipped.apply("refund")
    except ValueError as exc:
        print("expected:", exc)

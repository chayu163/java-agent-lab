"""Day 8 练习：计算确定性 top-k 检索指标。"""

from __future__ import annotations

from typing import TypedDict


class GoldenCase(TypedDict):
    query_id: str
    relevant_ids: set[str]


def recall_at_k(relevant_ids: set[str], retrieved_ids: list[str], k: int) -> float:
    """返回前 k 个结果中相关 ID 的召回比例。

    k <= 0 或 golden set 没有相关 ID 时抛出 ValueError。
    """
    raise NotImplementedError("TODO：实现 Recall@k")


def hit_at_k(relevant_ids: set[str], retrieved_ids: list[str], k: int) -> float:
    """前 k 个结果命中任一相关 ID 时返回 1.0，否则返回 0.0。"""
    raise NotImplementedError("TODO：实现 Hit@k")


def evaluate(
    golden_cases: list[GoldenCase],
    retrieved_by_query: dict[str, list[str]],
    k: int,
) -> dict[str, float]:
    """计算给定 golden cases 的平均 Recall@k 与 Hit@k。

    每个 case 包含 query_id 和非空的 relevant_ids 集合。
    每个 query_id 都必须有对应的检索结果列表。
    """
    raise NotImplementedError("TODO：逐题计算指标并求平均值")


GOLDEN_CASES: list[GoldenCase] = [
    {"query_id": "q1", "relevant_ids": {"ship-1", "ship-2"}},
    {"query_id": "q2", "relevant_ids": {"return-1"}},
]

RETRIEVED_BY_QUERY = {
    "q1": ["ship-1", "policy-1"],
    "q2": ["policy-2", "return-1"],
}


def check_examples() -> None:
    scores = evaluate(GOLDEN_CASES, RETRIEVED_BY_QUERY, k=2)
    assert scores["recall_at_k"] == 0.75
    assert scores["hit_at_k"] == 1.0

    assert recall_at_k({"a"}, ["a", "b"], k=1) == 1.0
    assert recall_at_k({"a", "b"}, ["a"], k=2) == 0.5
    assert hit_at_k({"a"}, ["b", "a"], k=2) == 1.0
    assert hit_at_k({"a"}, ["b", "c"], k=2) == 0.0

    for invalid_k in (0, -1):
        try:
            recall_at_k({"a"}, ["a"], k=invalid_k)
        except ValueError:
            pass
        else:
            raise AssertionError(f"k={invalid_k} 应抛 ValueError")


if __name__ == "__main__":
    check_examples()
    print("evaluate_retrieval：全部断言通过")

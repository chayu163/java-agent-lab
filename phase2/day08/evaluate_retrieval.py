"""Day 8 练习：计算确定性 top-k 检索指标。"""

from __future__ import annotations

import statistics
from typing import TypedDict


class GoldenCase(TypedDict):
    query_id: str
    relevant_ids: set[str]


def recall_at_k(relevant_ids: set[str], retrieved_ids: list[str], k: int) -> float:
    """返回前 k 个结果中相关 ID 的召回比例。

    k <= 0 或 golden set 没有相关 ID 时抛出 ValueError。
    """
    # ❌ if relevant_ids is None: 永远不触发——签名是 set[str]，调用方不会传 None。
    #    真正的边界是【空集合 set()】：能穿过这条检查，走到除法时
    #    all_number == 0，抛 ZeroDivisionError，而不是这条清晰的 ValueError。
    #    README 列的"空相关集合"指的就是它。not relevant_ids 同时覆盖 None 与空集。
    if k <= 0:
        raise ValueError("k 必须大于 0")
    if not relevant_ids:
        raise ValueError("golden set 没有相关 ID")

    # ❌ 原写法是手动下标 while 循环 + break（Java 的 for(i<k) 习惯）。
    #    Python 的切片 [:k] 直接表达"前 k 个"：结果不足 k 条时切片越界
    #    不报错、取到哪算哪，原写法里 index == len(...) 的 break 就不需要了。
    hit_number = sum(1 for retrieved_id in retrieved_ids[:k] if retrieved_id in relevant_ids)
    return hit_number / len(relevant_ids)


def hit_at_k(relevant_ids: set[str], retrieved_ids: list[str], k: int) -> float:
    """前 k 个结果命中任一相关 ID 时返回 1.0，否则返回 0.0。"""
    if k <= 0:
        raise ValueError("k 必须大于 0")
    if not relevant_ids:
        raise ValueError("golden set 没有相关 ID")

    # any() 短路：找到第一个命中就停，语义与"至少命中一个"一一对应
    return 1.0 if any(retrieved_id in relevant_ids for retrieved_id in retrieved_ids[:k]) else 0.0


def evaluate(
    golden_cases: list[GoldenCase],
    retrieved_by_query: dict[str, list[str]],
    k: int,
) -> dict[str, float]:
    """计算给定 golden cases 的平均 Recall@k 与 Hit@k。

    每个 case 包含 query_id 和非空的 relevant_ids 集合。
    每个 query_id 都必须有对应的检索结果列表。
    """
    # ❌ 原写法对缺失结果 append 0 分混进平均值。"检索器漏了这道题"与
    #    "查了但没命中"是两种故障：前者是管道断裂（配置错、query_id 对不上），
    #    后者才是检索质量。混在一起平均，一个配置 bug 会让指标静默变差——
    #    数字看着像"检索不太行"，实际是"一半的题根本没跑"，而你还拿着
    #    这个数字做回归比较。契约缺失必须炸出来，不是打分。
    recall_scores: list[float] = []
    hit_scores: list[float] = []

    for golden_case in golden_cases:
        # ❌ 原写法用 .get() 取键。GoldenCase 是 TypedDict，两个键必填，
        #    直接下标取值；.get() 返回 X | None，把 Optional 一路传给了
        #    recall_at_k，那边的 is None 检查（还拦不住空集）就是这么来的。
        #    入口类型收窄，下游检查才能少。
        query_id = golden_case["query_id"]
        relevant_ids = golden_case["relevant_ids"]
        retrieved_ids = retrieved_by_query.get(query_id)
        if retrieved_ids is None:
            raise ValueError(f"query_id {query_id!r} 缺少检索结果")

        recall_scores.append(recall_at_k(relevant_ids, retrieved_ids, k))
        hit_scores.append(hit_at_k(relevant_ids, retrieved_ids, k))

    return {
        "recall_at_k": statistics.mean(recall_scores),
        "hit_at_k": statistics.mean(hit_scores),
    }


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

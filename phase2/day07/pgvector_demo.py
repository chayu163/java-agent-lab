"""将示例文档写入 pgvector，并按查询向量检索 chunks。

运行时把本次的 chunk 清单、查询与 top-k 结果写进 logs/，作为笔记引用的实证。
"""

from __future__ import annotations

import json
import os
from datetime import datetime
from pathlib import Path
from typing import Any

import httpx
import psycopg
from pgvector import Vector
from pgvector.psycopg import register_vector

from phase2.day07.chunking import chunk_text

LOGS_DIR = Path(__file__).resolve().parent / "logs"

DOCUMENTS = {
    "shipping.md": """
    发货后可以在订单详情页查看物流。顺丰单号通常以 SF 开头。

    如果订单尚未发货，页面会显示预计发货时间。
    """,
    "returns.md": """
    订单签收后七天内可以申请退货。生鲜商品和已拆封的个人护理商品不支持无理由退货。

    申请通过后，退款会退回原支付账户。
    """,
}
QUERY = "订单已经发货，在哪里查顺丰物流单号？"
TABLE_NAME = "rag_chunks"
MAX_HNSW_DIMENSIONS = 2000


def embed_texts(
    texts: list[str],
    *,
    base_url: str,
    model: str,
    api_key: str | None,
) -> list[list[float]]:
    headers = {"Authorization": f"Bearer {api_key}"} if api_key else {}
    response = httpx.post(
        f"{base_url.rstrip('/')}/embeddings",
        json={"model": model, "input": texts},
        headers=headers,
        timeout=60.0,
    )
    response.raise_for_status()
    payload = response.json()
    rows = payload.get("data")
    if not isinstance(rows, list) or len(rows) != len(texts):
        raise ValueError("Embedding 响应的 data 数量与输入文本数不匹配")
    if any(not isinstance(row, dict) or not isinstance(row.get("index"), int) for row in rows):
        raise ValueError("Embedding 响应缺少有效的 index")
    indices = sorted(row["index"] for row in rows)
    if indices != list(range(len(texts))):
        raise ValueError("Embedding 响应的 index 不完整或重复")

    ordered = sorted(rows, key=lambda row: row["index"])
    vectors = [row["embedding"] for row in ordered]
    if any(not isinstance(vector, list) for vector in vectors):
        raise ValueError("Embedding 必须是向量列表")
    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) != 1:
        raise ValueError("同一批 embedding 的向量维度不一致")
    dimension = dimensions.pop()
    if dimension == 0 or dimension > MAX_HNSW_DIMENSIONS:
        raise ValueError(f"HNSW cosine index 要求 1 到 {MAX_HNSW_DIMENSIONS} 维")
    return vectors


def prepare_chunks() -> list[dict[str, Any]]:
    rows = []
    for source, text in DOCUMENTS.items():
        for index, content in enumerate(chunk_text(text, size=120, overlap=20)):
            rows.append({"source": source, "chunk_index": index, "content": content})
    return rows


def store_chunks(dsn: str, chunks: list[dict[str, Any]], vectors: list[list[float]]) -> None:
    if len(chunks) != len(vectors):
        raise ValueError("chunk 数量与 embedding 数量不匹配")
    dimensions = {len(vector) for vector in vectors}
    if len(dimensions) != 1:
        raise ValueError("同一批 embedding 的向量维度不一致")
    dimension = dimensions.pop()
    if dimension == 0 or dimension > MAX_HNSW_DIMENSIONS:
        raise ValueError(f"HNSW cosine index 要求 1 到 {MAX_HNSW_DIMENSIONS} 维")

    with psycopg.connect(dsn) as connection:
        with connection.cursor() as cursor:
            cursor.execute("CREATE EXTENSION IF NOT EXISTS vector")
        register_vector(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""CREATE TABLE IF NOT EXISTS {TABLE_NAME} (
                    source TEXT NOT NULL,
                    chunk_index INTEGER NOT NULL,
                    content TEXT NOT NULL,
                    embedding vector({dimension}) NOT NULL,
                    PRIMARY KEY (source, chunk_index)
                )"""
            )
            cursor.execute(
                f"""CREATE INDEX IF NOT EXISTS {TABLE_NAME}_embedding_hnsw
                    ON {TABLE_NAME} USING hnsw (embedding vector_cosine_ops)"""
            )

            for source in DOCUMENTS:
                cursor.execute(f"DELETE FROM {TABLE_NAME} WHERE source = %s", (source,))

            cursor.executemany(
                f"""INSERT INTO {TABLE_NAME}
                    (source, chunk_index, content, embedding)
                    VALUES (%s, %s, %s, %s)""",
                [
                    (
                        chunk["source"],
                        chunk["chunk_index"],
                        chunk["content"],
                        Vector(vector),
                    )
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
            )


def search(dsn: str, query_vector: list[float], top_k: int) -> list[dict[str, Any]]:
    if top_k < 1:
        raise ValueError("top_k 必须大于 0")

    with psycopg.connect(dsn) as connection:
        register_vector(connection)
        with connection.cursor() as cursor:
            cursor.execute(
                f"""SELECT source, chunk_index, content, embedding <=> %s AS distance
                    FROM {TABLE_NAME}
                    ORDER BY embedding <=> %s
                    LIMIT %s""",
                (Vector(query_vector), Vector(query_vector), top_k),
            )
            return [
                {"source": row[0], "chunk_index": row[1], "content": row[2], "distance": row[3]}
                for row in cursor.fetchall()
            ]


def save_log(
    chunks: list[dict[str, Any]],
    vectors: list[list[float]],
    query_vector: list[float],
    results: list[dict[str, Any]],
    *,
    dsn_host: str,
    model: str,
) -> Path:
    """把本次运行的关键事实写成 JSON：chunk 切分、维度、模型、top-k 结果。"""
    LOGS_DIR.mkdir(parents=True, exist_ok=True)
    stamp = datetime.now().strftime("%Y%m%d-%H%M%S")
    path = LOGS_DIR / f"retrieval-{stamp}.json"
    path.write_text(
        json.dumps(
            {
                "embedding_model": model,
                "embedding_dimensions": len(query_vector),
                "dsn_host": dsn_host,
                "chunks": [
                    {**chunk, "dimensions": len(vector)}
                    for chunk, vector in zip(chunks, vectors, strict=True)
                ],
                "query": QUERY,
                "top_k": len(results),
                "results": results,
            },
            ensure_ascii=False,
            indent=2,
        ),
        encoding="utf-8",
    )
    return path


def main() -> None:
    dsn = os.environ.get("PGVECTOR_DSN")
    embedding_base_url = os.environ.get("EMBEDDING_BASE_URL")
    embedding_model = os.environ.get("EMBEDDING_MODEL")
    if not dsn or not embedding_base_url or not embedding_model:
        raise SystemExit("请设置 PGVECTOR_DSN、EMBEDDING_BASE_URL 和 EMBEDDING_MODEL 后再运行")

    chunks = prepare_chunks()
    api_key = os.environ.get("EMBEDDING_API_KEY")
    # 所有 chunk 内容一次请求送 embedding 模型，返回向量顺序与输入一致
    vectors = embed_texts(
        [chunk["content"] for chunk in chunks],
        base_url=embedding_base_url,
        model=embedding_model,
        api_key=api_key,
    )
    # 查询句单独送同一个 embedding 模型，得到查询向量；入库与查询必须同模型
    query_vector = embed_texts(
        [QUERY],
        base_url=embedding_base_url,
        model=embedding_model,
        api_key=api_key,
    )[0]
    # chunk 文本连同向量写入 pgvector（先删旧数据保证重跑不残留）
    store_chunks(dsn, chunks, vectors)
    # 用查询向量按 cosine distance 升序查库，取最相近的 top_k 条
    results = search(dsn, query_vector, top_k=3)

    for result in results:
        print(
            f"{result['source']}#{result['chunk_index']} "
            f"distance={result['distance']:.4f} {result['content'].strip()}"
        )

    dsn_host = psycopg.conninfo.conninfo_to_dict(dsn).get("host", "")
    path = save_log(
        chunks,
        vectors,
        query_vector,
        results,
        dsn_host=str(dsn_host),
        model=embedding_model,
    )
    print(f"日志已写入 {path}")


if __name__ == "__main__":
    main()

"""探针：验证 Chroma 实际用的距离函数 + `1-d/2` 到底是什么

背景：config.py 注释写"Chroma 默认用余弦距离"，但 vectorstore.py 没设 hnsw:space，
      而 Chroma 的默认是 l2。两种假设下 `1-d/2` 的含义完全不同，必须实测定性。

做法：对相关/无关 query 各取 top-5，同时打印
  - raw distance（Chroma 原样返回）
  - 1-d/2（线上 cosine_distance_to_similarity 的值）
  - 按 l2 假设反推的 cos = 1 - d^2/2
  - 按 cosine-distance 假设反推的 cos = 1 - d
  - 手算的真余弦（直接拿两个向量点积），作为裁判
"""
import math

from app.rag.retriever import cosine_distance_to_similarity
from app.rag.vectorstore import get_embeddings, get_vectorstore


def cos_manual(a, b):
    dot = sum(x * y for x, y in zip(a, b))
    na = math.sqrt(sum(x * x for x in a))
    nb = math.sqrt(sum(y * y for y in b))
    return dot / (na * nb)


def main():
    vs = get_vectorstore()
    print("collection metadata:", vs._collection.metadata)
    print("collection count   :", vs._collection.count())

    emb = get_embeddings()

    queries = [
        ("相关", "React 的 useEffect 什么时候执行"),
        ("无关", "怎么用 Python 煮咖啡"),
        ("无关", "今天天气怎么样"),
    ]

    for label, q in queries:
        print(f"\n=== [{label}] {q} ===")
        print(f"{'rank':>4} {'d(raw)':>8} {'1-d/2':>8} {'cos(l2)':>8} {'cos(d=1-c)':>11} {'cos(手算)':>10}")
        results = vs.similarity_search_with_score(q, k=5)
        qv = emb.embed_query(q)
        for i, (doc, dist) in enumerate(results, 1):
            dv = emb.embed_query(doc.page_content)
            print(
                f"{i:>4} {dist:>8.4f} {cosine_distance_to_similarity(dist):>8.4f} "
                f"{1 - dist ** 2 / 2:>8.4f} {1 - dist:>11.4f} {cos_manual(qv, dv):>10.4f}"
            )


if __name__ == "__main__":
    main()

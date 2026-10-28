"""
retriever.py —— 检索函数 + 阈值兜底

Chroma 的分数说明：
─────────────────────────────────
Chroma 默认用 cosine distance（余弦距离），范围 [0, 2]：
  0 = 两个向量方向完全一致（意思一模一样）
  1 = 正交（没关系）
  2 = 方向相反（意思完全对立）

我们习惯用"相似度"来理解，所以做个转换：
  similarity = 1 - distance / 2
  → 距离 0 = 相似度 1.0（完美）
  → 距离 1 = 相似度 0.5
  → 距离 2 = 相似度 0.0（完全不搭）

SCORE_THRESHOLD = 0.3 意味着：相似度 < 0.3 的直接扔掉，
相当于"没翻到书"，避免给 AI 喂垃圾上下文。
"""


"""
总体就是：
1. 从向量库里取 top_k 条
2. 转相似度
3. 过滤掉相似度低于 score_threshold 的
4. 返回过滤后的结果
"""
from typing import List, Optional, Tuple

from langchain_core.documents import Document

from app.core import config
from app.rag.schemas import RetrievedChunk
from app.rag.vectorstore import get_vectorstore

"""这个函数单独抽出来:为了可测试,是整个RAG的度量衡.工程化思维:公式即函数,函数即可测"""
def cosine_distance_to_similarity(distance: float) -> float:
    """Chroma 给的是余弦距离，转成人类友好的相似度 [0, 1]"""
    return 1.0 - distance / 2.0


"""retriever 主函数"""
def retrieve(
    query: str,
    top_k: Optional[int] = None,
    score_threshold: Optional[float] = None,
) -> List[RetrievedChunk]:
    """
    核心检索函数。

    参数:
        query:           用户的问题（自然语言）
        top_k:           最多取几条。None = 用 config.TOP_K（调用时才读，测试可覆盖）
        score_threshold: 相似度低于这个值的丢掉。None = 用 config.SCORE_THRESHOLD

    返回:
        过滤后的 RetrievedChunk 列表，每条的 metadata 里带 "similarity" 和 "source"
        如果一条都没命中 → 返回空列表 []
    """
    # 哨兵：不能在函数定义时写 `top_k: int = TOP_K`，那是 import 时就把值绑死，
    # 之后改 config 或测试 monkeypatch 都不生效。改成 None 后每次调用才读。
    if top_k is None:
        top_k = config.TOP_K
    if score_threshold is None:
        score_threshold = config.SCORE_THRESHOLD

    """先拿向量库，没建就明确报错"""
    vs = get_vectorstore()
    if vs is None:
        raise RuntimeError("向量库还没建！先跑 `python -m app.rag.vectorstore` 构建它")

    # similarity_search_with_score = 搜索 + 返回每条的分数（距离）
    # 返回的是 [(Document, distance), (Document, distance), ...]
    """搜索+带分数"""
    raw_results: List[Tuple[Document, float]] = vs.similarity_search_with_score(
        query=query,
        k=top_k,
    )

    """转相似度+阈值过滤+组装成显式类型"""
    chunks: List[RetrievedChunk] = []
    for doc, distance in raw_results:
        sim = cosine_distance_to_similarity(distance)     # 距离转相似度

        if sim >= score_threshold:       # 阈值兜底
            chunks.append(RetrievedChunk(
                content=doc.page_content,
                source=doc.metadata.get("source", "?"),
                similarity=round(sim, 4),
            ))
        else:
            print(f"  [retriever] 丢弃（相似度 {sim:.3f} < 阈值 {score_threshold}）: "
                  f"{doc.metadata.get('source', '?')}")

    """一行日志(未来logging)"""
    print(f"[retriever] query='{query[:40]}...' → {len(chunks)}/{len(raw_results)} 条通过阈值")
    return chunks


if __name__ == "__main__":
    # 直接运行可以手动测一条 query
    test_query = "useState 是什么？怎么用？"
    results = retrieve(test_query)

    print(f"\n🔍 查询: {test_query}")
    print("=" * 60)
    for i, chunk in enumerate(results):
        print(f"\n【结果 {i+1}】source={chunk.source} "
              f"| 相似度={chunk.similarity}")
        # 打印前 200 字
        preview = chunk.content[:200].replace("\n", " ")
        print(f"  {preview}...")

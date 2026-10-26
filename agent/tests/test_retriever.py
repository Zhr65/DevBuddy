from app.rag.retriever import cosine_distance_to_similarity, retrieve
def test_distance_to_similarity():
    assert cosine_distance_to_similarity(0.0) == 1.0
    assert cosine_distance_to_similarity(1.0) == 0.5
    assert cosine_distance_to_similarity(2.0) == 0.0

class FakeVectorStore:
    """模拟向量数据库（测试替身，只实现retriever 用到的一个方法，签名照抄真实调用）"""
    def __init__(self, results):
        self.results = results
    def similarity_search_with_score(self, query, k):
        return self.results

def test_retrieve_returns_typed_chunks_and_filters(monkeypatch):
    from langchain_core.documents import Document
    fake = FakeVectorStore([
        (Document(page_content="命中的内容", metadata={"source": "a.md"}), 0.25),
        (Document(page_content="噪音内容", metadata={"source": "b.md"}), 1.75),
    ])
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)
    out = retrieve("userState 怎么用", top_k=2, score_threshold=0.3)
    assert len(out) == 1
    assert out[0].content == "命中的内容"
    assert out[0].source == "a.md"
    assert out[0].similarity == 0.875
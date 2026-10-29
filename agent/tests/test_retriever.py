"""retrieve / cosine_distance_to_similarity 的行为测试。

约定：所有测试都用 conftest.py 里的 fake_vs 夹具造假向量库，
不加载真实 Chroma、不加载 BGE-M3 模型——所以整套跑下来是毫秒级。
"""
import pytest
from langchain_core.documents import Document

from app.rag.retriever import cosine_distance_to_similarity, retrieve, RetrievalError


def _doc(text: str, source: str) -> Document:
    """造一条假的检索结果（模拟 loader 切块后的形状）。"""
    return Document(page_content=text, metadata={"source": source})


def test_distance_to_similarity():
    """锁定距离→相似度的转换公式。

    抓的 bug：谁把 `1 - d/2` 改成别的写法，或者把 /2 写漏。
    0/1/2 三个点都是二进制精确值，可以直接 == 比。
    """
    assert cosine_distance_to_similarity(0.0) == 1.0
    assert cosine_distance_to_similarity(1.0) == 0.5
    assert cosine_distance_to_similarity(2.0) == 0.0


def test_retrieve_returns_typed_chunks_and_filters(monkeypatch, fake_vs):
    """混合数据：一条过阈值、一条被过滤。

    抓的 bug：① 阈值过滤失效（噪声也被返回）；② 字段映射错位
    （content 取错、source 从 metadata 取错、sim 算错）。
    距离 0.25 → 相似度 0.875，精确可表示，可以 == 比。
    """
    fake = fake_vs([
        (_doc("命中的内容", "a.md"), 0.25),
        (_doc("噪音内容", "b.md"), 1.75),
    ])
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)

    out = retrieve("useState 怎么用", top_k=2, score_threshold=0.3)

    assert len(out) == 1
    assert out[0].content == "命中的内容"
    assert out[0].source == "a.md"
    assert out[0].similarity == 0.875


def test_retrieve_returns_empty_when_all_below_threshold(monkeypatch, fake_vs):
    """全部低于阈值 → 空列表。

    抓的 bug：过滤逻辑写反（把低于阈值的留下），或者返回 None
    导致调用方炸掉。
    """
    fake = fake_vs([(_doc("噪声", "x.md"), 1.9)])
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)

    assert retrieve("无关问题", top_k=1, score_threshold=0.3) == []


def test_retrieve_returns_empty_when_vectorstore_returns_nothing(monkeypatch, fake_vs):
    """向量库一条都没返回（知识库为空 / 全被 Chroma 自己过滤掉）→ 空列表，不崩。

    抓的 bug：在空列表上取 raw_results[0] 或 max(...)，抛 IndexError。
    """
    fake = fake_vs([])
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)

    assert retrieve("随便", top_k=5, score_threshold=0.3) == []


def test_retrieve_keeps_chunk_exactly_at_threshold(monkeypatch, fake_vs):
    """边界：sim 恰好等于阈值时必须保留（代码是 >= 不是 >）。

    distance=1.0 → sim=0.5，二进制精确可表示，所以能区分 >= 和 >。
    反例：distance=1.4 → sim=0.30000000000000004，比 0.3 大，
    >= 和 > 都为真，这个测试就抓不到把 >= 改成 > 的 bug。
    """
    fake = fake_vs([(_doc("边界内容", "edge.md"), 1.0)])
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)

    out = retrieve("边界", top_k=1, score_threshold=0.5)

    assert len(out) == 1
    assert out[0].similarity == 0.5


def test_retrieve_passes_top_k_through(monkeypatch, fake_vs):
    """top_k 要原样传给向量库；可用条数少于 top_k 时不补空、不崩。

    抓的 bug：① top_k 没传给底层（写死成默认值）；② 结果不足 top_k 时
    代码去补 None 或索引越界。
    """
    fake = fake_vs([(_doc("唯一一条", "one.md"), 0.25)])
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)

    out = retrieve("随便", top_k=10, score_threshold=0.3)

    assert fake.last_k == 10
    assert len(out) == 1


def test_retrieve_raises_when_vectorstore_missing(monkeypatch):
    """向量库没建 → 明确抛 RuntimeError。

    抓的 bug：把「向量库没建」静默变成「返回空列表」，
    那样用户会以为"知识库里没有相关内容"，实际是根本没建库——最难查的一类问题。
    这个用例不需要 fake_vs，因为它要的就是 get_vectorstore() 返回 None。
    """
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: None)

    with pytest.raises(RuntimeError):
        retrieve("随便")


def test_retrieve_reads_config_at_call_time(monkeypatch, fake_vs):
    """不传参数时，应读 config 的「当前值」，而不是 import 时绑死的值。

    抓的 bug：`top_k: int = TOP_K` 这种写法在函数定义时就把值算好了，
    之后改 config / 测试 monkeypatch 全部无效，改配置必须重启进程。

    注意这里 patch 的是 app.core.config 的属性，不是 retriever 里的名字：
    retriever 必须写成 `from app.core import config` + `config.TOP_K`，
    如果写成 `from app.core.config import TOP_K`，值会被拷贝，这个用例会红。
    """
    fake = fake_vs([(_doc("内容", "a.md"), 0.25)])   # sim = 1 - 0.25/2 = 0.875
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)
    monkeypatch.setattr("app.core.config.TOP_K", 2)
    monkeypatch.setattr("app.core.config.SCORE_THRESHOLD", 0.9)   # 0.875 < 0.9 → 应被过滤

    out = retrieve("不传任何参数")

    assert fake.last_k == 2, "top_k 应读到 monkeypatch 后的 config.TOP_K=2"
    assert out == [], "阈值应读到 0.9，0.875 的块被过滤"


def test_retrieve_rejects_blank_query(monkeypatch, fake_vs):
    """空 query 必须报错，不能静默返回一堆块。

    抓的 bug（2026-10-28 实测）：query='' 时 embedding 出中性向量，和所有文本
    相似度都在 0.5 附近，刚好过阈值 → 返回 4 条无关内容喂给 LLM。
    不崩、不空、不报错，是最难查的失败模式。
    """
    fake = fake_vs([(_doc("无关内容", "a.md"), 0.25)])
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)

    with pytest.raises(ValueError):
        retrieve("")
    with pytest.raises(ValueError):
        retrieve("   \n\t ")

    assert fake.last_k is None, "校验必须在碰向量库之前，否则坏输入也会白加载 2.2GB 模型"


def test_retrieve_rejects_non_str_query(monkeypatch, fake_vs):
    """None / 数字等非字符串必须抛 TypeError，同样不能进到向量库。

    抓的 bug：query=None 会在 tokenizer 内部炸出 AttributeError，
    报错指向 'NoneType' object has no attribute 'replace'，排查者根本看不出是参数问题。
    """
    fake = fake_vs([(_doc("x", "a.md"), 0.25)])
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)

    with pytest.raises(TypeError):
        retrieve(None)
    with pytest.raises(TypeError):
        retrieve(123)

    assert fake.last_k is None


def test_retrieve_rejects_out_of_range_params(monkeypatch, fake_vs):
    """top_k <= 0、threshold 越界必须报错，而不是把问题推给 Chroma 或静默放行。

    抓的 bug（2026-10-28 实测）：
      - top_k=0/-1 → Chroma 抛 TypeError("Number of requested results 0...")，
        错误来自第三方库，看不出是自己传错了；
      - threshold=-1 → 返回 5 条全部放行（兜底等于没设）；
      - threshold=2 → 静默返回 0 条，用户会以为"知识库里没这个内容"。
    后两个都是"不报错的错"，比抛异常难查得多。
    """
    fake = fake_vs([(_doc("x", "a.md"), 0.25)])
    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: fake)

    with pytest.raises(ValueError):
        retrieve("x", top_k=0)
    with pytest.raises(ValueError):
        retrieve("x", top_k=-1)
    with pytest.raises(ValueError):
        retrieve("x", score_threshold=-0.1)
    with pytest.raises(ValueError):
        retrieve("x", score_threshold=1.5)

    assert fake.last_k is None


def test_retrieve_wraps_vectorstore_failure(monkeypatch):
    """底层炸了要包成 RetrievalError，并保留原始异常链。"""
    class BoomVS:
        def similarity_search_with_score(self, query, k):
            raise ConnectionError("chroma 挂了")

    monkeypatch.setattr("app.rag.retriever.get_vectorstore", lambda: BoomVS())

    with pytest.raises(RetrievalError) as exc_info:
        retrieve("useState")  ##随机的提问
    assert isinstance(exc_info.value.__cause__,  ConnectionError),"必须保留原始异常链"
"""共享测试夹具 —— 放在 conftest.py 里的 fixture 不用 import，pytest 自动注入。

FakeVectorStore 只实现 retrieve 真正会调到的那一个方法。
方法名和参数名必须照抄 retriever.py 里的真实调用：
    vs.similarity_search_with_score(query=query, k=top_k)
（真实调用用的是关键字参数，所以这里也必须叫 query 和 k）
"""
import pytest


class FakeVectorStore:
    """测试替身：喂什么就返回什么，不碰真实 Chroma、不加载 embedding 模型。"""

    def __init__(self, results):
        self.results = results
        self.last_k = None  # 记录被调用时的 k，方便断言「top_k 有没有原样传下去」

    def similarity_search_with_score(self, query, k):
        self.last_k = k
        return self.results


@pytest.fixture
def fake_vs():
    """工厂夹具：fake_vs([(Document, distance), ...]) -> 假向量库实例。

    做成工厂（返回函数而不是实例），是因为不同用例要喂不同数据，
    一个替身就能服务所有场景，不用为每个用例写一个新 Fake 类。
    """

    def _make(results):
        return FakeVectorStore(results)

    return _make

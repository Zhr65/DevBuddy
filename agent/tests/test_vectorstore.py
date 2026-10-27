"""
vectorstore 的单例 / 缓存相关测试。

核心要守护的契约：
  - get_embeddings() 是进程内单例（@lru_cache(maxsize=1)），不能每次查询都重载 2.2GB 模型（债 #4）
"""
from app.rag import vectorstore


def test_get_embeddings_is_cached_within_process(tmp_path, monkeypatch):
    """
    债 #4：get_embeddings 进程内只构造一次 HuggingFaceEmbeddings。

    验证手段：用假工厂替换真模型构造（避免真加载 2.2GB），并造一个假的
    权重路径绕过 existence 检查，只测"是否只构造一次 + 是否返回同一实例"。
    """
    # 1) 造假的模型权重路径，绕过真实 2.2GB 模型的 existence 检查
    fake_model_dir = tmp_path / "bge-m3"
    fake_model_dir.mkdir()
    (fake_model_dir / "pytorch_model.bin").write_text("fake")
    monkeypatch.setattr(vectorstore, "BGE_M3_LOCAL_PATH", fake_model_dir)

    # 2) 把 HuggingFaceEmbeddings 换成计数器工厂，避免真加载
    calls = {"n": 0}

    class FakeEmbeddings:
        pass

    def fake_factory(*args, **kwargs):
        calls["n"] += 1
        return FakeEmbeddings()

    monkeypatch.setattr(vectorstore, "HuggingFaceEmbeddings", fake_factory)

    # 3) 清缓存，从干净状态测
    vectorstore.get_embeddings.cache_clear()
    try:
        e1 = vectorstore.get_embeddings()
        e2 = vectorstore.get_embeddings()
    finally:
        vectorstore.get_embeddings.cache_clear()

    assert calls["n"] == 1, f"应只构造 1 次，实际 {calls['n']} 次"
    assert e1 is e2, "两次调用应返回同一实例（单例）"

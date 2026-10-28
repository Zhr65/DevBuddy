"""
vectorstore.py —— Chroma 向量库封装

核心概念速记：
─────────────────────────────────
- Embedding：把文字变成长度 1024 的数字数组（bge-m3 输出）
- Collection：Chroma 里的"表"，一个 collection 存一批向量
- PersistDirectory：Chroma 把向量存到磁盘的位置，下次启动直接读，不用重算

我们为什么选 Chroma？
  1. 纯 Python，pip install 就能跑，不用 Docker
  2. LangChain 原生集成，from_documents 一行入库
  3. 支持 metadata filter（以后想按 source 过滤会用到）
"""
from functools import lru_cache
import logging
from pathlib import Path
from typing import Optional

import chromadb
from chromadb.config import Settings
from langchain_chroma import Chroma
from langchain_core.documents import Document
from langchain_huggingface import HuggingFaceEmbeddings

from app.core.config import BGE_M3_LOCAL_PATH, CHROMA_PERSIST_DIR

logger = logging.getLogger(__name__)


# Collection 名 —— 就像数据库里的表名
COLLECTION_NAME = "react_docs"


@lru_cache(maxsize=1)
def get_embeddings() -> HuggingFaceEmbeddings:
    """
    拿 embedding 实例 —— 本地自托管 BGE-M3，整个应用共享一个就行。

    @lru_cache(maxsize=1)：进程内只加载一次 2.2GB 权重，之后复用同一实例。
    满足"无参数 + 纯工厂"两个前提，所以 lru_cache 是正解。

    和之前硅基流动 API 版的区别：
      - 向量在本地算：零边际成本、不依赖网络和 API key
      - 用之前要先把权重下载到 BGE_M3_LOCAL_PATH（约 2.2GB）
      - CPU 能跑（本机 torch 是 CPU 版），大批量灌库会慢，属正常现象
    """
    if not (BGE_M3_LOCAL_PATH / "pytorch_model.bin").exists():
        raise ValueError(
            f"模型权重不在 {BGE_M3_LOCAL_PATH}！\n"
            "先把权重下下来（约 2.3GB，走魔搭镜像）：\n"
            '  curl -sL -o pytorch_model.bin "https://www.modelscope.cn/api/v1/models/BAAI/bge-m3/repo?Revision=master&FilePath=pytorch_model.bin"\n'
            "（其余 tokenizer/配置文件同理，或找我要一键脚本）\n"
            "或者设环境变量 BGE_M3_LOCAL_PATH 指向已有的模型副本"
        )
    return HuggingFaceEmbeddings(
        model_name=str(BGE_M3_LOCAL_PATH),
        encode_kwargs={"normalize_embeddings": True},  # bge-m3 输出已归一化，显式声明保平安
    )


def get_chroma_client(persist_dir: Path = CHROMA_PERSIST_DIR) -> chromadb.PersistentClient:
    """
    拿 Chroma 持久化客户端。
    PersistentClient = 存磁盘，重启不丢；EphemeralClient = 内存，重启就没了。
    """
    persist_dir.mkdir(parents=True, exist_ok=True)
    return chromadb.PersistentClient(
        path=str(persist_dir),
        settings=Settings(anonymized_telemetry=False),  # 关掉遥测，省流量
    )


def build_vectorstore(
    documents: list[Document],
    persist_dir: Path = CHROMA_PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
    rebuild: bool = False,
) -> Chroma:
    """
    把切块后的文档写入 Chroma。

    参数:
        documents:      loader 切好的 Document 列表
        persist_dir:    向量存磁盘的路径
        collection_name: collection 名
        rebuild:        True=删掉旧数据重建；False=已存在就跳过（防重复写）

    返回:
        LangChain Chroma 实例 —— retriever 会用它来相似度搜索
    """
    embeddings = get_embeddings()
    client = get_chroma_client(persist_dir)

    # 看看 collection 存在不存在
    collections = [c.name for c in client.list_collections()]
    exists = collection_name in collections

    if exists and not rebuild:
        logger.info("collection %s 已存在，跳过入库（rebuild=True 可强制重建）", collection_name)
    else:
        if exists and rebuild:
            client.delete_collection(collection_name)
            logger.info("已删除旧 collection %s", collection_name)

        logger.info("正在把 %d 块文档写入 Chroma...", len(documents))
        # from_documents 会自动做两件事：
        #   1. 调用 embeddings.embed_documents() 批量算向量
        #   2. 把向量 + 原文 + metadata 一起塞进 collection
        vs = Chroma.from_documents(
            documents=documents,
            embedding=embeddings,
            collection_name=collection_name,
            client=client,
            persist_directory=str(persist_dir),
        )
        logger.info("入库完成 collection=%s 共 %d 条", collection_name, vs._collection.count())
        return vs

    # 已存在且不想重建 —— 直接加载
    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        client=client,
        persist_directory=str(persist_dir),
    )


def get_vectorstore(
    persist_dir: Path = CHROMA_PERSIST_DIR,
    collection_name: str = COLLECTION_NAME,
) -> Optional[Chroma]:
    """
    拿已有的向量库。如果还没建就返回 None。
    retriever 和后续 Agent 都会调这个函数来拿 vs。
    """
    embeddings = get_embeddings()
    client = get_chroma_client(persist_dir)

    collections = [c.name for c in client.list_collections()]
    if collection_name not in collections:
        logger.warning("collection %s 还不存在，先跑 build_vectorstore() 吧", collection_name)
        return None

    return Chroma(
        collection_name=collection_name,
        embedding_function=embeddings,
        client=client,
        persist_directory=str(persist_dir),
    )


if __name__ == "__main__":
    # 直接运行可以一键重建向量库
    from app.rag.loader import load_and_split

    chunks = load_and_split()
    vs = build_vectorstore(chunks, rebuild=True)
    print(f"\n向量库就绪，共 {vs._collection.count()} 条向量")

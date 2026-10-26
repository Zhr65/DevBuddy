from dataclasses import dataclass


@dataclass(frozen=True)
class RetrievedChunk:
    """检索结果的显式契约:内容 + 出处 + 相似度"""

    content: str
    source: str
    similarity: float

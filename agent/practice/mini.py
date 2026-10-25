from dataclasses import dataclass
from langchain_core.documents import Document

@dataclass
class RetrieverChunk:
    document: Document
    score: float
    distance: float | None = None
    source: str = ""
    rank: int = 0
    rerank_score: float | None = None
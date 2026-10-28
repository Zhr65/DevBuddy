"""
loader.py —— 文档加载 & 切块

为什么要两步切？
─────────────────────────────────
Markdown 文档有标题结构（# / ## / ###），如果直接按字符数切，
表格、代码块经常被拦腰截断，或者脱离了所属的章节标题，
检索出来后 AI 看上下文会懵。

策略：
  第 1 步：MarkdownHeaderTextSplitter 按标题层级切
           → 每个 Document 的 metadata 里会带上 {"header": "#useState > ##Reference"}
  第 2 步：RecursiveCharacterTextSplitter 补刀
           → 把上一步出来的大块继续切到 500 字以内
           → chunk_overlap=50 保证相邻块有重叠，不会丢语义
"""
import logging
from pathlib import Path
from typing import List

from langchain_core.documents import Document
from langchain_text_splitters import (
    MarkdownHeaderTextSplitter,
    RecursiveCharacterTextSplitter,
)

logger = logging.getLogger(__name__)

from app.core.config import CHUNK_OVERLAP, CHUNK_SIZE, DATA_DIR


# Markdown 的标题层级 —— 我们关心 H1 到 H3
HEADERS_TO_SPLIT_ON = [
    ("#", "level1"),    # 一级标题，比如 # useState
    ("##", "level2"),   # 二级标题，比如 ## Reference
    ("###", "level3"),  # 三级标题，比如 ### useState(initialState)
]


def load_markdown_files(data_dir: Path = DATA_DIR) -> List[str]:
    """
    读进目录下所有 .md 文件的原文。
    返回: [文件全文, 文件全文, ...] —— 不带路径信息，路径留给 metadata
    """
    raw_texts = []
    md_files = sorted(data_dir.glob("*.md"))  # 排序 = 每次顺序一致，方便调试

    if not md_files:
        raise FileNotFoundError(f"在 {data_dir} 下没找到任何 .md 文件")

    for f in md_files:
        content = f.read_text(encoding="utf-8")
        raw_texts.append(content)

    logger.info("读进 %d 篇 Markdown 文件，共 %d 字符", len(md_files), sum(len(t) for t in raw_texts))
    return raw_texts, md_files


def split_documents(
    raw_texts: List[str],
    source_files: List[Path],
) -> List[Document]:
    """
    两步切块。

    参数:
        raw_texts:     load_markdown_files 返回的文件原文列表
        source_files:  对应的文件 Path 对象列表 —— 用来写 metadata["source"]

    返回:
        切好的 LangChain Document 列表
        每个 Document 自带 metadata: {source: "useState.md", level1: "...", level2: "...", ...}
    """
    # ----- 第 1 步：按标题切 -----
    header_splitter = MarkdownHeaderTextSplitter(
        headers_to_split_on=HEADERS_TO_SPLIT_ON,
        return_each_line=False,
    )

    # 每个文件独立切，这样可以把文件名写进 metadata
    header_chunks: List[Document] = []
    for text, src in zip(raw_texts, source_files):
        chunks = header_splitter.split_text(text)
        # 给每个块补上 source 字段
        for c in chunks:
            c.metadata["source"] = src.name  # 比如 "useState.md"
        header_chunks.extend(chunks)

    logger.info("第 1 步（按标题切）得到 %d 块", len(header_chunks))

    # ----- 第 2 步：按字符数补刀 -----
    char_splitter = RecursiveCharacterTextSplitter(
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
        length_function=len,            # 按字符数算（中文友好）
        separators=["\n\n", "\n", "。", "！", "？", " ", ""],  # 优先在段落/句号/空格处断
    )

    final_chunks = char_splitter.split_documents(header_chunks)
    logger.info("第 2 步（按字符补刀）得到 %d 块", len(final_chunks))

    return final_chunks


def load_and_split(data_dir: Path = DATA_DIR) -> List[Document]:
    """一站式：读文件 → 切块 → 返回"""
    raw_texts, source_files = load_markdown_files(data_dir)
    return split_documents(raw_texts, source_files)


if __name__ == "__main__":
    # 直接运行此文件可以测试切块效果
    chunks = load_and_split()
    print(f"\n总共 {len(chunks)} 块\n")
    # 打印前 3 块看看效果
    for i, c in enumerate(chunks[:3]):
        print(f"--- chunk {i} ---")
        print(f"metadata: {c.metadata}")
        print(f"内容前 120 字: {c.page_content[:120]}...\n")

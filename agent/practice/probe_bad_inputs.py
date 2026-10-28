"""探测：retrieve 遇到坏输入的真实行为（不校验的话会怎样）

目的：为「防御性编程」提供依据 —— 先看现状有多糟，再决定每个参数怎么防。
跑法：python -m practice.probe_bad_inputs
"""
from app.rag.retriever import retrieve

CASES = [
    ("query=None", {"query": None}),
    ("query=''", {"query": ""}),
    ("query='   '", {"query": "   "}),
    ("top_k=0", {"query": "useState", "top_k": 0}),
    ("top_k=-1", {"query": "useState", "top_k": -1}),
    ("threshold=-1", {"query": "useState", "score_threshold": -1}),
    ("threshold=2", {"query": "useState", "score_threshold": 2}),
]


def main():
    for name, kwargs in CASES:
        try:
            out = retrieve(**kwargs)
            print(f"[{name}] -> 返回 {len(out)} 条  {'⚠️ 静默放行' if out else '（空）'}")
        except Exception as e:
            print(f"[{name}] -> {type(e).__name__}: {str(e)[:100]}")


if __name__ == "__main__":
    main()

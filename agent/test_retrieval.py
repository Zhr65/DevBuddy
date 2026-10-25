"""
test_retrieval.py —— M1 验收测试

验收标准：5 个典型问题，top-1 命中正确段落 ≥ 4 个就算合格
如果不通过 → 调 CHUNK_SIZE / CHUNK_OVERLAP / SCORE_THRESHOLD，别先加 rerank
"""
from app.rag.retriever import retrieve


# 5 个典型问题 + 预期命中的 source 文件
TEST_CASES = [
    {
        "query": "useState hook 是干什么的？怎么声明一个状态变量？",
        "expected_source": "useState.md",
        "hint": "应该命中 useState.md 的前几段或 Reference 部分",
    },
    {
        "query": "useEffect 什么时候触发？依赖数组 dependency array 怎么写？",
        "expected_source": "useEffect.md",
        "hint": "应该命中 useEffect.md 里关于 dependency 的段落",
    },
    {
        "query": "React Context 怎么用？解决什么问题？",
        "expected_source": "useContext.md",
        "hint": "应该命中 useContext.md 或 useContext 相关段落",
    },
    {
        "query": "useRef 和 useState 有什么区别？什么时候用 ref？",
        "expected_source": "useRef.md",
        "hint": "应该命中 useRef.md",
    },
    {
        "query": "父组件怎么把数据传给子组件？props 怎么传递和读取？",
        "expected_source": "passing-props.md",
        "hint": "应该命中 passing-props.md",
    },
]


def run_tests():
    passed = 0
    total = len(TEST_CASES)

    for i, case in enumerate(TEST_CASES):
        print(f"\n{'='*60}")
        print(f"📝 问题 {i+1}/{total}: {case['query']}")
        print(f"   预期命中: {case['expected_source']}")
        print(f"   💡 {case['hint']}")
        print('-' * 60)

        results = retrieve(case["query"])

        if not results:
            print(f"   ❌ 检索结果为空（没翻到书）")
            continue

        # 只看 top-1
        top1 = results[0]
        top1_source = top1.metadata.get("source", "未知")
        top1_sim = top1.metadata.get("similarity", 0)

        if top1_source == case["expected_source"]:
            print(f"   ✅ PASS  top-1 source={top1_source}  相似度={top1_sim}")
            passed += 1
        else:
            print(f"   ❌ FAIL  top-1 source={top1_source}(相似度={top1_sim})"
                  f"  但预期 {case['expected_source']}")
            # 打印 top-3 帮助诊断
            print(f"   top-3 结果:")
            for j, doc in enumerate(results[:3]):
                src = doc.metadata.get("source", "?")
                sim = doc.metadata.get("similarity", "?")
                preview = doc.page_content[:80].replace("\n", " ")
                print(f"     [{j}] {src}(sim={sim}) → {preview}...")

    # ---- 总结 ----
    print(f"\n{'='*60}")
    print(f"📊 验收结果: {passed}/{total} 问题 top-1 命中正确")
    if passed >= 4:
        print(f"   🎉 合格！RAG 管线通了，可以进 M2（FastAPI）")
    else:
        print(f"   ⚠️  不合格，通过率 {passed/total*100:.0f}%")
        print(f"   建议：调大 CHUNK_OVERLAP 或降低 SCORE_THRESHOLD 再试试")
    print(f"{'='*60}")


if __name__ == "__main__":
    run_tests()

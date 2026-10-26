"""手推 attention 的验证脚本（对应 D2 基础线任务）

跑法（在 agent/ 目录下）：
    D:\\python\\python312\\python.exe -m practice.attention_manual

三段内容：
1. 手推样例：3 个 token, d_k=2,逐行输出 分数 / 权重 / 输出
2. 平移不变性：softmax 对"所有分数同时加常数"免疫
3. 换数字自测：q2 换成 [2,1]、k3 换成 [1,2]
"""
import math


def softmax(xs):
    """数值稳定的 softmax：先减最大值，避免 exp 溢出。"""
    m = max(xs)
    es = [math.exp(x - m) for x in xs]
    s = sum(es)
    return [e / s for e in es]


def attention_row(q, K, V, d_k):
    """算一行的 attention：返回 (分数, 权重, 输出向量)。"""
    scores = [sum(q[t] * k[t] for t in range(len(q))) / math.sqrt(d_k) for k in K]
    weights = softmax(scores)
    out = [
        sum(weights[j] * v[t] for j, v in enumerate(V))
        for t in range(len(q))
    ]
    return scores, weights, out


def main():
    Q = [[1, 0], [0, 1], [1, 1]]
    K = [[1, 0], [1, 1], [0, 1]]
    V = [[1, 0], [0, 1], [1, 1]]
    d_k = 2

    print("=== 1. 手推样例（3 token, d_k=2）===")
    for i, q in enumerate(Q):
        s, w, o = attention_row(q, K, V, d_k)
        print(f"q{i + 1} scores {[round(x, 4) for x in s]}"
              f" | weights {[round(x, 4) for x in w]}"
              f" | out {[round(x, 4) for x in o]}")

    print()
    print("=== 2. softmax 平移不变：所有分数同时 +0.7071，权重不变 ===")
    a = softmax([0, 0.7071, 0.7071])
    b = softmax([0.7071, 1.4142, 1.4142])
    print("原权重     ", [round(x, 6) for x in a])
    print("整体平移后 ", [round(x, 6) for x in b])
    print("完全相同:", a == b, "→ softmax 只看差距，不看绝对大小")

    print()
    print("=== 3. 换数字自测：q2=[2,1], k3=[1,2] ===")
    K2 = [[1, 0], [1, 1], [1, 2]]
    s, w, o = attention_row([2, 1], K2, V, d_k)
    print("scores ", [round(x, 4) for x in s])
    print("weights", [round(x, 4) for x in w], "← k3 从并列 0.4011 涨到 0.576")
    print("out    ", [round(x, 4) for x in o], "← 距最大值的差全部拉开，softmax 更尖锐")


if __name__ == "__main__":
    main()

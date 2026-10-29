# -*- coding: utf-8 -*-
"""
模块 4：RAG 检索增强生成（Retrieval-Augmented Generation）
====================================
模块 1-3 的 AI 都在"闭卷考试"：只靠训练时记住的东西回答。
RAG = 开卷考试：先翻资料（检索），再答题（生成）。

三大步（RAG 的全部骨架）：
    1. 建知识库：把资料切成小块，每块算出"语义坐标"（向量）
    2. 检索：用户的问题也算坐标，找最相似的几块
    3. 增强生成：把找到的块塞进 prompt，AI 照着资料回答

核心认知：
    - 向量 = 文字的"语义坐标"，意思越近的两句话，坐标越靠近
    - 相似度 = 衡量两段文字有多像，打一个 0~1 的分
    - RAG 没有魔法：就是"搜索 + 塞 prompt"，搜索和工具调用一样
      是【你写的代码】在干活，AI 只负责读资料、开口说话

本文件已是真项目做法：
    聊天模型走 apihub，embedding 走硅基流动（免费额度）。
    真·向量检索 + 余弦相似度 —— 和生产级 RAG 同一套路。

实验1：年假有几天？       → 检索得分高，AI 照资料回答
实验2：发票怎么报销？     → 命中另一块
实验3：1+1等于几？        → 检索得分低于阈值，AI 不看资料直接答
"""

import math
import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ===============================================================
# 配置区
# ===============================================================
# 密钥从 agent/.env 读，不写死在代码里（本文件要进公开仓库）
# 独立运行（python practice/agent_rag.py）时 __file__ 在 practice/，往上两层才是 agent/
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

# 真项目常见分工：聊天一个站，embedding 另一个站，各配一个 client
client = OpenAI(              # 聊天模型：apihub
    api_key=os.getenv("AGNES_API_KEY", ""),
    base_url="https://apihub.agnes-ai.com/v1",
)
embed_client = OpenAI(        # embedding 模型：硅基流动（免费）
    api_key=os.getenv("SILICONFLOW_API_KEY", ""),
    base_url="https://api.siliconflow.cn/v1",
)
MODEL = "agnes-2.5-flash"
EMBED_MODEL = "BAAI/bge-m3"   # 硅基流动的免费 embedding 模型，1024 维
SCORE_THRESHOLD = 0.3         # 检索门槛：最高分低于它 = 没翻到书


# ===============================================================
# 第 1 部分：知识库 —— AI 训练时没见过的"私有资料"
# ===============================================================
# 真实项目里这里是一个公司文档/手册/产品说明书。
# 我们虚构一份"员工手册"，注意 AI 的训练数据里绝不会有它。
KB = [
    "员工入职满一年享有5天带薪年假，满三年增加到10天，年假需提前3天向主管申请。",
    "报销流程：每月最后一天前提交发票照片到财务系统，单笔超过200元需要主管审批，超过2000元需要总监审批。",
    "考勤制度：工作时间为9点到18点，午休1小时，一个月内迟到3次按旷工半天处理。",
]

# ===============================================================
# 第 2 部分：向量化 —— 把文字变成可比较的数学对象
# ===============================================================
def embed(text: str) -> list:
    """真向量化：调 embedding API，把一句话变成 1024 个数字。
    向量 = 文字的'语义坐标'：意思越近的两句话，这串数字越接近。
    注意它是把【整句话的语义】压成一串数字，不是关键词匹配 ——
    '怎么请假' 和 '年假有几天' 字面几乎不重合，向量却很近。
    这就是语义检索比关键词匹配强的地方，也是真 RAG 的价值。
    """
    resp = embed_client.embeddings.create(model=EMBED_MODEL, input=text)
    return resp.data[0].embedding


def similarity(a: list, b: list) -> float:
    """余弦相似度：比较两个向量'方向'的夹角，1 同向最像，0 垂直无关。
    数学就两步：点积（对应位置相乘再求和）÷ 两个向量各自长度之积。
    小例子：a=[1,2]、b=[2,4] 方向相同
        点积 = 1*2 + 2*4 = 10
        长度 = √5 和 √20，乘积 = √100 = 10
        相似度 = 10 / 10 = 1.0   ← 完全同向
    """
    dot = sum(x * y for x, y in zip(a, b))      # 点积：zip 配对相乘再求和
    norm_a = math.sqrt(sum(x * x for x in a))   # 向量 a 的长度
    norm_b = math.sqrt(sum(x * x for x in b))   # 向量 b 的长度
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


# ===============================================================
# 第 3 部分：检索 —— RAG 的"翻书"动作
# ===============================================================
# 关键知识点：知识库的向量是【提前算好】的（入库时算一次），
# 不是每次提问都重算 —— 所以这行代码在循环外面！
# （真项目入库会批量算：embeddings.create(input=KB) 一次传整列表，更省）
KB_EMBEDDED = [(chunk, embed(chunk)) for chunk in KB]

'''问题变成向量'''
def search(question: str, top_k: int = 2) -> list:
    """拿问题去知识库里翻书：算分、排序、取最像的 top_k 块。"""
    q_vec = embed(question)

    '''逐个打分'''
    scored = []
    for chunk, vec in KB_EMBEDDED:
        score = similarity(q_vec, vec)
        scored.append((chunk, score))

    # 按得分从高到低排，key=lambda 告诉 sort 按每项的[1]（得分）比
    scored.sort(key=lambda x: x[1], reverse=True)
    hits = scored[:top_k]

    for chunk, score in hits:
        print(f"  [检索命中] 得分 {score:.2f} | {chunk[:18]}……")
    return hits


# ===============================================================
# 第 4 部分：回答 —— 检索到的资料塞进 prompt（开卷答题）
# ===============================================================
def answer(user_input: str) -> str:
    # ① 检索：先翻书
    hits = search(user_input)
    context = "\n".join(chunk for chunk, _ in hits)

    # ② 没翻到书（最高分低于阈值）：跳过资料，直接问
    # 真向量的得分几乎不会恰好等于 0，只能设门槛 —— SCORE_THRESHOLD
    # 是真项目必调的超参数：太低会被无关资料带偏，太高又老检索不到
    if hits[0][1] < SCORE_THRESHOLD:
        prompt = user_input
    else:
        # ③ 增强生成：把"小抄"和问题打包塞给 AI
        prompt = (
            f"请只依据以下资料回答问题。"
            f"如果资料里没有答案，就说明资料里没有，不要瞎编。\n\n"
            f"【资料】\n{context}\n\n"
            f"【问题】{user_input}"
        )

    resp = client.chat.completions.create(
        model=MODEL,
        messages=[
            {"role": "system", "content": "你是公司员工手册助手，回答简洁。"},
            {"role": "user", "content": prompt},
        ],
    )
    return resp.choices[0].message.content


# ===============================================================
# 第 5 部分：CLI 循环 —— 骨架照旧
# ===============================================================
def main():
    print("=== 模块4 RAG 员工手册助手（q 退出）===\n")
    while True:
        user_input = input("你> ").strip()
        if user_input.lower() == "q":
            break
        if not user_input:
            continue
        print("AI>", answer(user_input), "\n")


if __name__ == "__main__":
    main()

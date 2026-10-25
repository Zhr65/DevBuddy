# -*- coding: utf-8 -*-
"""
模块 5：生产化 —— 从"能跑的玩具"到"能给人用的东西"
====================================
前四个模块的零件各是各的，这一课把它们组装成完整 Agent，并补上
生产环境必做的三件工程事，共四件套：

    1. .env 管 key：代码里不再出现密钥（防上传 GitHub 泄露）
    2. 流式输出：打字机效果，一个字一个字往外蹦（不再干等十几秒）
    3. 出错重试：网络抖一下不崩，自动重试最多 3 次
    4. 组装：工具(模块3) + RAG(模块4) + 多轮记忆(模块1) = 真 Agent

组装的核心思想：
    把"查员工手册"也注册成一个工具！AI 觉得需要资料时，
    自己决定调用 search_kb —— RAG 不再是"每次都检索"，
    而是"AI 判断需要时才检索"。这就是 function calling + RAG 的正宗组合。

运行前（一次性准备）：
    1. 终端执行：pip install python-dotenv
    2. 打开同目录 .env 文件，填好两个 key
运行：python agent_prod.py
实验1：北京天气怎么样？   → 调 get_weather 工具
实验2：年假有几天？       → 调 search_kb 工具翻手册，再回答
实验3：1+1等于几？        → 不调工具，直接答
实验4：先问北京天气，再问"那上海呢？" → 记得上文（多轮记忆）
"""

import json
import math
import os
import time

from dotenv import load_dotenv
from openai import OpenAI

# ===============================================================
# 四件套之 1：.env 管 key
# ===============================================================
# load_dotenv()：读取同目录的 .env 文件，把里面的键值对塞进环境变量
# 之后再由 os.getenv("名字") 取用 —— 代码里永远看不到密钥本体
# 顺序很重要：必须先 load_dotenv()，再创建 client
load_dotenv()

client = OpenAI(          # 聊天模型：apihub
    api_key=os.getenv("AGNES_API_KEY"),
    base_url="https://apihub.agnes-ai.com/v1",
)
embed_client = OpenAI(    # embedding 模型：硅基流动
    api_key=os.getenv("SILICONFLOW_API_KEY"),
    base_url="https://api.siliconflow.cn/v1",
)
MODEL = "agnes-2.5-flash"
EMBED_MODEL = "BAAI/bge-m3"
SCORE_THRESHOLD = 0.3


# ===============================================================
# 第 1 部分：RAG 零件 —— 从模块 4 原样搬来，一行没改
# ===============================================================
KB = [
    "员工入职满一年享有5天带薪年假，满三年增加到10天，年假需提前3天向主管申请。",
    "报销流程：每月最后一天前提交发票照片到财务系统，单笔超过200元需要主管审批，超过2000元需要总监审批。",
    "考勤制度：工作时间为9点到18点，午休1小时，一个月内迟到3次按旷工半天处理。",
]

def embed(text: str) -> list:               
    """文字 -> 1024 个数字的语义坐标（模块 4 讲过）"""
    resp = embed_client.embeddings.create(model=EMBED_MODEL, input=text)       # 调用硅基流动模型
    return resp.data[0].embedding          # 取第一个元素的 embedding

def similarity(a: list, b: list) -> float:
    """余弦相似度：两个坐标有多像（模块 4 讲过）"""
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = math.sqrt(sum(x * x for x in a))
    norm_b = math.sqrt(sum(x * x for x in b))
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)

KB_EMBEDDED = [(chunk, embed(chunk)) for chunk in KB]   # 入库时算一次

def search(question: str, top_k: int = 2) -> list:    
    """翻书：算分、排序、取前 top_k 块（模块 4 讲过）"""
    q_vec = embed(question)          # 把问题转换为语义坐标
    scored = []
    for chunk, vec in KB_EMBEDDED:       # 遍历知识库里的每一条
        # 计算问题和每一条的相似度
        score = similarity(q_vec, vec)
        scored.append((chunk, score))
    scored.sort(key=lambda x: x[1], reverse=True)
    return scored[:top_k]


# ===============================================================
# 第 2 部分：普通工具 —— 模块 3 的老朋友
# ===============================================================
def get_weather(city: str) -> str:
    """假装查天气"""
    return f"{city}今天晴，25 度，微风，适合出门。"


# ===============================================================
# 第 3 部分：组装点！把 RAG 包装成一个工具
# ===============================================================
# 看清楚：search_kb 就是个普通函数，只是函数体内调了模块 4 的 search()。
# 对 AI 来说它和 get_weather 没有任何区别 —— 都是注册表里的一个工具。
# 这就是"组装"：没有新魔法，只是把旧零件插进同一个插座。
def search_kb(query: str) -> str:
    """在员工手册知识库里检索，返回最相关的资料文本。"""
    hits = search(query, top_k=2)
    if hits[0][1] < SCORE_THRESHOLD:
        return "（知识库里没有相关资料）"   # 兜底：别拿无关资料糊弄 AI
    return "\n".join(chunk for chunk, _ in hits)


# 工具注册表：两个工具并存，AI 自己挑
TOOLS = {
    "get_weather": get_weather,
    "search_kb": search_kb,
}

# 两份工具说明书（模块 3 的 JSON Schema 格式）
TOOLS_SCHEMA = [
    {
        "type": "function",
        "function": {
            "name": "get_weather",
            "description": "查询某个城市今天的天气。当用户问到天气时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "city": {"type": "string", "description": "城市名字，比如：北京"}
                },
                "required": ["city"],
            },
        },
    },
    {
        "type": "function",
        "function": {
            "name": "search_kb",
            "description": "在员工手册知识库中检索资料（年假、报销、考勤等制度问题）。"
                           "当用户问到公司制度相关问题时调用。",
            "parameters": {
                "type": "object",
                "properties": {
                    "query": {"type": "string", "description": "要检索的问题，比如：年假有几天"}
                },
                "required": ["query"],
            },
        },
    },
]


# ===============================================================
# 第 4 部分：call_llm —— 四件套之 2（流式）+ 3（重试）都在这
# ===============================================================
# 流式的真相：AI 的回答不是一次性到货，是切成几百节"车厢"（chunk）
# 源源不断送来。每节车厢里可能装：
#   - 文字片段（delta.content）→ 立刻打印上屏，用户看到打字机效果
#   - 工具请求的零件（delta.tool_calls）→ 名字、参数是分批到的，
#     必须攒齐再组装（这就是 tool_acc 干的事）
def call_llm(messages: list):
    """生产级 LLM 调用：流式打印 + 自动重试 + 拼装工具请求。
    返回 (text, tool_calls)：text=AI说的话；tool_calls=工具请求列表（没有则 None）
    """
    for attempt in range(3):                       # 四件套之 3：最多重试 3 次
        try:
            stream = client.chat.completions.create(
                model=MODEL,
                messages=messages,
                tools=TOOLS_SCHEMA,
                stream=True,                       # 四件套之 2：开流式
                temperature=0.3,
            )
            text_parts = []        # 攒文字
            tool_acc = {}          # 攒工具零件：{车厢序号: {"id","name","args"}}

            for chunk in stream:
                if not chunk.choices:
                    continue
                delta = chunk.choices[0].delta
                if delta.content:                          # 文字车厢到货
                    print(delta.content, end="", flush=True)  # flush=立刻显示，不等缓冲
                    text_parts.append(delta.content)
                if delta.tool_calls:                       # 工具零件到货（可能分几批）
                    for tc in delta.tool_calls:            # 每个工具请求可能有多个参数（不同的零件）
                        slot = tool_acc.setdefault(
                            tc.index, {"id": "", "name": "", "args": ""}
                        )        # 每个工具请求的零件，都用 index 标记
                        if tc.id:         # 工具请求的 id 是唯一的，每个零件都有一个
                            slot["id"] = tc.id
                        if tc.function and tc.function.name:           # 工具请求的 name 是唯一的，每个零件都有一个
                            slot["name"] += tc.function.name
                        if tc.function and tc.function.arguments:      # 工具请求的 arguments 是分批到的，每个零件都有一个
                            slot["args"] += tc.function.arguments  # 参数是拼出来的！

            print()    # 流式打印完补个换行，别让后面的日志贴在答案上

            text = "".join(text_parts)    # 拼成完整文字
            if not tool_acc:              # 没有工具请求
                return text, None         # 直接返回文字(没有工具请求)

            # 攒齐零件，组装成标准格式（和非流式的 tool_calls 结构一致）
            tool_calls = [
                {
                    "id": slot["id"],
                    "type": "function",
                    "function": {"name": slot["name"], "arguments": slot["args"]},
                }
                for _, slot in sorted(tool_acc.items())       # 按 index 排序，确保工具请求的顺序
            ]
            return text, tool_calls

        except Exception as e:
            print(f"  [网络出错，正在重试 {attempt + 1}/3] {e}")
            time.sleep(1)      # 等 1 秒再试，给网络喘口气

    raise RuntimeError("重试 3 次仍失败，请检查网络和 key")


# ===============================================================
# 第 5 部分：ReAct 循环 —— 骨架同模块 3，两处小差异
# ===============================================================
# 差异1：messages 在函数外面，多轮对话共享记忆本（模块 1 的 chat.py 回归）
# 差异2：流式下 SDK 不帮我们拼 assistant 对象，记账要自己拼 dict
messages = [
    {"role": "system", "content": "你是一个既能查天气、又能查员工手册的中文助手，回答简洁。"},
]


def run_agent(user_input: str, max_steps: int = 5) -> str:           
    messages.append({"role": "user", "content": user_input})      # 记账：用户输入

    for step in range(max_steps):                      # 最多 5 次

        text, tool_calls = call_llm(messages)            # 调用 LLM，获取文字和工具请求

        if tool_calls:                  # 有工具请求
            # AI 想调工具：把"带工具请求的话"记进记忆本（流式下自己拼 dict）
            messages.append({
                "role": "assistant",
                "content": text or None,
                "tool_calls": tool_calls,
            })
            for tc in tool_calls:          # 每个工具请求可能有多个参数（不同的零件）
                tool_name = tc["function"]["name"]          # dict 取值用 [""]，
                args = json.loads(tc["function"]["arguments"])  # 解析参数为 dict

                print(f"  [Agent 调用工具] {tool_name}({args})")
                result = TOOLS[tool_name](**args)           # 真正干活的永远是我们
                print(f"  [工具返回] {result}")

                messages.append({
                    "role": "tool",
                    "tool_call_id": tc["id"],               # 快递单号对账
                    "content": result,
                })
            continue   # 转下一圈：AI 看到结果，给出真正回答

        else:
            # 最终回答（已在 call_llm 里流式打完屏，这里只记账）
            messages.append({"role": "assistant", "content": text})
            return text

    return "（达到最大步数 5，强制停止）"


# ===============================================================
# 第 6 部分：CLI —— 加了个 /history 彩蛋，随时看 AI 的记忆本
# ===============================================================
def main():
    print("=== 模块5 生产级 Agent（q 退出 / history 看记忆）===\n")
    while True:
        user_input = input("你> ").strip()
        if user_input.lower() == "q":
            break
        if user_input.lower() == "history":
            for m in messages:
                brief = str(m.get("content"))[:40]
                print(f"  [{m['role']}] {brief}")
            continue
        if not user_input:
            continue
        run_agent(user_input)   # 注意：流式已在 call_llm 里上屏，这里不再打印返回值
        print("\n")


if __name__ == "__main__":
    main()

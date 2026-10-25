# -*- coding: utf-8 -*-
"""
模块 1：LLM 调用 + 多轮对话
====================================
目标：写一个能在命令行里连续聊天的机器人

最重要的一个概念（先记住它，整个 Agent 体系都建立在它上面）：

    LLM API 是【无状态】的。
    服务器不记得你上一句说了什么。
    所谓"多轮对话"，就是每次都把【全部历史】重新发一遍。

类比前端：HTTP 请求本身不保存 session，你要自己带上 cookie。
messages 列表就是你的 "cookie" —— 记忆全靠它，AI 本身没有记忆。

运行前先填好下面配置区的 3 个值，然后运行：  python chat.py
"""

import os
from openai import OpenAI

# ===============================================================
# 第 1 步：配置 API
# ===============================================================
# OpenAI SDK 的格式是行业通用标准：DeepSeek / 智谱 / Kimi / 各种中转站
# 都兼容，差别只是 base_url 和 key 不同。
client = OpenAI(
    # 优先从环境变量读（安全，不会把 key 提交到 git），
    # 也可以直接把第二个参数改成你的真实 key / base_url
    api_key=os.getenv("LLM_API_KEY", "在这里填你的key"),
    base_url=os.getenv("LLM_BASE_URL", "在这里填你的base_url"),
)

MODEL = "在这里填你的模型名"  # 例如 deepseek-chat / gpt-4o-mini / glm-4-flash


# ===============================================================
# 第 2 步：理解 messages 列表 —— AI 的"记忆"
# ===============================================================
# messages 是一个由"消息字典"组成的列表，每个字典两个字段：
#   role:    谁说的？
#            system    = 导演/人设（最高优先级的背景规则）
#            user      = 用户说的话
#            assistant = AI 自己说过的话
#   content: 具体内容
#
# 为什么 assistant 的历史消息也要放回去？
# 因为模型每次都从零开始读整个列表，只有把 AI 说过的也带上，
# 它才知道"自己之前说了什么"。

messages = [
    {"role": "system", "content": "你是一个简洁友好的中文编程助手，回答控制在3句话以内。"},
]


def chat(user_input: str) -> str:
    """发一次请求，返回 AI 的回复文本。这就是最小可用的 '对话单元'。"""
    # 2.1 把用户这轮说的话追加到历史（历史就是这样一轮轮长出来的）
    messages.append({"role": "user", "content": user_input})

    # 2.2 发请求：注意，发的是【整个 messages 列表】，不是只有这一句
    response = client.chat.completions.create(
        model=MODEL,
        messages=messages,
        temperature=0.7,   # 0 = 最稳定死板，1 = 更有创造性
        max_tokens=1024,   # 限制本次回复的最大长度
    )

    # 2.3 从返回结构里取出文本
    reply = response.choices[0].message.content

    # 2.4 把 AI 的回复也追加进历史（不加这行，下一轮它就"失忆"）
    messages.append({"role": "assistant", "content": reply})

    return reply


# ===============================================================
# 第 3 步：CLI 循环
# ===============================================================
def main():
    print("=== 模块1 CLI 聊天机器人 ===")
    print("直接输入开始聊天 | q 退出 | /history 查看 messages 列表\n")

    while True:
        try:
            user_input = input("你> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n再见！")
            break

        if not user_input:
            continue
        if user_input.lower() == "q":
            print("再见！")
            break

        # 教学彩蛋：随时偷看 messages 现在长什么样 ——
        # 你会看到列表越来越长，这就是"多轮对话"的全部真相
        if user_input == "/history":
            print("--- 当前 messages ---")
            for m in messages:
                print(f"  [{m['role']:>9}] {m['content'][:50]}")
            print("---------------------\n")
            continue

        reply = chat(user_input)
        print(f"AI> {reply}\n")


if __name__ == "__main__":
    main()

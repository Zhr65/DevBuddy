# -*- coding: utf-8 -*-
"""
模块 2：工具调用 + ReAct 循环
====================================
目标：给聊天机器人装一个"天气工具"，看它自己决定什么时候用

先建立三大认知（模块 2 的全部灵魂）：

    1. 工具 = 一个普通的 Python 函数，没有任何魔法
    2. AI 只会"说"（输出文字），永远不会"做"（执行函数）
       —— 真正的执行者是你写的 for 循环！
    3. 工具的执行结果也是一条消息，塞回 messages，AI 才能看见

ReAct = Reason(想) + Act(做) + Observation(看结果)，
循环往复，直到 AI 给出最终回答。

运行前：把 client 配置区填好（和 mini.py 一样的三样东西）
运行：  python agent_tool.py
"""

import os
from pathlib import Path

from dotenv import load_dotenv
from openai import OpenAI

# ===============================================================
# 配置区（和 mini.py 一样）
# ===============================================================
# 密钥从 agent/.env 读，不写死在代码里（本文件要进公开仓库）
# 独立运行（python practice/agent_tool.py）时 __file__ 在 practice/，往上两层才是 agent/
load_dotenv(Path(__file__).resolve().parent.parent / ".env")

client = OpenAI(
    api_key=os.getenv("AGNES_API_KEY", ""),
    base_url="https://apihub.agnes-ai.com/v1",
)
MODEL = "agnes-2.5-flash"


# ===============================================================
# 第 1 部分：工具 —— 就是普通函数
# ===============================================================
def get_weather(city: str) -> str:
    """假装查天气：返回写死的数据。以后换成真 API，Agent 代码一行都不用改。"""
    return f"{city}今天晴，25 度，微风，适合出门。"

# 工具注册表：名字 -> 函数
# AI "点名"要用工具时，我们靠这张表找到该执行哪个函数
TOOLS = {
    "get_weather": get_weather,
}


# ===============================================================
# 第 2 部分：ReAct 循环 —— Agent 的心脏
# ===============================================================
messages = [
    {"role": "system", "content": (
        "你是一个可以调用天气工具的助手。"
        "当需要查天气时，你只能输出一行、不要输出别的内容，格式严格如下："
        "TOOL_CALL: get_weather:城市名"
        "例如：TOOL_CALL: get_weather:北京"
        "如果收到 TOOL_RESULT 开头的消息，说明是工具的执行结果，请基于它回答用户。"
        "如果问题不需要查天气，就直接正常回答，不要输出 TOOL_CALL。"
    )},
]


def run_agent(user_input: str, max_steps: int = 5) -> str:
    """一次完整的 Agent 运行：里面可能循环调用 LLM 好几次。"""
    messages.append({"role": "user", "content": user_input})

    # max_steps：最多转 5 圈。没有它，一旦 AI 输出格式不对，
    # 循环就永远停不下来，你的 token 费用会一直烧（真实事故！）
    for step in range(max_steps):

        reply = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            temperature=0.3,  # 工具调用需要格式稳定，温度调低
        ).choices[0].message.content

        # ---- R（Reason）：AI 开口了，判断它是"想用工具"还是"直接回答" ----
        if reply.startswith("TOOL_CALL:"):

            # ---- A（Act）：解析出工具名和参数，然后【我们】执行它 ----
            # "TOOL_CALL: get_weather:北京" -> " get_weather:北京"
            rest = reply.split(":", 1)[1].strip()
            tool_name, tool_arg = rest.split(":", 1)
            tool_name = tool_name.strip()

            print(f"  [Agent 想调用工具] {tool_name}({tool_arg})")
            result = TOOLS[tool_name](tool_arg)   # 真正干活的是这一行，不是 AI
            print(f"  [工具返回结果] {result}")

            # ---- O（Observation）：把结果塞回 messages，让 AI 看见 ----
            # assistant 的"想调用工具"和工具结果都要进历史
            messages.append({"role": "assistant", "content": reply})
            # 这种手动 ReAct 没有专用角色，借用 user 传递工具结果
            # （模块 3 的真 function calling 会有专门的 tool 角色）
            messages.append({"role": "user", "content": f"TOOL_RESULT: {result}"})
            continue   # 转下一圈：AI 看到结果，给出真正的回答

        else:
            # 没有 TOOL_CALL 标记 = 这就是最终回答，Agent 运行结束
            messages.append({"role": "assistant", "content": reply})
            return reply

    return "（达到最大步数 5，强制停止 —— 通常是 AI 输出格式不对）"


# ===============================================================
# 第 3 部分：CLI 循环
# ===============================================================
def main():
    print("=== 模块2 天气 Agent（q 退出）===\n")
    while True:
        user_input = input("你> ").strip()
        if user_input.lower() == "q":
            break
        if not user_input:
            continue
        print("AI>", run_agent(user_input), "\n")


if __name__ == "__main__":
    main()

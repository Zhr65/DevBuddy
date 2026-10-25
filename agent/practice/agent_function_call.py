# -*- coding: utf-8 -*-
"""
模块 3：真 Function Calling（官方协议）
====================================
模块 2 我们靠"暗号"（TOOL_CALL: ...）求 AI 配合，格式全靠自觉。
模块 3 用 OpenAI 官方的 tools 参数 —— 厂商原生支持，正规军上岗。

对照模块 2，只有 4 处升级，其余一模一样：

    升级1 教 AI 用工具：不用在 system prompt 里写暗号格式，
          直接递 tools=[说明书]，JSON Schema 官方格式，系统自动教
    升级2 判断 AI 意图：不用 startswith("TOOL_CALL:") 猜暗号，
          看 msg.tool_calls 是否存在，官方明确告诉你"它想调工具"
    升级3 拿到参数：不用 split(":", 1) 手撕字符串，
          arguments 是 JSON 字符串，json.loads 一下就是字典
    升级4 回传结果：不用借用 user 角色喊 TOOL_RESULT，
          有专属的 role="tool"，凭 tool_call_id 对账

不变的：ReAct 循环骨架、max_steps 防烧钱、TOOLS 注册表。

运行：python agent_function_call.py
实验1：北京天气怎么样？      → 看到工具调用日志
实验2：1+1等于几？           → 直接回答，不调工具
实验3：帮我查北京和上海的天气 → AI 可以一次发多个工具请求（模块2很难做到！）
"""

import json
from openai import OpenAI

# ===============================================================
# 配置区（和前两章一样）
# ===============================================================
client = OpenAI(
    api_key="<REDACTED>",
    base_url="https://apihub.agnes-ai.com/v1",
)
MODEL = "agnes-2.5-flash"


# ===============================================================
# 第 1 部分：工具 —— 普通函数，和模块 2 一字不差
# ===============================================================
def get_weather(city: str) -> str:
    """假装查天气：返回写死的数据。以后换真 API，Agent 代码不用改。"""
    return f"{city}今天晴，25 度，微风，适合出门。"

TOOLS = {
    "get_weather": get_weather,
}


# ===============================================================
# 第 2 部分：工具说明书（JSON Schema）—— 模块 3 的新东西
# ===============================================================
# 这份说明书替代了模块 2 system prompt 里的暗号教学：
# AI 厂商拿到底层后，会用官方训练教模型"怎么填工单"，
# 我们只需要说清楚：这工具叫什么、干什么用、要什么参数。
TOOLS_SCHEMA = [
    {
        "type": "function",                 # 类型固定写 "function"
        "function": {
            "name": "get_weather",          # 工具名（要和 TOOLS 表对上）
            "description": "查询某个城市今天的天气。当用户问到天气时调用。",
            "parameters": {                 # 参数长什么样：JSON Schema
                "type": "object",
                "properties": {
                    "city": {
                        "type": "string",
                        "description": "城市名字，比如：北京",
                    }
                },
                "required": ["city"],       # 哪些参数必须给
            },
        },
    }
]


# ===============================================================
# 第 3 部分：ReAct 循环 —— 骨架同模块 2，只有 4 处升级
# ===============================================================
# 注意 system prompt 瘦身了！不用再教暗号格式，一句话就够
messages = [
    {"role": "system", "content": "你是一个乐于助人的中文助手。"},
]


def run_agent(user_input: str, max_steps: int = 5) -> str:
    """一次完整的 Agent 运行：里面可能循环调用 LLM 好几次。"""
    messages.append({"role": "user", "content": user_input})

    for step in range(max_steps):

        resp = client.chat.completions.create(
            model=MODEL,
            messages=messages,
            tools=TOOLS_SCHEMA,      # 升级1：把说明书递给 AI（每次都要带）
            temperature=0.3,
        )
        msg = resp.choices[0].message

        # ---- 升级2：判断方式 ----
        # 模块2：reply.startswith("TOOL_CALL:")   靠猜暗号
        # 模块3：msg.tool_calls 存在 = AI 明确表示"我要调工具"
        #（等价写法：resp.choices[0].finish_reason == "tool_calls"）
        if msg.tool_calls:

            # AI 这句话里装着"调工具请求"，原样记进记忆本
            #（assistant 消息现在自带 tool_calls 字段，不能丢！丢了下一圈对不了账）
            messages.append(msg)

            # 注意是复数：AI 可以一口气发多个工具请求（升级2的隐藏福利）
            for tc in msg.tool_calls:

                # ---- 升级3：拿参数 ----
                # 模块2：reply.split(":", 1)            手撕字符串
                # 模块3：arguments 是 JSON 字符串，loads 成字典
                args = json.loads(tc.function.arguments)
                tool_name = tc.function.name

                print(f"  [Agent 想调用工具] {tool_name}({args})")

                # TOOLS[tool_name] 从注册表找到函数
                # **args 解包：{"city": "北京"} -> get_weather(city="北京")
                result = TOOLS[tool_name](**args)
                print(f"  [工具返回结果] {result}")

                # ---- 升级4：回结果 ----
                # 模块2：借用 user 说 "TOOL_RESULT: ..."
                # 模块3：专属 role="tool"，tool_call_id 像快递单号，
                #        告诉 AI 这份结果对应哪个请求（多工具时不 confusion）
                messages.append({
                    "role": "tool",
                    "tool_call_id": tc.id,
                    "content": result,
                })

            continue   # 转下一圈：AI 看到结果，给出真正的回答

        else:
            # 没有工具请求 = 这是最终回答，Agent 运行结束
            messages.append({"role": "assistant", "content": msg.content})
            return msg.content

    return "（达到最大步数 5，强制停止）"


# ===============================================================
# 第 4 部分：CLI 循环 —— 和模块 2 一字不差
# ===============================================================
def main():
    print("=== 模块3 Function Calling Agent（q 退出）===\n")
    while True:
        user_input = input("你> ").strip()
        if user_input.lower() == "q":
            break
        if not user_input:
            continue
        print("AI>", run_agent(user_input), "\n")


if __name__ == "__main__":
    main()

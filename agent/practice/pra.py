# -*- coding: utf-8 -*-
"""
【模块 1 · 完整答案版】
运行：python pra.py
验收：最后一行能打印出 "小美"
先填好下面的 key / base_url / 模型名
"""

import os
from openai import OpenAI

client = OpenAI(
    api_key=os.getenv("LLM_API_KEY", "在这里填你的key"),
    base_url=os.getenv("LLM_BASE_URL", "在这里填你的base_url"),
)

MODEL = "在这里填你的模型名"

# system 角色 = 给 AI 的"人设/规则"，优先级最高，只出现一次，放在最前面
messages = [
    {"role": "system", "content": "你是一个爱记名字的助手。"},
]

# ---------- 第 1 轮：告诉它你的名字 ----------

# user 角色 = 用户说的话。用 append 追加进历史列表
messages.append({"role": "user", "content": "你好，我叫小美，请记住我的名字。"})

# 方法是 .create() —— 发起一次对话请求就靠它
# 注意：发的是【整个 messages 列表】，不是只有这一句话。
# 此刻列表里有 2 条：[system, user]
resp1 = client.chat.completions.create(
    model=MODEL,
    messages=messages,
)

# 取回复文本的固定写法：resp.choices[0].message.content
reply1 = resp1.choices[0].message.content

# AI 说的话算 assistant 角色，必须塞回列表。
# 不塞回去的话，下一轮 AI 就不记得自己说过什么（无状态！）
messages.append({"role": "assistant", "content": reply1})

print("第1轮 AI 说：", reply1)

# ---------- 第 2 轮：考它记不记得 ----------

# 追加第二轮的用户提问
messages.append({"role": "user", "content": "我叫什么名字？"})

# 关键点：这次发过去的列表已经有 4 条了：
# [system, user(我叫小美), assistant(你好小美), user(我叫什么?)]
# 它能答对"小美"，不是因为服务器记住了，而是因为答案就写在列表里
resp2 = client.chat.completions.create(
    model=MODEL,
    messages=messages,
)

reply2 = resp2.choices[0].message.content

# 同样把 AI 的回答塞回列表（养成习惯：每次都塞）
messages.append({"role": "assistant", "content": reply2})

print("第2轮 AI 说：", reply2)  # 应该输出 "小美" 相关内容

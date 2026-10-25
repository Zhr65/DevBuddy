# -*- coding: utf-8 -*-
"""
模块 6：LangGraph —— 把你手写的一切交给框架托管
====================================
前 5 个模块你亲手写过 Agent 的每个零件。这一课全部交给 LangGraph。

对照表（本课程的灵魂）——你写的代码 → LangGraph 的对应物：

    你的全局 messages 列表         → State（框架管理的状态，自动追加）
    你的 run_agent 的 for + if     → 图（StateGraph）：节点 + 条件边
    你的 call_llm()（58行）        → call_model 节点（只剩 1 行 invoke！）
    你的工具执行 + 记账整段        → ToolNode（框架内置，自动执行自动记账）
    你的 TOOLS 字典 + 手写 Schema  → @tool 装饰器（schema 从 docstring 自动生成）
    你手动 append 记账             → checkpointer（自动存档，多轮记忆白送）

运行前（一次性）：pip install langgraph langchain-openai
运行：python agent_langgraph.py
实验1：北京天气怎么样？   → 调 get_weather
实验2：年假有几天？       → 调 search_kb 翻手册
实验3：先问北京天气，再问"那上海呢？" → 记得上一轮（checkpointer 的功劳）
"""

import os
from typing import Annotated, TypedDict

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

# ===============================================================
# 配置区：复用 .env（模块 5 立的规矩：代码里不见 key）
# ===============================================================
load_dotenv()

llm = ChatOpenAI(
    model="agnes-2.5-flash",
    api_key=os.getenv("AGNES_API_KEY"),
    base_url="https://apihub.agnes-ai.com/v1",
    temperature=0.3,
)


# ===============================================================
# 第 1 部分：@tool —— 工具注册的框架版
# ===============================================================
# 对照模块 5：以前要写三件套 ①函数 ②TOOLS 字典 ③手写 JSON Schema。
# 现在 @tool 一个装饰器全包：
#   函数名   → name
#   docstring → description（所以 docstring 要写成"给 AI 看的说明书"！）
#   类型标注  → 参数 schema
@tool
def get_weather(city: str) -> str:
    """查询某个城市今天的天气。当用户问到天气时调用。"""
    return f"{city}今天晴，25 度，微风，适合出门。"


@tool
def search_kb(query: str) -> str:
    """在员工手册知识库中检索资料（年假、报销、考勤等制度问题）。当用户问到公司制度时调用。"""
    # 检索逻辑就是把 agent_prod.py 里的 search() 搬进来（一行不用改）。
    # 为了聚焦框架本身，这里先用关键词假检索 —— 工具是真是假，图完全不关心。
    if "年假" in query or "假期" in query or "请假" in query:
        return "员工入职满一年享有5天带薪年假，满三年增加到10天，年假需提前3天向主管申请。"
    if "报销" in query or "发票" in query:
        return "报销流程：每月最后一天前提交发票照片到财务系统，单笔超过200元需要主管审批，超过2000元需要总监审批。"
    if "考勤" in query or "迟到" in query or "工作时间" in query:
        return "考勤制度：工作时间为9点到18点，午休1小时，一个月内迟到3次按旷工半天处理。"
    return "（知识库里没有相关资料）"


# 把说明书递给模型（对照模块 3 的 tools=TOOLS_SCHEMA 参数）
llm_with_tools = llm.bind_tools([get_weather, search_kb])


# ===============================================================
# 第 2 部分：State —— 框架管的"记忆本"
# ===============================================================
# 对照：以前 messages 是你手动 append 的全局列表。
# 这里 messages 字段挂上 add_messages 这个"合并规则"：
# 节点返回新消息时，框架自动【追加】而不是覆盖 —— append 这活儿框架干了。
class State(TypedDict):             
    messages: Annotated[list, add_messages]


# ===============================================================
# 第 3 部分：节点 —— 图上的"工作站"
# ===============================================================
def call_model(state: State):         # 问 AI 节点
    """对照你手写的 call_llm()：58 行 → 1 行。
    流式、重试、碎片拼装、记账……框架全接管了（本课先不追求流式）。"""
    return {"messages": [llm_with_tools.invoke(state["messages"])]}


# 工具执行节点：对照你手写的"解析 tool_calls → 查注册表 → 执行 → 记账"整段
tool_node = ToolNode([get_weather, search_kb])


# ===============================================================
# 第 4 部分：组图 —— 把循环画出来
# ===============================================================
builder = StateGraph(State)
builder.add_node("agent", call_model)    # 工作站1：问 AI
builder.add_node("tools", tool_node)     # 工作站2：执行工具

builder.add_edge(START, "agent")         # 入口 → agent 站    add_edge(从, 到) 意思是：「从 A 走完，就直接去 B。」
# 条件边 = 你手写的 if tool_calls：
# AI 的回复带工具请求 → 拐去 tools 站；不带 → 直达 END
builder.add_conditional_edges("agent", tools_condition)    # 条件边：根据 tool_calls 决定是否去 tools 站
builder.add_edge("tools", "agent")       # 工具结果回炉再问 AI（= 你的 continue）

# checkpointer：自动存档员。按 thread_id 给每个对话单独记历史，
# 你的多轮记忆从"全局变量手动记账"升级成"框架白送"。
memory = MemorySaver()
graph = builder.compile(checkpointer=memory)


# ===============================================================
# 第 5 部分：CLI
# ===============================================================
def main():
    print("=== 模块6 LangGraph Agent（q 退出）===\n")
    config = {"configurable": {"thread_id": "会话1"}}   # 对话的"档案号"
    while True:
        user_input = input("你> ").strip()
        if user_input.lower() == "q":
            break
        if not user_input:
            continue
        result = graph.invoke(
            {"messages": [("user", user_input)]},
            config,
        )
        print("AI>", result["messages"][-1].content, "\n")


if __name__ == "__main__":
    main()

# -*- coding: utf-8 -*-
"""
模块 6.4：一行造 Agent（create_react_agent）
====================================
对照 agent_langgraph.py 的手搭图版 —— 手搭 60 行，这里核心只剩 1 行。

诚实的说明：工具定义（@tool）哪一版都省不掉 —— "有什么工具"是业务事实，
框架替不掉。框架替掉的是：循环、判断、工具执行、记账、记忆管理。

运行前：pip install langgraph langchain-openai
运行：python agent_langgraph_mini.py
实验：北京天气怎么样？ / 年假有几天？ / 先问北京再问"那上海呢？"
"""

import os

from dotenv import load_dotenv
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langgraph.checkpoint.memory import MemorySaver
from langgraph.prebuilt import create_react_agent

load_dotenv()

llm = ChatOpenAI(
    model="agnes-2.5-flash",
    api_key=os.getenv("AGNES_API_KEY"),
    base_url="https://apihub.agnes-ai.com/v1",
    temperature=0.3,
)


@tool
def get_weather(city: str) -> str:
    """查询某个城市今天的天气。当用户问到天气时调用。"""
    return f"{city}今天晴，25 度，微风，适合出门。"


@tool
def search_kb(query: str) -> str:
    """在员工手册知识库中检索资料（年假、报销、考勤等制度问题）。当用户问到公司制度时调用。"""
    if "年假" in query or "假期" in query or "请假" in query:
        return "员工入职满一年享有5天带薪年假，满三年增加到10天，年假需提前3天向主管申请。"
    if "报销" in query or "发票" in query:
        return "报销流程：每月最后一天前提交发票照片到财务系统，单笔超过200元需要主管审批，超过2000元需要总监审批。"
    if "考勤" in query or "迟到" in query or "工作时间" in query:
        return "考勤制度：工作时间为9点到18点，午休1小时，一个月内迟到3次按旷工半天处理。"
    return "（知识库里没有相关资料）"


# ============ 核心就这一行：图、节点、条件边、工具执行、记账，全包了 ============
agent = create_react_agent(llm, tools=[get_weather, search_kb], checkpointer=MemorySaver())
# ==============================================================================

if __name__ == "__main__":
    config = {"configurable": {"thread_id": "会话1"}}
    print("=== 模块6.4 一行版 Agent（q 退出）===\n")
    while True:
        user_input = input("你> ").strip()
        if user_input.lower() == "q":
            break
        if not user_input:
            continue
        result = agent.invoke({"messages": [("user", user_input)]}, config)
        print("AI>", result["messages"][-1].content, "\n")

"""
graph.py —— LangGraph Agent 核心

架构分层（M2 的规矩）：
─────────────────────────────────
  API 层 (routes.py)        ← HTTP 进出，SSE 格式
      ↓ 调用 graph.stream_chat()
  Agent 层 (graph.py)       ← LangGraph 组图，ReAct 循环，流式事件派发
      ↓ @tool search_react_docs 内部调用
  RAG 层 (retriever.py)    ← 向量检索 + 阈值兜底（M1 已完成）

为什么手搭 StateGraph 而不是 create_react_agent？
─────────────────────────────────
create_react_agent 一行造 Agent 没错，但它把"工具执行"这件事黑盒化了。
SSE 流式需要把"AI 思考中 → 调了什么工具 → 拿到什么资料 → 正在回答"
这四个阶段清晰地推给前端做 UI，所以必须手动组图来精细控制每个阶段的事件派发。

SSE Event 格式（前端消费这个）：
─────────────────────────────────
  {"type": "thinking", "content": "token..."}      ← AI 思考 + 回答的流式 token
  {"type": "tool_call", "tool": "search_react_docs", "query": "useState", "source": "useState.md"}
  {"type": "done"}                                 ← 流结束
  {"type": "error", "message": "..."}              ← 异常兜底
"""
import logging
logger = logging.getLogger(__name__)
from typing import Annotated, AsyncGenerator, TypedDict

from langchain_core.messages import AIMessageChunk, ToolMessage, SystemMessage
from langchain_core.tools import tool
from langchain_openai import ChatOpenAI
from langchain_openai.chat_models.base import OpenAIRateLimitError
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import START, StateGraph
from langgraph.graph.message import add_messages
from langgraph.prebuilt import ToolNode, tools_condition

from app.core.config import AGNES_API_KEY
from app.rag.retriever import retrieve, RetrievalError


# ===============================================================
# LLM —— 复用你模块6的配置（apihub.agnes-ai.com 是 OpenAI 兼容接口）
# ===============================================================
llm = ChatOpenAI(
    model="agnes-2.5-flash",
    api_key=AGNES_API_KEY,
    base_url="https://apihub.agnes-ai.com/v1",
    temperature=0.3,
)


# ===============================================================
# @tool —— 把 retriever 包成 Agent 能调的工具
# ===============================================================
# docstring 写给 AI 看的说明书，@tool 从这里自动生成 tool schema
@tool
def search_react_docs(query: str) -> str:
    """在 React 官方文档知识库中检索资料。当用户问到 React hooks（useState/useEffect/useContext/useRef）、props、组件通信等问题时调用。只返回相关的原文片段，不做改写。"""
    results = retrieve(query)

    if not results:
        return "（知识库中没有找到相关资料，请换个角度提问）"

    # 把检索结果拼成可读文本喂给 LLM
    # 每条结果带 source 让 LLM 知道"这段来自哪篇"
    chunks = []
    for chunk in results:
        src = chunk.source
        sim = chunk.similarity
        chunks.append(f"[来源: {src}, 相关度: {sim:.2f}]\n{chunk.content}")

    return "\n\n---\n\n".join(chunks)


TOOLS = [search_react_docs]

# ===============================================================
# System Prompt —— 约束 LLM 的行为边界
# ===============================================================
SYSTEM_PROMPT = """你是 React 官方文档助手。严格遵守以下三条规则：

1. 回答必须基于 search_react_docs 工具返回的原文片段。如果工具返回「知识库中没有找到相关资料」，
   就直接告诉用户没找到，不要用自己的知识补充——宁可说不知道，也不要编。
   **最多检索 2 次。如果两次都没找到直接相关的内容，就明确告诉用户"知识库中没有找到相关内容"，
   不要再换说法继续检索。**
2. 引用具体内容时，标明来源文件名（例如 useState.md），让用户能自己核对。
3. 不要改写原文的技术细节（参数名、执行顺序、限制条件）。可以总结，但不要替换术语、不要模糊化。
"""



# ===============================================================
# State —— 和模块6一模一样
# ===============================================================
class State(TypedDict):
    messages: Annotated[list, add_messages]


# ===============================================================
# 组图 —— 和模块6一模一样，但这次要拿流式事件
# ===============================================================
llm_with_tools = llm.bind_tools(TOOLS)


def call_model(state: State):
    # system prompt 每次临时拼在最前面，不写进 state
    # 否则 MemorySaver 会把它当历史消息累积，每轮多一条，token 白烧
    messages = [SystemMessage(content=SYSTEM_PROMPT)] + state["messages"]
    return {"messages": [llm_with_tools.invoke(messages)]}


tool_node = ToolNode(TOOLS)

builder = StateGraph(State)
builder.add_node("agent", call_model)
builder.add_node("tools", tool_node)

builder.add_edge(START, "agent")
builder.add_conditional_edges("agent", tools_condition)
builder.add_edge("tools", "agent")

memory = MemorySaver()
graph = builder.compile(checkpointer=memory)


# ===============================================================
# 流式输出 —— M2 核心！把 LangGraph 的流式 chunk 变成 SSE event
# ===============================================================
async def stream_chat(
    user_message: str,
    conversation_id: str = "default",
) -> AsyncGenerator[dict, None]:        #异步生成器
    """
    把用户问题塞进 LangGraph，逐 token yield SSE event dict。

    参数:
        user_message:    用户的问题
        conversation_id: 对话ID —— 同一ID的多轮对话会自动记得上下文

    yield (每个 dict 就是一个 SSE event，routes.py 会序列化成 JSON):
        {"type": "thinking", "content": "..."}
        {"type": "tool_call", "tool": "...", "query": "..."}
        {"type": "tool_result", "source": "..."}
        {"type": "done"}
        {"type": "error", "message": "..."}
    """
    config = {
        "configurable": {"thread_id": conversation_id},
        "recursion_limit": 10,
    }

    try:
        # stream_mode=["messages", "updates"] —— LangGraph 会同时推两个流
        # 每个 item 是 2 元组: (stream_type, (inner_payload, meta))
        #   ("messages", (AIMessageChunk, meta)) → 逐 token（thinking）
        #   ("updates",   ({node_name: output},)) → 节点完整输出（能解 tool_calls）
        async for item in graph.astream(              # 异步流（传送带）
            {"messages": [("user", user_message)]},
            config,
            stream_mode=["messages", "updates"],
        ):
            stream_type = item[0]
            inner = item[1]

            if stream_type == "messages":
                # inner = (AIMessageChunk, meta)   一个是内容块一个是元数据
                chunk = inner[0]
                if isinstance(chunk, AIMessageChunk) and chunk.content:
                    yield {"type": "thinking", "content": chunk.content}

            elif stream_type == "updates":
                # inner = ({node_name: node_output_dict},)
                updates_dict = inner[0] if isinstance(inner, tuple) else inner
                node_name = list(updates_dict.keys())[0] if updates_dict else ""

                if node_name == "agent":
                    #挖出 tool_calls（5行防御）
                    agent_output = updates_dict["agent"]
                    agent_messages = agent_output.get("messages", [])
                    if agent_messages:
                        last_msg = agent_messages[-1]
                        tool_calls = getattr(last_msg, "tool_calls", None) or []
                        #for tc: 兼容两种格式（7行防御）
                        for tc in tool_calls:
                            if isinstance(tc, dict):
                                name = tc.get("name", "?")
                                args = tc.get("args", {})
                            else:
                                name = getattr(tc, "name", "?")
                                args = getattr(tc, "args", {})
                            yield {
                                "type": "tool_call",
                                "tool": name,
                                "query": args.get("query", ""),
                            }

                elif node_name == "tools":
                    yield {"type": "tool_done"}

        # 流正常结束
        yield {"type": "done"}

    except OpenAIRateLimitError:
        yield {"type": "error", "message": "AI 服务当前繁忙（限流），请稍后重试"}
    except RetrievalError as e:
        yield {"type": "error", "message": f"知识库暂时不可用，请稍后重试({e})"}
    except Exception:
        logger.exception("stream_chat 未知异常")
        yield {"type": "error", "message": "服务异常，请稍后重试"}


def chat(
    user_message: str,
    conversation_id: str = "default",
) -> str:
    """
    非流式版本 —— 等 AI 完整回答好一次性返回。
    前端 SSE 接口用 stream_chat()，这个给调试/后端内部调用用。
    """
    config = {
        "configurable": {"thread_id": conversation_id},
        "recursion_limit": 10,
    }
    result = graph.invoke(
        {"messages": [("user", user_message)]},
        config,
    )
    return result["messages"][-1].content


if __name__ == "__main__":
    # 直接运行可以在 CLI 测试 Agent
    import asyncio

    async def test():
        print("=== DevBuddy Agent 测试（q 退出）===\n")
        conv_id = "test_conv_1"
        while True:
            user_input = input("你> ").strip()
            if user_input.lower() == "q":
                break
            if not user_input:
                continue

            print("\nAI> ", end="", flush=True)
            async for event in stream_chat(user_input, conv_id):
                if event["type"] == "thinking":
                    print(event["content"], end="", flush=True)
                elif event["type"] == "tool_call":
                    print(f"\n  🔧 调工具: {event['tool']}(query='{event['query']}')", flush=True)
                elif event["type"] == "tool_done":
                    print("  ✅ 检索完成\nAI> ", end="", flush=True)
                elif event["type"] == "done":
                    print("\n")
                elif event["type"] == "error":
                    print(f"\n❌ 出错: {event['message']}")

    asyncio.run(test())

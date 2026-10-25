"""
routes.py —— HTTP 路由 + SSE 流式输出

SSE 协议速记：
─────────────────────────────────
Content-Type: text/event-stream
每个事件格式：
    data: {JSON字符串}\n\n     ← 注意两个 \n\n 分隔事件

为什么 SSE 而不是 WebSocket？
  - 前端 React 用 EventSource() 就能消费 SSE，比 WebSocket 简单 10 倍
  - 我们只需要"后端推前端"（AI 逐 token 吐回复），不需要双向
  - 走 HTTP 协议，CORS/代理都友好
"""
import json
from typing import Optional

from fastapi import APIRouter
from fastapi.responses import StreamingResponse
from pydantic import BaseModel

from app.agent.graph import stream_chat
from app.rag.vectorstore import get_vectorstore

router = APIRouter()


# ===============================================================
# 请求 / 响应模型
# ===============================================================
class ChatRequest(BaseModel):
    message: str                        # 用户的问题
    conversation_id: Optional[str] = None  # 对话ID，不传则用 "default"


class ChatResponse(BaseModel):
    """非流式响应（暂未使用，留着给以后扩展）"""
    reply: str
    conversation_id: str


class HealthResponse(BaseModel):
    status: str
    vectorstore_exists: bool
    chunks_count: Optional[int] = None


# ===============================================================
# 核心：POST /chat —— SSE 流式端点
# ===============================================================
def _to_sse_line(event_dict: dict) -> str:
    """把一个 event dict 序列化成 SSE 格式的一行"""
    return f"data: {json.dumps(event_dict, ensure_ascii=False)}\n\n"


async def _sse_generator(user_message: str, conversation_id: str):
    """包装 graph.stream_chat() 的输出为 SSE 格式"""
    # 先发个连接确认事件
    yield _to_sse_line({"type": "connected", "conversation_id": conversation_id})

    async for event in stream_chat(user_message, conversation_id):
        yield _to_sse_line(event)

    # SSE 连接保持打开，等前端收到 done 事件后主动 close
    # 不用额外发 [DONE]，我们有 {"type": "done"}


@router.post("/chat")
async def chat(req: ChatRequest):
    """
    流式聊天接口。

    请求体:
        {
            "message": "useState 怎么用？",
            "conversation_id": "可选，多轮对话时传同一个ID"
        }

    响应: text/event-stream（SSE）
    事件类型:
        connected   —— 连接建立
        thinking    —— AI 逐 token 思考/回答
        tool_call   —— AI 决定调用检索工具
        tool_done   —— 检索完成
        done        —— 整个回答结束
        error       —— 出错了
    """
    conv_id = req.conversation_id or "default"

    return StreamingResponse(
        _sse_generator(req.message, conv_id),
        media_type="text/event-stream",
        headers={
            "Cache-Control": "no-cache",           # 代理/浏览器别缓存流
            "X-Accel-Buffering": "no",             # Nginx 别缓冲（开流式必须有）
            "Connection": "keep-alive",
        },
    )


# ===============================================================
# GET /health —— 健康检查
# ===============================================================
@router.get("/health", response_model=HealthResponse)
async def health():
    vs = get_vectorstore()
    if vs is None:
        return HealthResponse(status="ok", vectorstore_exists=False)
    return HealthResponse(
        status="ok",
        vectorstore_exists=True,
        chunks_count=vs._collection.count(),
    )

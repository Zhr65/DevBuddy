/**
 * useSSE.ts —— 用 fetch + ReadableStream 手动解析 POST SSE
 * ==========================================================
 *
 * 为什么不能用浏览器原生 EventSource？
 *   EventSource 只支持 GET 请求，但我们的后端 /api/chat 是 POST（需要 body 传 message）。
 *   所以必须用 fetch，手动读 response.body 这个 ReadableStream。
 *
 * SSE 协议格式（后端 routes.py 发来的）：
 * ┌──────────────────────────────────────┐
 * │ data: {"type":"thinking","content":"..."}  \n\n │
 * │ data: {"type":"tool_call","tool":"..."}    \n\n │
 * │ data: {"type":"tool_done"}                  \n\n │
 * │ data: {"type":"done"}                        \n\n │
 * └──────────────────────────────────────┘
 * 每个事件以 \n\n 结尾（SSE 协议规定），data: 前缀是 SSE 的"事件字段名"。
 */
import { useCallback, useRef, useState } from 'react'

// 后端 SSE 事件的类型定义 —— 和 routes.py 里 yield 的 dict 对应
export type SSEEvent =
  | { type: 'connected'; conversation_id: string }
  | { type: 'thinking'; content: string }
  | { type: 'tool_call'; tool: string; query: string }
  | { type: 'tool_done' }
  | { type: 'done' }
  | { type: 'error'; message: string }

// 我们自己在 React state 里管理的"消息"结构 —— 一条消息可能经历：
//   thinking（AI 在打字） → 完整（tool_call 了） → thinking → ... 最后 done
export interface ChatMessage {
  id: string
  role: 'user' | 'assistant'
  content: string                // 助手消息的文本内容（逐 token 累加）
  status: 'streaming' | 'done' | 'error'
  toolCalls?: { tool: string; query: string }[]  // 助手期间调了哪些工具
}

// 给每条消息生成唯一 ID
const genId = () => Math.random().toString(36).slice(2)

export function useSSE(apiUrl = '/api/chat') {
  const [messages, setMessages] = useState<ChatMessage[]>([])
  const [loading, setLoading] = useState(false)
  // 当前正在流式接收的那条 assistant 消息的 ID
  const currentAssistantId = useRef<string | null>(null)
  // 会话 ID：每个标签页一个。
  // 用 sessionStorage 而不是 localStorage —— localStorage 是"同源共享"，
  // 两个标签页会拿到同一个 ID，等于没修串台；sessionStorage 是"每标签页独立"，
  // 且刷新不丢（localStorage 那种"刷新保留"的诉求它也能满足）。
  const [conversationId] = useState(() => {
    const saved = sessionStorage.getItem('conversation_id')
    if (saved) return saved
    const id = crypto.randomUUID()
    sessionStorage.setItem('conversation_id', id)
    return id
  })

  /**
   * 解析 SSE 流的核心函数 —— 把 ReadableStream 切成一个个 SSE event
   *
   * SSE 协议：每个 event 块由 \n\n 分隔，每一行以 "data: " 开头
   *   data: {"type":"thinking","content":"hello"}
   * （如果有多个 data: 行会拼成一个 event，我们这里后端只发一行）
   */
  async function parseSSEStream(
    response: Response,
    onEvent: (event: SSEEvent) => void,
  ) {
    if (!response.body) throw new Error('response.body 为空')

    // ReadableStream 的 reader —— 像吸管一样从网络流里逐块吸数据
    const reader = response.body.getReader()
    // TextDecoder 把二进制块转成 UTF-8 字符串（中文友好）
    const decoder = new TextDecoder()
    // 缓冲区 —— 因为每次 reader.read() 拿到的是任意字节块，
    // 可能半截 SSE event（比如刚好切在 JSON 中间），所以要拼起来再切
    let buffer = ''

    while (true) {
      // 吸一块二进制数据
      const { value, done } = await reader.read()
      if (done) break  // 流结束

      // 转成字符串，追加到缓冲区
      buffer += decoder.decode(value, { stream: true })

      // 按 SSE 协议的事件分隔符 \n\n 切
      let idx: number
      while ((idx = buffer.indexOf('\n\n')) !== -1) {
        const rawEvent = buffer.slice(0, idx)    // 一个完整的 SSE event
        buffer = buffer.slice(idx + 2)            // 剩的留着跟下次拼

        // 从 "data: {...}" 里抽出 JSON
        const dataLine = rawEvent.split('\n').find(l => l.startsWith('data:'))
        if (dataLine) {
          const jsonStr = dataLine.replace(/^data:\s*/, '')  // 去掉 "data: " 前缀
          try {
            const parsed: SSEEvent = JSON.parse(jsonStr)
            onEvent(parsed)
          } catch {
            console.warn('SSE 事件解析失败:', jsonStr)
          }
        }
      }
    }
  }

  /**
   * 发送一条用户消息 —— 整个 Agent 循环的入口
   */
  const sendMessage = useCallback(async (userText: string) => {
    if (!userText.trim() || loading) return

    setLoading(true)
    currentAssistantId.current = null

    // 1. 先把用户消息塞进 state（让 UI 立即显示"用户气泡"）
    const userMsg: ChatMessage = {
      id: genId(),
      role: 'user',
      content: userText,
      status: 'done',
    }
    setMessages(prev => [...prev, userMsg])

    // 2. 发 POST /api/chat
    try {
      const response = await fetch(apiUrl, {
        method: 'POST',
        headers: { 'Content-Type': 'application/json' },
        body: JSON.stringify({
          message: userText,
          // 带上本标签页的会话 ID —— 不传的话后端全落到 "default"，多窗口会串台
          conversation_id: conversationId,
        }),
      })

      if (!response.ok) {
        throw new Error(`HTTP ${response.status}`)
      }

      // 3. 开始读 SSE 流
      await parseSSEStream(response, (event) => {
        // 每个 event 来了就更新 state —— React 自动重渲染 → 打字机效果
        setMessages(prev => {
          const next = [...prev]

          switch (event.type) {
            case 'connected': {
              // 新建一条空的 assistant 消息（status=streaming）
              const id = genId()
              currentAssistantId.current = id
              next.push({
                id,
                role: 'assistant',
                content: '',
                status: 'streaming',
                toolCalls: [],
              })
              return next
            }

            case 'thinking': {
              // 把 token 追加到当前 assistant 消息的 content
              const idx = next.findIndex(m => m.id === currentAssistantId.current)
              if (idx !== -1) {
                next[idx] = {
                  ...next[idx],
                  content: next[idx].content + event.content,
                }
              }
              return next
            }

            case 'tool_call': {
              // 记录：助手正在调某个工具
              const idx = next.findIndex(m => m.id === currentAssistantId.current)
              if (idx !== -1) {
                next[idx] = {
                  ...next[idx],
                  toolCalls: [
                    ...(next[idx].toolCalls ?? []),
                    { tool: event.tool, query: event.query },
                  ],
                }
              }
              return next
            }

            case 'tool_done': {
              // 工具执行完了 —— 目前不需要特殊处理，thinking 会继续来
              return next
            }

            case 'done': {
              const idx = next.findIndex(m => m.id === currentAssistantId.current)
              if (idx !== -1) {
                next[idx] = { ...next[idx], status: 'done' }
              }
              return next
            }

            case 'error': {
              const idx = next.findIndex(m => m.id === currentAssistantId.current)
              if (idx !== -1) {
                next[idx] = {
                  ...next[idx],
                  status: 'error',
                  content: (next[idx].content || '') + `\n\n[错误] ${event.message}`,
                }
              }
              return next
            }
          }
          return next
        })
      })
    } catch (err) {
      // 整个请求层面的错误（网络断了、后端挂了等）
      setMessages(prev => [
        ...prev,
        {
          id: genId(),
          role: 'assistant',
          content: `[网络错误] ${(err as Error).message}`,
          status: 'error',
        },
      ])
    } finally {
      setLoading(false)
    }
  }, [loading, apiUrl])

  return { messages, loading, sendMessage }
}

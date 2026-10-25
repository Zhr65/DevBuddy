import { useState } from 'react'
import { useSSE } from './hooks/useSSE'
import type { ChatMessage } from './hooks/useSSE'

/**
 * Message 气泡组件 —— 区分 user / assistant 两种样式
 */
function MessageBubble({ msg }: { msg: ChatMessage }) {
  const isUser = msg.role === 'user'

  return (
    <div className={`message ${isUser ? 'user' : 'assistant'}`}>
      <div className="avatar">{isUser ? '你' : '🤖'}</div>
      <div className="bubble">
        {/* 如果这条 assistant 消息期间调了工具，在内容上方显示"🔍 搜索中..." */}
        {!isUser && msg.toolCalls && msg.toolCalls.length > 0 && (
          <div className="tool-info">
            🔍 查阅 React 文档：
            {msg.toolCalls.map((tc, i) => (
              <span key={i} className="tool-tag">
                "{tc.query}"
              </span>
            ))}
          </div>
        )}

        {/* 助手消息正在流式接收时，逐 token 显示（打字机效果）*/}
        <pre className="content">{msg.content}</pre>

        {/* 流式中的 loading 动画 —— 三个小点 */}
        {msg.status === 'streaming' && <span className="typing-cursor" />}

        {/* 错误态 */}
        {msg.status === 'error' && <div className="error-badge">⚠️ 出错了</div>}
      </div>
    </div>
  )
}

export default function App() {
  const { messages, loading, sendMessage } = useSSE()
  const [input, setInput] = useState('')

  const handleSubmit = (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim() || loading) return
    sendMessage(input)
    setInput('')
  }

  // 几个快捷提问 —— 点一下就发
  const quickQs = [
    'useState hook 是干什么的？',
    'useEffect 什么时候触发？',
    'React Context 怎么用？',
    'useRef 和 useState 有什么区别？',
    '父组件怎么把数据传给子组件？',
  ]

  return (
    <div className="app">
      {/* 顶部标题栏 */}
      <header className="header">
        <h1>DevBuddy</h1>
        <p>React 文档知识库 · AI Agent 毕业项目</p>
      </header>

      {/* 快捷提问区（首次打开时显示，有对话后隐藏） */}
      {messages.length === 0 && (
        <div className="quick-questions">
          <p className="hint">试试这些问题👇</p>
          {quickQs.map(q => (
            <button
              key={q}
              className="quick-btn"
              onClick={() => sendMessage(q)}
              disabled={loading}
            >
              {q}
            </button>
          ))}
        </div>
      )}

      {/* 消息列表 */}
      <div className="messages">
        {messages.map(msg => (
          <MessageBubble key={msg.id} msg={msg} />
        ))}
      </div>

      {/* 底部输入框 */}
      <form className="input-bar" onSubmit={handleSubmit}>
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="问我关于 React hooks、props 的任何问题..."
          disabled={loading}
          autoFocus
        />
        <button type="submit" disabled={loading || !input.trim()}>
          {loading ? '思考中...' : '发送'}
        </button>
      </form>
    </div>
  )
}

import react from '@vitejs/plugin-react'
import { defineConfig } from 'vite'

// https://vite.dev/config/
export default defineConfig({
  plugins: [react()],
  server: {
    port: 5173,
    // 前端发 /api/chat → Vite 代理转发到 FastAPI（解决跨域 + 让前端用相对路径）
    // 没代理也能跑（后端已开 CORS），但代理更干净
    proxy: {
      '/api': {
        target: 'http://localhost:8899',
        changeOrigin: true,
        // SSE 流式必须关掉代理缓冲 —— 否则 FastAPI 逐 token 吐的 chunk 被代理攒成大包
        configure: (proxy) => {
          proxy.on('proxyRes', (proxyRes) => {
            // 强制 SSE 响应的 buffering=off，让每个 chunk 实时穿过代理
            if (proxyRes.headers['content-type']?.includes('text/event-stream')) {
              proxyRes.headers['cache-control'] = 'no-cache'
              proxyRes.headers['x-accel-buffering'] = 'no'
            }
          })
        },
      },
    },
  },
})

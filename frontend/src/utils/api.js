import axios from 'axios'

const BASE_URL = 'http://localhost:8001'
const http = axios.create({ baseURL: BASE_URL, timeout: 30000 })

// ── 对话 API（Phase 1，不变）──────────────────────────────────────────────────
export const chatAPI = {
    async sendStream(message, sessionId = 'default', promptId = 'default_assistant', onToken, onDone) {
        const response = await fetch(`${BASE_URL}/api/chat/send`, {
            method: 'POST',
            headers: { 'Content-Type': 'application/json' },
            body: JSON.stringify({ message, session_id: sessionId, prompt_id: promptId }),
        })
        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''
        while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop()
            for (const line of lines) {
                if (line.startsWith('data: ')) {
                    try {
                        const data = JSON.parse(line.slice(6))
                        if (data.token) onToken?.(data.token)
                        if (data.done) onDone?.()
                    } catch { }
                }
            }
        }
    },
    getHistory: (sid, limit = 40) => http.get(`/api/chat/history/${sid}`, { params: { limit } }),
    clearHistory: (sid) => http.delete(`/api/chat/history/${sid}`),
}

// ── 设置 API（Phase 1，不变）──────────────────────────────────────────────────
export const settingsAPI = {
    get: () => http.get('/api/settings'),
    update: (data) => http.put('/api/settings', data),
    toggleVoice: (enabled) => http.post('/api/settings/modules/voice', { enabled }),
    toggleQQ: (enabled) => http.post('/api/settings/modules/qq', { enabled }),
}

// ── Prompt API（Phase 1，不变）────────────────────────────────────────────────
export const promptsAPI = {
    list: () => http.get('/api/prompts'),
    get: (id) => http.get(`/api/prompts/${id}`),
    save: (data) => http.post('/api/prompts', data),
    delete: (id) => http.delete(`/api/prompts/${id}`),
}

// ── 屏幕 / Vision API（Phase 2 新增）─────────────────────────────────────────
//
// analyze() 的回调风格与 chatAPI.sendStream() 完全一致，
// 前端组件只管提供回调，不用关心任何流解析细节。
export const screenAPI = {
    /**
     * 手动触发一次截图 + 视觉分析 + AI 点评（SSE 流式）。
     *
     * 回调说明：
     *   onStatus(key)        — 阶段变化：'capturing' / 'analyzing_vision' / 'generating'
     *   onVisionDesc(text)   — 视觉模型返回的原始画面描述（可选展示）
     *   onToken(text)        — AI 点评的流式 token，逐字拼接
     *   onDone(fullText)     — 流结束，fullText 是完整点评
     *   onError(message)     — 发生错误
     */
    async analyze({ onStatus, onVisionDesc, onToken, onDone, onError } = {}) {
        let response
        try {
            response = await fetch(`${BASE_URL}/api/screen/analyze`, {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({}),
            })
        } catch (e) {
            onError?.(e.message); return
        }

        if (!response.ok) {
            onError?.(`HTTP ${response.status}`); return
        }

        const reader = response.body.getReader()
        const decoder = new TextDecoder()
        let buffer = ''

        while (true) {
            const { done, value } = await reader.read()
            if (done) break
            buffer += decoder.decode(value, { stream: true })
            const lines = buffer.split('\n')
            buffer = lines.pop()

            for (const line of lines) {
                if (!line.startsWith('data: ')) continue
                try {
                    const data = JSON.parse(line.slice(6))
                    if (data.status) onStatus?.(data.status)
                    if (data.vision_desc) onVisionDesc?.(data.vision_desc)
                    if (data.token) onToken?.(data.token)
                    if (data.done) onDone?.(data.full_text ?? '')
                    if (data.error) onError?.(data.error)
                } catch { }
            }
        }
    },

    /** 启动主动互动引擎 */
    startProactive: () => http.post('/api/screen/proactive/start'),

    /** 停止主动互动引擎 */
    stopProactive: () => http.post('/api/screen/proactive/stop'),

    /** 获取引擎状态与最近一次分析摘要 */
    getStatus: async () => {
        const res = await http.get('/api/screen/status')
        return res.data
    },

    /** 获取系统显示器列表（供设置界面使用） */
    getMonitors: async () => {
        const res = await http.get('/api/screen/monitors')
        return res.data
    },
}

export const healthCheck = () => http.get('/health')
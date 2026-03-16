import axios from 'axios'

const BASE_URL = 'http://localhost:8001'
const http = axios.create({ baseURL: BASE_URL, timeout: 30000 })

// ── 对话 API ──────────────────────────────────────────────────────────────────
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

// ── 设置 API ──────────────────────────────────────────────────────────────────
export const settingsAPI = {
    get: () => http.get('/api/settings'),
    update: (data) => http.put('/api/settings', data),
    reload: () => http.post('/api/settings/reload'),
    toggleVoice: (enabled) => http.post('/api/settings/modules/voice', { enabled }),
    toggleQQ: (enabled) => http.post('/api/settings/modules/qq', { enabled }),
}

// ── Prompt API ────────────────────────────────────────────────────────────────
export const promptsAPI = {
    list: () => http.get('/api/prompts'),
    get: (id) => http.get(`/api/prompts/${id}`),
    save: (data) => http.post('/api/prompts', data),
    delete: (id) => http.delete(`/api/prompts/${id}`),
}

// ── 屏幕 / Vision API ─────────────────────────────────────────────────────────
export const screenAPI = {
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

    startProactive: () => http.post('/api/screen/proactive/start'),
    stopProactive: () => http.post('/api/screen/proactive/stop'),
    getStatus: async () => (await http.get('/api/screen/status')).data,
    getMonitors: async () => (await http.get('/api/screen/monitors')).data,
}

export const healthCheck = () => http.get('/health')
import axios from 'axios'

const BASE_URL = 'http://localhost:8001'
const http = axios.create({ baseURL: BASE_URL, timeout: 30000 })

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
          } catch {}
        }
      }
    }
  },
  getHistory: (sid, limit = 40) => http.get(`/api/chat/history/${sid}`, { params: { limit } }),
  clearHistory: (sid) => http.delete(`/api/chat/history/${sid}`),
}

export const settingsAPI = {
  get: () => http.get('/api/settings'),
  update: (data) => http.put('/api/settings', data),
  toggleVoice: (enabled) => http.post('/api/settings/modules/voice', { enabled }),
  toggleQQ: (enabled) => http.post('/api/settings/modules/qq', { enabled }),
}

export const promptsAPI = {
  list: () => http.get('/api/prompts'),
  get: (id) => http.get(`/api/prompts/${id}`),
  save: (data) => http.post('/api/prompts', data),
  delete: (id) => http.delete(`/api/prompts/${id}`),
}

export const healthCheck = () => http.get('/health')

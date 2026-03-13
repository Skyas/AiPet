import { defineStore } from 'pinia'
import { chatAPI } from '@/utils/api'

export const useChatStore = defineStore('chat', {
  state: () => ({
    messages: [],       // { role, content, id, streaming }
    sessionId: 'default',
    promptId: 'default_assistant',
    isStreaming: false,
    isConnected: false,
  }),

  actions: {
    async loadHistory() {
      try {
        const res = await chatAPI.getHistory(this.sessionId)
        this.messages = res.data.messages.map((m, i) => ({
          ...m,
          id: `hist_${i}`,
          streaming: false,
        }))
      } catch (e) {
        console.error('加载历史失败', e)
      }
    },

    async sendMessage(text) {
      if (this.isStreaming || !text.trim()) return

      const userMsg = { role: 'user', content: text, id: `u_${Date.now()}`, streaming: false }
      this.messages.push(userMsg)

      const aiMsg = { role: 'assistant', content: '', id: `a_${Date.now()}`, streaming: true }
      this.messages.push(aiMsg)
      this.isStreaming = true

      try {
        await chatAPI.sendStream(
          text,
          this.sessionId,
          this.promptId,
          (token) => { aiMsg.content += token },
          () => { aiMsg.streaming = false; this.isStreaming = false }
        )
      } catch (e) {
        aiMsg.content = `[错误] ${e.message}`
        aiMsg.streaming = false
        this.isStreaming = false
      }
    },

    async clearHistory() {
      await chatAPI.clearHistory(this.sessionId)
      this.messages = []
    },
  }
})
